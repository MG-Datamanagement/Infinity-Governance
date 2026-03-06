from fastapi import APIRouter, HTTPException
import psycopg2
from datetime import datetime, timezone


import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("PG_HOST", "postgres_ig"),
    "port": int(os.getenv("PG_PORT", "5432")),
    "dbname": os.getenv("PG_NAME", "semantic_search"),
    "user": os.getenv("PG_USER", "semantic_user"),
    "password": os.getenv("PG_PASSWORD", "semantic_pass"),
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def execute_query(query, params=None):
    conn = get_connection()

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params or {})
            return cur.fetchall()
    finally:
        conn.close()
router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


    
@router.get("/pending-review")
def get_pending_review():
    try:
        pending_review = execute_query("""
            SELECT COUNT(*) AS count
            FROM catalogs
            WHERE owner_id IS NULL
               OR description IS NULL
               OR TRIM(description) = ''
        """)[0]["count"]

        return {"pending_review": pending_review}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/open-issues")
def get_open_issues():
    try:
        open_issues = execute_query("""
            SELECT open_issues_count
            FROM compliance_snapshots
            ORDER BY recorded_at DESC
            LIMIT 1
        """)[0]["open_issues_count"]

        return {"open_issues": open_issues}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    
@router.get("/governance-score")
def get_governance_score():
    try:
        governance_score = execute_query("""
            SELECT overall_score
            FROM compliance_snapshots
            ORDER BY recorded_at DESC
            LIMIT 1
        """)[0]["overall_score"]

        return {"governance_score": governance_score}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/at-risk-domains")
def get_at_risk_domains():
    try:
        at_risk_domains = execute_query("""
            SELECT COUNT(DISTINCT dataset) AS count
            FROM (
                SELECT issue->>'dataset' AS dataset
                FROM compliance_snapshots,
                     jsonb_array_elements(snapshot_json->'open_issues'->'items') AS issue
                WHERE issue->>'severity' IN ('CRITICAL','HIGH')
            ) t
        """)[0]["count"]

        return {"at_risk_domains": at_risk_domains}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/compliance-overview")
def get_compliance_overview():
    try:
        snapshot = execute_query("""
            SELECT snapshot_json
            FROM compliance_snapshots
            ORDER BY recorded_at DESC
            LIMIT 1
        """)[0]["snapshot_json"]

        insight_text = snapshot.get("ai_insights", {}).get("text", "")

        frameworks = snapshot.get("frameworks", [])

        framework_scores = [
            {"framework": fw["name"], "score": fw["score"]}
            for fw in frameworks
        ]

        return {
            "insight": insight_text,
            "framework_scores": framework_scores
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recently-viewed")
def get_recently_viewed():
    try:

        rows = execute_query("""
            SELECT
                c.table_name,
                ds.name AS source_name,
                t.name AS tag,
                al.created_at
            FROM api_logs al
            JOIN catalogs c
                ON c.id::text = al.entity_id
            LEFT JOIN data_sources ds
                ON ds.id = c.source_id
            LEFT JOIN tag_catalog_assignments tca
                ON tca.catalog_id = c.id
            LEFT JOIN tags t
                ON t.id = tca.tag_id
            WHERE al.entity_type = 'catalog'
            ORDER BY al.created_at DESC
            LIMIT 5
        """)

        datasets = [
            {
                "dataset": row["table_name"],
                "source": row["source_name"],
                "tag": row["tag"],
                "time": format_time_ago(row["created_at"])
            }
            for row in rows
        ]

        return {"recently_viewed": datasets}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))