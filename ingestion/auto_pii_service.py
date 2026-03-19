"""
auto_pii_service.py
--------------------
Orchestrates automatic PII / tag detection for both catalogs (tables) and
columns after a successful ingestion job.

Called internally by the ingestion pipeline — NOT a public HTTP endpoint.

Flags
-----
require_auto_pii_detection : bool
    Master switch.  When False the entire service is skipped.

required_human_approval : bool
    Only meaningful when require_auto_pii_detection=True.

    True  → classifications are returned as PENDING suggestions stored in
            pii_detection_pending table; a human must approve before they
            are written to tag_catalog_assignments / tag_column_assignments.

    False → classifications are written directly to the assignment tables
            (save_to_db=True with assigned_by="ai-auto").

"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

# ---------------------------------------------------------------------------
#  classification helpers 
# ---------------------------------------------------------------------------

from services.tag_classify import table_classification_agent as catalog_agent
from services.tag_classify import _fetch_available_tags, _fetch_catalogs_for_source, _save_tag_assignment

from services.tag_classify import column_classification_agent as column_agent
from services.tag_classify import _fetch_columns_for_source, _save_tag_column_assignment
from services.tag_classify import (
    _fetch_available_tags,
    _fetch_catalogs_for_source,
    _fetch_columns_for_source,
    _save_tag_assignment,
    _save_tag_column_assignment,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry-point called by ingestion_manager after successful ingest
# ---------------------------------------------------------------------------

async def run_auto_pii_detection(
    db,
    source_id: str,
    require_auto_pii_detection: bool,
    required_human_approval: bool,
    min_confidence: float = 0.0,
    assigned_by: str = "ai-auto",
) -> dict[str, Any]:
    """
    Orchestrate table-level and column-level tag classification for a source
    that has just been successfully ingested.

    Parameters
    ----------
    db                        : async DB connection (from app)
    source_id                 : UUID of the ingested source
    require_auto_pii_detection: Master switch — if False, returns immediately
    required_human_approval   : If True, store results as PENDING (no direct
                                write to assignment tables).
                                If False, write directly to assignment tables.
    min_confidence            : Skip saving results below this score
    assigned_by               : Label written to assigned_by column

    Returns
    -------
    A summary dict describing what was done. Always safe to log/return.
    """

    # ── Guard: master switch ────────────────────────────────────────────────
    if not require_auto_pii_detection:
        return {
            "skipped": True,
            "reason": "require_auto_pii_detection is False",
        }

    logger.info(
        f"[AutoPII] Starting detection for source={source_id}  "
        f"human_approval={required_human_approval}"
    )

    # ── Fetch shared data once ──────────────────────────────────────────────
    tags = await _fetch_available_tags(db)
    if not tags:
        logger.warning("[AutoPII] No tags found in DB — skipping detection.")
        return {
            "skipped": True,
            "reason": "No tags found in database. Create tags first.",
        }

    tag_name_to_id = {t["name"].lower(): t["id"] for t in tags}
    available_tags_str = ", ".join(t["name"] for t in tags)

    logger.info(f"[AutoPII]  Available tags ({len(tags)}): {available_tags_str}")
    logger.info(f"[AutoPII]  Starting TABLE-level tag classification ...")


    # ── Run both classifiers ────────────────────────────────────────────────
    catalog_summary = await _classify_catalogs(
        db=db,
        source_id=source_id,
        tags=tags,
        tag_name_to_id=tag_name_to_id,
        available_tags_str=available_tags_str,
        required_human_approval=required_human_approval,
        min_confidence=min_confidence,
        assigned_by=assigned_by,
    )

    logger.info(f"[AutoPII]  Starting COLUMN-level tag classification ...")


    column_summary = await _classify_columns(
        db=db,
        source_id=source_id,
        tags=tags,
        tag_name_to_id=tag_name_to_id,
        available_tags_str=available_tags_str,
        required_human_approval=required_human_approval,
        min_confidence=min_confidence,
        assigned_by=assigned_by,
    )

    summary = {
        "skipped": False,
        "source_id": source_id,
        "required_human_approval": required_human_approval,
        "catalog_classification": catalog_summary,
        "column_classification": column_summary,
    }

    logger.info(f"[AutoPII] Completed for source={source_id} → {summary}")
    return summary


# ---------------------------------------------------------------------------
# Internal: classify catalogs (tables)
# ---------------------------------------------------------------------------

async def _classify_catalogs(
    db,
    source_id: str,
    tags: list,
    tag_name_to_id: dict,
    available_tags_str: str,
    required_human_approval: bool,
    min_confidence: float,
    assigned_by: str,
) -> dict:
    catalogs = await _fetch_catalogs_for_source(db, source_id)
    if not catalogs:
        return {"total": 0, "classified": 0, "saved": 0, "pending": 0}

    saved_count   = 0
    pending_count = 0
    error_count   = 0

    logger.info(f"[AutoPII]  Classifying {len(catalogs)} table(s) using fuzzy/LLM logic ...")
    for catalog in catalogs:
        try:
            logger.info(f"[AutoPII]    Analyzing table '{catalog['table_name']}' ...")
            result = catalog_agent.invoke({
                "table_name": catalog["table_name"],
                "table_description": catalog.get("description") or catalog["table_name"], 
                "available_tags": available_tags_str,
            })

            tag_name   = result.get("tag", "Unknown")
            confidence = float(result.get("confidence_score", 0.0))
            reasoning  = result.get("reasoning", "")
            tag_id     = tag_name_to_id.get(tag_name.lower())

            if tag_id is None or confidence < min_confidence:
                logger.info(
                    f"[AutoPII]     '{catalog['table_name']}' skipped — "
                    f"tag='{tag_name}' confidence={confidence:.2f} (below threshold or unknown tag)"
                )
                continue

            logger.info(
                f"[AutoPII]     '{catalog['table_name']}' → tag='{tag_name}' "
                f"(confidence={confidence:.2f})"
            )

            if required_human_approval:
                await _store_pending_catalog(
                    db, source_id, catalog["id"], catalog["table_name"],
                    tag_id, tag_name, confidence, reasoning, assigned_by,
                )
                pending_count += 1
                logger.info(f"[AutoPII]     '{catalog['table_name']}' queued as PENDING (awaiting human approval)")
            else:
                ok = await _save_tag_assignment(db, tag_id, catalog["id"], assigned_by)
                if ok:
                    saved_count += 1
                    logger.info(f"[AutoPII]     Tag '{tag_name}' assigned and saved for table '{catalog['table_name']}'")

        except Exception as e:
            error_count += 1
            logger.error(
                f"[AutoPII] Catalog classification error "
                f"table={catalog['table_name']}: {e}"
            )

    return {
        "total":      len(catalogs),
        "classified": len(catalogs) - error_count,
        "saved":      saved_count,
        "pending":    pending_count,
        "errors":     error_count,
    }


# ---------------------------------------------------------------------------
# Internal: classify columns
# ---------------------------------------------------------------------------

async def _classify_columns(
    db,
    source_id: str,
    tags: list,
    tag_name_to_id: dict,
    available_tags_str: str,
    required_human_approval: bool,
    min_confidence: float,
    assigned_by: str,
) -> dict:
    columns = await _fetch_columns_for_source(db, source_id)
    if not columns:
        return {"total": 0, "classified": 0, "saved": 0, "pending": 0}

    saved_count   = 0
    pending_count = 0
    error_count   = 0

    logger.info(f"[AutoPII]  Classifying {len(columns)} column(s) using fuzzy/LLM logic ...")
    for col in columns:
        try:
            logger.info(
                f"[AutoPII]    Analyzing column '{col['table_name']}.{col['column_name']}' ..."
            )
            result = column_agent.invoke({
                "column_name":        col["column_name"],
                "column_description":  col.get("description") or col.get("column_name") or col.get("name", ""),
                "available_tags":     available_tags_str,
            })

            tag_name     = result.get("tag", "Unknown")
            confidence   = float(result.get("confidence_score", 0.0))
            is_sensitive = bool(result.get("is_sensitive", False))
            data_type    = result.get("data_type", "UNKNOWN")
            reasoning    = result.get("reasoning", "")
            tag_id       = tag_name_to_id.get(tag_name.lower())

            if tag_id is None or confidence < min_confidence:
                logger.info(
                    f"[AutoPII]     '{col['table_name']}.{col['column_name']}' skipped — "
                    f"tag='{tag_name}' confidence={confidence:.2f}"
                )
                continue

            logger.info(
                f"[AutoPII]    '{col['table_name']}.{col['column_name']}' → "
                f"tag='{tag_name}' sensitive={is_sensitive} type={data_type} "
                f"(confidence={confidence:.2f})"
            )

            if required_human_approval:
                await _store_pending_column(
                    db, source_id,
                    col["id"], col["column_name"], col["catalog_id"], col["table_name"],
                    tag_id, tag_name, confidence, is_sensitive, data_type,
                    reasoning, assigned_by,
                )
                pending_count += 1
                logger.info(
                    f"[AutoPII]     '{col['table_name']}.{col['column_name']}' "
                    f"queued as PENDING (awaiting human approval)"
                )
            else:
                ok = await _save_tag_column_assignment(
                    db, tag_id, col["id"], col["catalog_id"],
                    confidence, assigned_by,
                )
                if ok:
                    saved_count += 1
                    logger.info(
                        f"[AutoPII]     Tag '{tag_name}' assigned and saved for "
                        f"column '{col['table_name']}.{col['column_name']}'"
                    )

        except Exception as e:
            error_count += 1
            logger.error(
                f"[AutoPII] Column classification error "
                f"col={col['column_name']} catalog={col['catalog_id']}: {e}"
            )

    return {
        "total":      len(columns),
        "classified": len(columns) - error_count,
        "saved":      saved_count,
        "pending":    pending_count,
        "errors":     error_count,
    }


# ---------------------------------------------------------------------------
# Pending-approval helpers
# ---------------------------------------------------------------------------

async def _store_pending_catalog(
    db,
    source_id: str,
    catalog_id: str,
    table_name: str,
    tag_id: str,
    tag_name: str,
    confidence: float,
    reasoning: str,
    suggested_by: str,
) -> None:
    await db.execute(
        """
        INSERT INTO pii_detection_pending
            (source_id, entity_type, catalog_id, column_id,
             tag_id, tag_name, confidence_score, reasoning,
             suggested_by, status)
        VALUES ($1, 'catalog', $2, NULL, $3, $4, $5, $6, $7, 'pending')
        ON CONFLICT (entity_type, catalog_id, column_id_or_null, tag_id)
        DO UPDATE SET
            confidence_score = EXCLUDED.confidence_score,
            reasoning        = EXCLUDED.reasoning,
            suggested_by     = EXCLUDED.suggested_by,
            suggested_at     = NOW(),
            status           = 'pending'
        """,
        source_id, catalog_id, tag_id, tag_name,
        confidence, reasoning, suggested_by,
    )


async def _store_pending_column(
    db,
    source_id: str,
    column_id: str,
    column_name: str,
    catalog_id: str,
    table_name: str,
    tag_id: str,
    tag_name: str,
    confidence: float,
    is_sensitive: bool,
    data_type: str,
    reasoning: str,
    suggested_by: str,
) -> None:
    await db.execute(
        """
        INSERT INTO pii_detection_pending
            (source_id, entity_type, catalog_id, column_id,
             tag_id, tag_name, confidence_score, is_sensitive, data_type,
             reasoning, suggested_by, status)
        VALUES ($1, 'column', $2, $3, $4, $5, $6, $7, $8, $9, $10, 'pending')
        ON CONFLICT (entity_type, catalog_id, column_id_or_null, tag_id)
        DO UPDATE SET
            confidence_score = EXCLUDED.confidence_score,
            is_sensitive     = EXCLUDED.is_sensitive,
            data_type        = EXCLUDED.data_type,
            reasoning        = EXCLUDED.reasoning,
            suggested_by     = EXCLUDED.suggested_by,
            suggested_at     = NOW(),
            status           = 'pending'
        """,
        source_id, catalog_id, column_id, tag_id, tag_name,
        confidence, is_sensitive, data_type, reasoning, suggested_by,
    )


