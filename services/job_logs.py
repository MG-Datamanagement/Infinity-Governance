"""
services/job_logs.py
--------------------
Server-Sent Events (SSE) endpoint that streams real-time ingestion logs
for a specific job to any connected client, plus a REST endpoint to
query persisted logs for a data source.

Endpoints
---------
GET /api/v1/jobs/{job_id}/logs/stream
    → Real-time SSE stream for a running job.

GET /api/v1/sources/{source_id}/logs
    → Paginated log history for a source, optionally filtered by:
        - last_run=true          → only logs from the most recent job
        - since=<ISO timestamp>  → logs after a given timestamp
        - level=error|success|warning
        - limit (default 100, max 500)

How to connect via SSE (frontend)
----------------------------------
    const es = new EventSource(`/api/v1/jobs/${jobId}/logs/stream`);

    es.addEventListener("log", (e) => {
        const { timestamp, level, message } = JSON.parse(e.data);
        console.log(`[${timestamp}] ${level}: ${message}`);
    });

    es.addEventListener("done", () => {
        console.log("Job finished — stream closed");
        es.close();
    });

    es.addEventListener("error", (e) => {
        console.error("Stream error", e);
        es.close();
    });

SSE event types emitted
-----------------------
  log   — a single log line  { timestamp, level, message }
  done  — job finished, stream will close
  error — job_id not found or stream error

Level values
------------
  "error"   — ERROR / CRITICAL log records
  "warning" — WARNING log records
  "success" — INFO / DEBUG log records
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ingestion.job_log_handler import get_log_queue, is_done_sentinel

# NOTE: `db` is imported lazily inside functions (not at module level) to
# avoid a circular import — app.py imports this module, so a top-level
# `from app import db` here would create: app.py → job_logs.py → app.py.

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ingestion Logs"])


def _get_db():
    """
    Return the shared Database() instance from app.py.
    Deferred to call-time so app.py finishes loading before we touch it.
    """
    import importlib
    return importlib.import_module("app").db


# =============================================================================
# SSE stream — real-time logs for a running job
# =============================================================================

@router.get(
    "/api/v1/jobs/{job_id}/logs/stream",
    summary="Stream real-time ingestion logs via SSE",
    response_description="text/event-stream — one SSE event per log line",
    responses={
        200: {"description": "SSE stream open — events: log | done | error"},
        404: {"description": "No active log stream found for this job_id"},
    },
)
async def stream_job_logs(job_id: str):
    """
    Open a Server-Sent Events stream for a running ingestion job.

    - Connect before or immediately after the ingest call.
    - Emits `log` events until the job finishes, then emits `done` and closes.
    - Levels emitted: `error` | `warning` | `success`.
    - If job_id is not found, polls briefly before returning 404.
    """
    # Guard against race condition: SSE connected before job registers handler
    queue = None
    for _ in range(20):          # wait up to 2 s
        queue = get_log_queue(job_id)
        if queue is not None:
            break
        await asyncio.sleep(0.1)

    if queue is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No active log stream for job '{job_id}'. "
                "The job may have already completed or the job_id is invalid."
            ),
        )

    async def event_generator():
        try:
            while True:
                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue

                if is_done_sentinel(entry):
                    yield 'event: done\ndata: {"message": "Ingestion job completed"}\n\n'
                    break

                yield f"event: log\ndata: {json.dumps(entry)}\n\n"

        except asyncio.CancelledError:
            pass  # client disconnected cleanly
        except Exception as e:
            logger.error(f"SSE stream error for job {job_id}: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",   # disable Nginx buffering
            "Connection":        "keep-alive",
        },
    )


# =============================================================================
# REST — persisted logs for a data source
# =============================================================================

@router.get(
    "/api/v1/sources/{source_id}/logs",
    summary="List persisted ingestion logs for a data source",
    responses={
        200: {"description": "List of log entries, newest first"},
        404: {"description": "No logs found"},
    },
)
async def get_source_logs(
    source_id: str,
    last_run: bool = Query(
        False,
        description="If true, return only logs from the most recent ingestion job.",
    ),
    since: Optional[datetime] = Query(
        None,
        description="Return logs at or after this ISO-8601 timestamp (e.g. 2025-01-15T10:00:00Z).",
    ),
    level: Optional[str] = Query(
        None,
        description="Filter by level: error | warning | success",
        pattern="^(error|warning|success)$",
    ),
    limit: int = Query(
        100,
        ge=1,
        le=500,
        description="Maximum number of log entries to return (default 100, max 500).",
    ),
):
    """
    Retrieve persisted ingestion logs for a specific data source.

    **Filters (combinable)**
    - `last_run=true` — only the most recent job's logs
    - `since=<timestamp>` — logs after a specific point in time
    - `level=error|warning|success` — filter by severity
    - `limit` — page size (default 100, max 500)

    **Response** — ordered newest-first:
    ```json
    {
      "source_id": "uuid",
      "total": 42,
      "filters": { ... },
      "logs": [
        {
          "id":        "uuid",
          "job_id":    "uuid",
          "source_id": "uuid",
          "level":     "error | warning | success",
          "message":   "Concise one-line description",
          "logged_at": "2025-01-15T10:23:45.123456+00:00"
        }
      ]
    }
    ```
    """
    db = _get_db()

    # ── Resolve latest job_id when last_run=true ──────────────────────────
    target_job_id: Optional[str] = None
    if last_run:
        rows_job = await db.fetch_all(
            """
            SELECT id
            FROM   ingestion_jobs
            WHERE  source_id = $1
            ORDER  BY created_at DESC
            LIMIT  1
            """,
            source_id,
        )
        if not rows_job:
            raise HTTPException(
                status_code=404,
                detail=f"No ingestion jobs found for source '{source_id}'.",
            )
        target_job_id = str(rows_job[0]["id"])

    # ── Build query with dynamic filters ─────────────────────────────────
    conditions = ["source_id = $1"]
    params     = [source_id]
    idx        = 2

    if target_job_id:
        conditions.append(f"job_id = ${idx}")
        params.append(target_job_id)
        idx += 1

    if since:
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        conditions.append(f"logged_at >= ${idx}")
        params.append(since)
        idx += 1

    if level:
        conditions.append(f"level = ${idx}")
        params.append(level)
        idx += 1

    params.append(limit)
    where_clause = " AND ".join(conditions)

    rows = await db.fetch_all(
        f"""
        SELECT id, job_id, source_id, level, message, logged_at
        FROM   job_logs
        WHERE  {where_clause}
        ORDER  BY logged_at DESC
        LIMIT  ${idx}
        """,
        *params,
    )

    if not rows:
        detail = f"No logs found for source '{source_id}'"
        if last_run:
            detail += " (last run)"
        if since:
            detail += f" since {since.isoformat()}"
        if level:
            detail += f" with level '{level}'"
        raise HTTPException(status_code=404, detail=detail + ".")

    return {
        "source_id": source_id,
        "total":     len(rows),
        "filters": {
            "last_run": last_run,
            "since":    since.isoformat() if since else None,
            "level":    level,
            "limit":    limit,
        },
        "logs": [
            {
                "id":        str(row["id"]),
                "job_id":    str(row["job_id"]),
                "source_id": str(row["source_id"]),
                "level":     row["level"],
                "message":   row["message"],
                "logged_at": row["logged_at"].isoformat(),
            }
            for row in rows
        ],
    }