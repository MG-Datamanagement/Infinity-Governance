from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import json

router = APIRouter(tags=["audit"])

# ============================================================================
# Schemas for the Audit Trail Screen
# ============================================================================

class AuditSummary(BaseModel):
    total_events: int
    metadata_updates: int
    classification_events: int
    access_events: int
    lineage_events: int

class ActivityEventItem(BaseModel):
    id: str
    when_time: datetime
    who_name: str
    what_action: str
    where_location: str
    details: Optional[str]
    status: str

class CatalogAuditTrailResponse(BaseModel):
    catalog_id: str
    summary: AuditSummary
    total_log_count: int
    activity_log: List[ActivityEventItem]

# ============================================================================
# API Endpoint Logic
# ============================================================================

@router.get(
    "/api/v1/catalogs/{catalog_id}/audit-trail",
    response_model=CatalogAuditTrailResponse,
    summary="Retrieve the comprehensive audit trail for a dataset (catalog)"
)
async def get_catalog_audit_trail(
    catalog_id: str, 
    limit: int = 50, 
    offset: int = 0
):
    """
    Fetches the summary metrics and paginated activity logs for the Audit Screen.
    Matches the `entity_id` in `api_logs` to the given `catalog_id`.
    """
    from app import db, logger  # Assuming `db` is the instance from the app module
    
    # -------------------------------------------------------------------------
    # 1. Fetch Summary Metrics (The top 4 cards)
    # -------------------------------------------------------------------------
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import json

router = APIRouter(tags=["audit"])

# ============================================================================
# Schemas for the Audit Trail Screen
# ============================================================================

class AuditSummary(BaseModel):
    total_events: int
    metadata_updates: int
    classification_events: int
    access_events: int
    lineage_events: int

class ActivityEventItem(BaseModel):
    id: str
    when_time: datetime
    who_name: str
    what_action: str
    where_location: str
    details: Optional[str]
    status: str

class CatalogAuditTrailResponse(BaseModel):
    catalog_id: str
    summary: AuditSummary
    total_log_count: int
    activity_log: List[ActivityEventItem]

# ============================================================================
# API Endpoint Logic
# ============================================================================

