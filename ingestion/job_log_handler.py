"""
ingestion/job_log_handler.py
-----------------------------
In-memory log capture per ingestion job, with DB persistence.

How it works
------------
- JobLogHandler is a standard Python logging.Handler subclass.
- When a job starts, a handler is registered for that job_id.
- Every logger.info/error call in ingestion.core or ingestion.auto_pii_service
  gets captured into an asyncio.Queue for that job.
- The SSE endpoint reads from that queue and streams to the frontend.
- Each log entry is also persisted to the `job_logs` DB table via the
  shared Database() instance from app.py (lazy-imported to avoid circular deps).
- When the job finishes (or times out) the handler is removed.

Level mapping
-------------
  logging.ERROR / CRITICAL  → "error"
  logging.WARNING           → "warning"
  everything else           → "success"

Error messages
--------------
  Full tracebacks are collapsed to a single concise line.

Usage
-----
    from ingestion.job_log_handler import register_job, deregister_job, get_log_queue

    register_job(job_id, source_id)   # call before ingest() starts
    ...ingest runs...
    deregister_job(job_id)            # call after ingest() ends
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
from datetime import datetime, timezone
from typing import Dict, Optional

# ── Global registry ───────────────────────────────────────────────────────────
_job_queues: Dict[str, asyncio.Queue] = {}
_lock = threading.Lock()

_DONE_SENTINEL = "__DONE__"


# ── Level mapping ─────────────────────────────────────────────────────────────

def _map_level(levelname: str) -> str:
    if levelname in ("ERROR", "CRITICAL"):
        return "error"
    if levelname == "WARNING":
        return "warning"
    return "success"


# ── Message condenser ─────────────────────────────────────────────────────────

_TRACEBACK_START = re.compile(r"Traceback \(most recent call last\)", re.IGNORECASE)
_EXCEPTION_LINE  = re.compile(r"^(\w*Error|\w*Exception|Exception):\s*(.+)$", re.MULTILINE)

# Known error patterns → short 6-7 word labels (checked in order)
_ERROR_PATTERNS = [
    (re.compile(r"duplicate key.+unique constraint", re.I), "Duplicate key, unique constraint violated"),
    (re.compile(r"unique constraint",                re.I), "Unique constraint violated"),
    (re.compile(r"foreign key.+violat",              re.I), "Foreign key constraint violated"),
    (re.compile(r"not.null.+violat|null value.+column", re.I), "Null value in non-null column"),
    (re.compile(r"connect.+refused|could not connect", re.I), "Connection refused to host"),
    (re.compile(r"timeout|timed out",                re.I), "Connection timed out"),
    (re.compile(r"permission denied|access denied",  re.I), "Permission denied"),
    (re.compile(r"does not exist|no such",           re.I), "Resource does not exist"),
    (re.compile(r"syntax error",                     re.I), "SQL syntax error"),
    (re.compile(r"out of memory|memory error",       re.I), "Out of memory"),
    (re.compile(r"disk.*(full|quota)|no space",      re.I), "Disk full or quota exceeded"),
    (re.compile(r"authentication fail|password",     re.I), "Authentication failed"),
    (re.compile(r"schema.*(process|fail|error)",     re.I), "Error processing schema"),
    (re.compile(r"(process|parsing).*(record|row)",  re.I), "Error processing record"),
    (re.compile(r"pipeline.*(fail|error)",           re.I), "Ingestion pipeline failed"),
]


def _condense_message(message: str, levelname: str) -> str:
    """
    For errors: match against known patterns and return a max 6-7 word label.
    For other levels: return the first meaningful line as-is.
    """
    if levelname not in ("ERROR", "CRITICAL"):
        return next((ln.strip() for ln in message.splitlines() if ln.strip()), message)

    # Check known patterns first (scans full message including any traceback)
    for pattern, label in _ERROR_PATTERNS:
        if pattern.search(message):
            return label

    # Extract exception type + short snippet from traceback
    match = _EXCEPTION_LINE.search(message)
    if match:
        exc_type = match.group(1)
        words = match.group(2).strip().split()
        short = " ".join(words[:6]) + ("..." if len(words) > 6 else "")
        return f"{exc_type}: {short}"

    # Fallback: first non-boilerplate line, capped at 7 words
    lines = [ln.strip() for ln in message.splitlines() if ln.strip()]
    lines = [ln for ln in lines if not _TRACEBACK_START.match(ln)
             and not ln.startswith("File ") and not ln.startswith("^")]
    first = lines[0] if lines else message
    words = first.split()
    return " ".join(words[:7]) + ("..." if len(words) > 7 else "")


# ── Public API ────────────────────────────────────────────────────────────────

def register_job(
    job_id: str,
    source_id: Optional[str] = None,
    maxsize: int = 2000,
) -> asyncio.Queue:
    """
    Create a log queue for this job and attach a logging handler.

    Args:
        job_id:    Unique ingestion job UUID string.
        source_id: The data source this job belongs to (stored in DB).
        maxsize:   Max in-memory log entries buffered (drops if full).
    """
    q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
    handler = _JobQueueHandler(job_id, source_id, q)
    handler.setLevel(logging.DEBUG)

    with _lock:
        _job_queues[job_id] = q

    for name in ("ingestion.core", "ingestion.auto_pii_service"):
        logging.getLogger(name).addHandler(handler)

    return q


def deregister_job(job_id: str) -> None:
    """Remove the handler and push done sentinel so the SSE stream closes."""
    with _lock:
        q = _job_queues.pop(job_id, None)

    if q:
        for name in ("ingestion.core", "ingestion.auto_pii_service"):
            lg = logging.getLogger(name)
            lg.handlers = [
                h for h in lg.handlers
                if not (isinstance(h, _JobQueueHandler) and h.job_id == job_id)
            ]
        try:
            q.put_nowait(_DONE_SENTINEL)
        except asyncio.QueueFull:
            pass


def get_log_queue(job_id: str) -> Optional[asyncio.Queue]:
    """Return the queue for a running job, or None if not found."""
    with _lock:
        return _job_queues.get(job_id)


def is_done_sentinel(value) -> bool:
    return value == _DONE_SENTINEL


# ── Internal handler ──────────────────────────────────────────────────────────

class _JobQueueHandler(logging.Handler):
    """
    Logging handler that:
      1. Condenses the message to one concise line.
      2. Maps the Python log level to error / warning / success.
      3. Pushes the entry to the asyncio.Queue (consumed by SSE stream).
      4. Persists the entry to the `job_logs` DB table via app.db.
    """

    def __init__(self, job_id: str, source_id: Optional[str], queue: asyncio.Queue):
        super().__init__()
        self.job_id    = job_id
        self.source_id = source_id
        self._queue    = queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            raw     = self.format(record)
            message = _condense_message(raw, record.levelname)
            level   = _map_level(record.levelname)

            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level":     level,
                "message":   message,
            }

            # Push to SSE queue (non-blocking — drops if queue full)
            try:
                self._queue.put_nowait(entry)
            except asyncio.QueueFull:
                pass

            # Persist to DB (fire-and-forget on the running event loop)
            self._persist(entry)

        except Exception:
            self.handleError(record)

    def _persist(self, entry: dict) -> None:
        """Schedule async DB insert without blocking the ingestion thread."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._insert(entry))
        except RuntimeError:
            pass  # no event loop available — skip persistence

    async def _insert(self, entry: dict) -> None:
        """Insert one log entry into job_logs using the shared Database()."""
        try:
            # Lazy import — avoids circular dependency with app.py at module load
            import importlib
            db = importlib.import_module("app").db

            await db.execute(
                """
                INSERT INTO job_logs (job_id, source_id, level, message, logged_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                self.job_id,
                self.source_id,
                entry["level"],
                entry["message"],
                datetime.fromisoformat(entry["timestamp"]),
            )
        except Exception as exc:
            # Never let a DB failure surface into ingestion logic
            logging.getLogger(__name__).debug("job_logs DB insert failed: %s", exc)