@router.get(
    "/api/v1/catalogs/{catalog_id}/audit-trail",
    response_model=CatalogAuditTrailResponse,
    summary="Retrieve the comprehensive audit trail for a dataset (catalog)"
)
async def get_catalog_audit_trail(
    catalog_id: str, 
    limit: int = 50, 
    offset: int = 0
):
    """
    Fetches the summary metrics and paginated activity logs for the Audit Screen.
    Matches the `entity_id` in `api_logs` to the given `catalog_id`.
    """
    from app import db, logger  # Assuming `db` is the instance from the app module
    
    # -------------------------------------------------------------------------
    # 1. Fetch Summary Metrics (The top 4 cards)
    # -------------------------------------------------------------------------
    
    summary_query = """
        SELECT 
            -- 1. Total Events (Last 30 Days)
            COUNT(*) AS total_events,
            
            -- 2. Metadata Updates
            COUNT(*) FILTER (
                WHERE method != 'GET' AND (
                   LOWER(action_summary) LIKE '%property%' 
                   OR LOWER(action_summary) LIKE '%datacard%'
                )
            ) AS metadata_updates,
            
            -- 3. Classification Events
            COUNT(*) FILTER (
                WHERE method != 'GET' AND (
                   LOWER(action_summary) LIKE '%tag%' 
                   OR LOWER(action_summary) LIKE '%classif%'
                )
            ) AS classification_events, 
            
            -- 4. Access Events (Placeholder, calculated dynamically below)
            0 AS access_events,
            
            -- 5. Lineage Events
            COUNT(*) FILTER (
                WHERE method != 'GET' AND (
                   LOWER(action_summary) LIKE '%lineage%'
                ) 
            ) AS lineage_events

        FROM api_logs
        WHERE entity_id = $1 
          AND entity_type = 'catalog'
    """
    summary_record = await db.fetch_one(summary_query, catalog_id)
    
    # -------------------------------------------------------------------------
    # 2. Fetch the Paginated Activity Log Table
    # -------------------------------------------------------------------------
    
    # First, get catalog info for fallback owner and source name
    catalog_info = await db.fetch_one("""
        SELECT 
            ds.name AS source_name,
            COALESCE(co.name, so.name) AS fallback_owner_name,
            COALESCE(co.role, so.role) AS fallback_owner_role
        FROM catalogs c
        LEFT JOIN data_sources ds ON c.source_id = ds.id
        LEFT JOIN owners co ON c.owner_id = co.id
        LEFT JOIN owners so ON ds.owner_id = so.id
        WHERE c.id = $1
    """, catalog_id)
    
    if catalog_info:
        source_name = catalog_info["source_name"] or "Unknown Source"
        if catalog_info["fallback_owner_name"]:
            fallback_owner = f"{catalog_info['fallback_owner_name']} ({catalog_info['fallback_owner_role'] or 'No Role'})"
        else:
            fallback_owner = "Unassigned"
    else:
        source_name = "Unknown Source"
        fallback_owner = "Unassigned"

    log_query = """
        SELECT 
            al.id,
            al.created_at AS when_time,
            o.name AS explicit_owner_name,
            o.role AS explicit_owner_role,
            al.action_summary AS what_action,
            al.endpoint AS where_location,
            al.response_summary AS details,
            al.status_code,
            al.method
        FROM api_logs al
        LEFT JOIN owners o ON al.owner_id = o.id
        WHERE al.entity_id = $1
          AND al.entity_type = 'catalog'
        ORDER BY al.created_at DESC
        LIMIT $2 OFFSET $3
    """
    
    logs_records = await db.fetch_all(log_query, catalog_id, limit, offset)
    
    # Total count for table pagination
    total_count = await db.fetch_val(
        "SELECT COUNT(*) FROM api_logs WHERE entity_id = $1 AND entity_type = 'catalog'", 
        catalog_id
    )

    # -------------------------------------------------------------------------
    # 3. Format the Results
    # -------------------------------------------------------------------------
    
    activity_log = []
    for record in logs_records:
        # Resolve status string from HTTP status codes for the UI badge
        status_code = record["status_code"]
        if status_code and 200 <= status_code < 300:
            status_text = "Done"
        elif status_code and 400 <= status_code < 600:
            status_text = "Alert"
        else:
            status_text = "Review"
            
        # Parse endpoint and method
        endpoint_lower = (record["where_location"] or "").lower()
        method = record["method"] or ""
        raw_action = record["what_action"] or ""
        
        # Determine "who_name"
        is_ai_task = False
        if ("datacard" in endpoint_lower or "classify" in endpoint_lower) and method == "POST":
            is_ai_task = True
            
        if is_ai_task:
            who_name = "AI Agent (Automated)"
        elif record["explicit_owner_name"]:
            who_name = f"{record['explicit_owner_name']} ({record['explicit_owner_role'] or 'No Role'})"
        else:
            who_name = fallback_owner
            
        # Determine "where_location" tab
        if "datacard" in endpoint_lower:
            tab_name = "Datacard Tab"
        elif "compliance" in endpoint_lower:
            tab_name = "Compliance Tab"
        elif "lineage" in endpoint_lower:
            tab_name = "Lineage Tab"
        elif "properties" in endpoint_lower:
            tab_name = "Properties Tab"
        elif "classify" in endpoint_lower or "tag" in endpoint_lower:
            tab_name = "Classification Tab"
        else:
            tab_name = "General Tab"
            
        final_where = f"{source_name} - {tab_name}"
        
        # Determine "what_action"
        if "classify" in endpoint_lower or "tag" in endpoint_lower:
            final_what = f"Classification - {raw_action}"
        elif method == "POST":
            final_what = f"Creation - {raw_action}"
        elif method in ("PUT", "PATCH"):
            final_what = f"Updation - {raw_action}"
        elif method == "DELETE":
            final_what = f"Deletion - {raw_action}"
        else:
            final_what = f"Viewed - {raw_action}"
            
        activity_log.append(
            ActivityEventItem(
                id=str(record["id"]),
                when_time=record["when_time"],
                who_name=who_name,
                what_action=final_what,
                where_location=final_where,
                details=record["details"] or "No extra details available.",
                status=status_text
            )
        )
        
    # Calculate mutually exclusive sums representing 100% of logs
    meta_ev  = summary_record["metadata_updates"] or 0
    class_ev = summary_record["classification_events"] or 0
    lin_ev   = summary_record["lineage_events"] or 0

    # Ensure total sum equals the total_count
    acc_ev   = total_count - (meta_ev + class_ev + lin_ev)
    if acc_ev < 0:
        acc_ev = 0

    return CatalogAuditTrailResponse(
        catalog_id=catalog_id,
        summary=AuditSummary(
            total_events=total_count,
            metadata_updates=meta_ev,
            classification_events=class_ev,
            access_events=acc_ev,
            lineage_events=lin_ev,
        ),
        total_log_count=total_count,
        activity_log=activity_log
    )
