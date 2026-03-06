# =============================================================================
#  COMPLIANCE ENGINE — FastAPI Dashboard API
#
#  Endpoints:
#    GET /api/compliance/overview      → trigger fresh scan + return dashboard
#    GET /health                    → liveness check
#
#  New table: compliance_snapshots
#    Replaces compliance_history entirely.
#    Stores the FULL dashboard response payload as JSONB plus individual
#    score columns for fast trend queries.
#
#  Install:
#    pip install fastapi uvicorn langchain langchain-groq langgraph
#                psycopg2-binary python-dotenv
#
#  .env:
#    PG_DSN=postgresql://user:password@host:5432/dbname
#    -- or individual: DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD
#    GROQ_API_KEY=...
#    GROQ_MODEL_NAME=llama-3.1-8b-instant
#
#  Run:
#    uvicorn main:app --reload --port 8000
#    -- or --
#    python main.py
# =============================================================================

import json
import logging
import os
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from itertools import chain
from typing import Any, Generator, Optional, TypedDict
import re
from langchain_openai import AzureChatOpenAI
import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.graph import END, StateGraph

import io
import json
import os
from datetime import datetime

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (HRFlowable, KeepTogether, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("compliance_engine")

# Use UTC timezone (cross-platform compatible)
IST = timezone.utc

# =============================================================================
# CONSTANTS
# =============================================================================

QUICK_ACTIONS = [
    {"label": "Run Full Scan", "action": "run_full_scan"},
    {"label": "Export Report", "action": "export_report"},
]

SEVERITY_DUE_DAYS = {"critical": 3, "high": 7, "medium": 14, "low": 30}


# =============================================================================
# DDL — AUTO-CREATED TABLES ON STARTUP
#
# compliance_snapshots replaces compliance_history:
#   - One row per scan run
#   - Individual score columns (fast trend queries without JSON parsing)
#   - snapshot_json stores the FULL dashboard payload for GET /dashboard
#
# glossary tables auto-created if missing (needed by GDPR-003 / HIPAA-002)
# =============================================================================

# =============================================================================
# FRAMEWORK RULES
# =============================================================================

FRAMEWORK_RULES: dict = {

    "GDPR": [
        {
            "rule_id": "GDPR-001",
            "rule": "PII/sensitive catalogs must have a description (retention policy proxy)",
            "sql": """
                SELECT c.id, c.table_name AS name, c.full_name, c.schema_name,
                       c.database_name, c.description, c.owner_id,
                       t.name AS tag_name, c.updated_at
                FROM catalogs c
                JOIN tag_catalog_assignments tca ON tca.catalog_id = c.id
                JOIN tags t ON t.id = tca.tag_id
                WHERE LOWER(t.name) = ANY(%(tags)s)
                  AND (c.description IS NULL OR TRIM(c.description) = '')
                ORDER BY c.full_name LIMIT 100
            """,
            "sql_params": {"tags": ["pii", "sensitive", "confidential", "personal data"]},
            "eval_prompt": (
                "You are a GDPR compliance auditor. "
                "The following tables are tagged as PII or sensitive but have NO description. "
                "Description is the only place to document retention policies and processing "
                "purposes. Missing = no documented retention policy = GDPR Article 5(1)(e) violation. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
        },
        {
            "rule_id": "GDPR-002",
            "rule": "PII/sensitive catalogs must have an assigned owner (data steward accountability)",
            "sql": """
                SELECT c.id, c.table_name AS name, c.full_name, c.schema_name,
                       c.database_name, c.owner_id, t.name AS tag_name,
                       c.created_at, c.updated_at
                FROM catalogs c
                JOIN tag_catalog_assignments tca ON tca.catalog_id = c.id
                JOIN tags t ON t.id = tca.tag_id
                WHERE LOWER(t.name) = ANY(%(tags)s)
                  AND c.owner_id IS NULL
                ORDER BY c.full_name LIMIT 100
            """,
            "sql_params": {"tags": ["pii", "sensitive", "confidential", "personal data"]},
            "eval_prompt": (
                "You are a GDPR compliance auditor. "
                "These tables contain personal data but have no assigned owner. "
                "GDPR Article 5(2) requires accountability for all personal data assets. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
        },
        {
            "rule_id": "GDPR-003",
            "rule": "PII-tagged columns must be linked to a glossary term (Article 30 data mapping)",
            "sql": """
                SELECT col.id AS column_id, col.name AS column_name, col.data_type,
                       col.description AS column_description, c.id AS catalog_id,
                       c.table_name, c.full_name, c.schema_name, t.name AS tag_name
                FROM columns col
                JOIN catalogs c ON c.id = col.catalog_id
                JOIN tag_column_assignments tca ON tca.column_id = col.id
                JOIN tags t ON t.id = tca.tag_id
                WHERE LOWER(t.name) = ANY(%(tags)s)
                  AND (
                    (col.description IS NULL OR TRIM(col.description) = '')
                    OR col.id NOT IN (SELECT column_id FROM glossary_term_column_assignments)
                  )
                ORDER BY c.full_name, col.name LIMIT 100
            """,
            "sql_params": {"tags": ["pii", "personal data", "sensitive"]},
            "eval_prompt": (
                "You are a GDPR compliance auditor. "
                "These PII columns have no glossary term or description. "
                "Without linkage they cannot appear in Article 30 records of processing activities. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
        },
    ],

    "SOC2": [
        {
            "rule_id": "SOC2-001",
            "rule": "Admin and data steward owners must have an email address (CC6.1 access accountability)",
            "sql": """
                SELECT o.id, o.name, o.role, o.email, o.created_at, o.updated_at
                FROM owners o
                WHERE o.role = ANY(%(roles)s)
                  AND (o.email IS NULL OR TRIM(o.email) = '')
                ORDER BY o.role, o.name LIMIT 100
            """,
            "sql_params": {"roles": ["admin", "data_steward", "technical_owner"]},
            "eval_prompt": (
                "You are a SOC2 compliance auditor. "
                "These data owners (admins/stewards) have no email address. "
                "SOC2 CC6.1 requires identifiable, contactable responsible parties. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
        },
        {
            "rule_id": "SOC2-002",
            "rule": "All catalog tables must have an assigned owner (CC6.3 access review accountability)",
            "sql": """
                SELECT c.id, c.table_name AS name, c.full_name, c.schema_name,
                       c.database_name, c.row_count, c.created_at, c.updated_at, c.last_seen_at
                FROM catalogs c
                WHERE c.owner_id IS NULL
                ORDER BY c.full_name LIMIT 100
            """,
            "sql_params": {},
            "eval_prompt": (
                "You are a SOC2 compliance auditor. "
                "These catalog tables have no assigned owner. "
                "SOC2 CC6.3 requires an accountable owner for access reviews. "
                ">50 = critical, 20-50 = high, 5-20 = medium, <5 = low. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
        },
        {
            "rule_id": "SOC2-003",
            "rule": "Data sources must not remain in failed ingestion status (A1.2 availability)",
            "sql": """
                SELECT ds.id, ds.name, ds.source_type, ds.status,
                       ds.last_ingested_at, ds.updated_at, ds.created_at,
                       o.name AS owner_name, o.email AS owner_email, o.role AS owner_role
                FROM data_sources ds
                LEFT JOIN owners o ON o.id = ds.owner_id
                WHERE ds.status = 'failed'
                ORDER BY ds.updated_at DESC LIMIT 100
            """,
            "sql_params": {},
            "eval_prompt": (
                "You are a SOC2 compliance auditor. "
                "These data sources are in FAILED ingestion status. "
                "SOC2 A1.2 requires monitored, functioning data pipelines. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
        },
    ],

    "HIPAA": [
        {
            "rule_id": "HIPAA-001",
            "rule": "PHI-tagged catalogs must have an owner with email (45 CFR 164.308 assigned responsibility)",
            "sql": """
                SELECT c.id, c.table_name AS name, c.full_name, c.schema_name,
                       c.database_name, c.owner_id, t.name AS tag_name,
                       o.name AS owner_name, o.role AS owner_role,
                       o.email AS owner_email, c.updated_at
                FROM catalogs c
                JOIN tag_catalog_assignments tca ON tca.catalog_id = c.id
                JOIN tags t ON t.id = tca.tag_id
                LEFT JOIN owners o ON o.id = c.owner_id
                WHERE LOWER(t.name) = ANY(%(tags)s)
                  AND (c.owner_id IS NULL OR o.email IS NULL OR TRIM(o.email) = '')
                ORDER BY c.full_name LIMIT 100
            """,
            "sql_params": {"tags": ["phi", "hipaa", "health data", "medical"]},
            "eval_prompt": (
                "You are a HIPAA compliance auditor. "
                "PHI tables have no owner or owner has no email. "
                "HIPAA 45 CFR 164.308(a)(2) requires an assigned, contactable security officer for PHI. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
        },
        {
            "rule_id": "HIPAA-002",
            "rule": "PHI-tagged columns must have a description and glossary term (45 CFR 164.312 documentation)",
            "sql": """
                SELECT col.id AS column_id, col.name AS column_name, col.data_type,
                       col.description AS column_description, c.id AS catalog_id,
                       c.table_name, c.full_name, c.schema_name, t.name AS tag_name,
                       CASE WHEN col.description IS NULL OR TRIM(col.description) = ''
                            THEN 'missing_description' ELSE 'missing_glossary_term'
                       END AS violation_type
                FROM columns col
                JOIN catalogs c ON c.id = col.catalog_id
                JOIN tag_column_assignments tca ON tca.column_id = col.id
                JOIN tags t ON t.id = tca.tag_id
                WHERE LOWER(t.name) = ANY(%(tags)s)
                  AND (
                    (col.description IS NULL OR TRIM(col.description) = '')
                    OR col.id NOT IN (SELECT column_id FROM glossary_term_column_assignments)
                  )
                ORDER BY c.full_name, col.name LIMIT 100
            """,
            "sql_params": {"tags": ["phi", "hipaa", "health data", "medical"]},
            "eval_prompt": (
                "You are a HIPAA compliance auditor. "
                "PHI columns lack description or glossary term. "
                "HIPAA 45 CFR 164.312 requires PHI to be properly identified and documented. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
        },
        {
            "rule_id": "HIPAA-003",
            "rule": "PHI-tagged catalogs must not be stale (last seen within 30 days)",
            "sql": """
                SELECT c.id, c.table_name AS name, c.full_name, c.schema_name,
                       c.database_name, c.last_seen_at, c.updated_at,
                       t.name AS tag_name, o.name AS owner_name, o.email AS owner_email,
                       EXTRACT(DAY FROM NOW() - c.last_seen_at) AS days_since_seen
                FROM catalogs c
                JOIN tag_catalog_assignments tca ON tca.catalog_id = c.id
                JOIN tags t ON t.id = tca.tag_id
                LEFT JOIN owners o ON o.id = c.owner_id
                WHERE LOWER(t.name) = ANY(%(tags)s)
                  AND c.last_seen_at < NOW() - INTERVAL '30 days'
                ORDER BY c.last_seen_at ASC LIMIT 100
            """,
            "sql_params": {"tags": ["phi", "hipaa", "health data", "medical"]},
            "eval_prompt": (
                "You are a HIPAA compliance auditor. "
                "PHI tables have not been refreshed in 30+ days. "
                "HIPAA 45 CFR 164.312(b) requires a current, accurate PHI inventory. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
        },
    ],
}


# =============================================================================
# HELPERS
# =============================================================================

def calculate_due_date(severity: str) -> str:
    days = SEVERITY_DUE_DAYS.get(severity.lower(), 14)
    return (datetime.utcnow() + timedelta(days=days)).strftime("%b %d, %Y")


def extract_dataset_from_results(query_results: list) -> str:
    datasets: set = set()
    for row in query_results:
        name = (row.get("full_name") or row.get("name")
                or row.get("table_name") or row.get("column_name"))
        if name:
            datasets.add(str(name))
    return ", ".join(sorted(datasets)) if datasets else "unknown"


def flatten(list_of_lists: list) -> list:
    return list(chain.from_iterable(list_of_lists))


def health_status(score: float) -> str:
    if score >= 90:   return "excellent"
    elif score >= 75: return "good"
    elif score >= 50: return "needs_attention"
    return "critical"


def human_time_ago(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = datetime.now(timezone.utc) - dt
    secs = int(diff.total_seconds())
    if secs < 60:        return "just now"
    elif secs < 3600:
        m = secs // 60;  return f"{m} minute{'s' if m != 1 else ''} ago"
    elif secs < 86400:
        h = secs // 3600; return f"{h} hour{'s' if h != 1 else ''} ago"
    else:
        d = secs // 86400; return f"{d} day{'s' if d != 1 else ''} ago"


def month_label(dt: datetime) -> str:
    return dt.strftime("%b")


# =============================================================================
# DATABASE MANAGER
# =============================================================================

def _build_pg_connect_kwargs() -> dict:
    dsn = os.getenv("PG_DSN")
    if dsn:
        return {"dsn": dsn}
    return {
        "host":               os.getenv("PG_HOST",     "postgres_ig"),
        "port":               int(os.getenv("PG_PORT", "5432")),
        "dbname":             os.getenv("PG_DBNAME",     "semantic_search"),
        "user":               os.getenv("PG_USER",     "semantic_user"),
        "password":           os.getenv("PG_PASSWORD", "semantic_pass"),
        "sslmode":            os.getenv("PG_SSLMODE",  "prefer"),
        "keepalives":          1,
        "keepalives_idle":     30,
        "keepalives_interval": 10,
        "keepalives_count":    5,
        "options":            "-c statement_timeout=30000",
    }


# Schema is managed by init.sql (executed at app startup via app.py).
# DDL_STATEMENTS is kept as an empty list so DatabaseManager._ensure_tables()
# is a no-op rather than raising NameError.
DDL_STATEMENTS: list = []


class DatabaseManager:
    def __init__(self, min_conn: int = 1, max_conn: int = 10):
        self._connect_kwargs = _build_pg_connect_kwargs()
        psycopg2.extras.register_default_jsonb(globally=True, loads=json.loads)
        self._pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=min_conn, maxconn=max_conn, **self._connect_kwargs
        )
        self._ensure_tables()
        logger.info("DatabaseManager: pool ready (min=%d, max=%d).", min_conn, max_conn)

    def _ensure_tables(self):
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    for stmt in DDL_STATEMENTS:
                        cur.execute(stmt)
                conn.commit()
            logger.info("DatabaseManager: all tables are ready.")
        except psycopg2.Error as exc:
            logger.error("Table setup failed [pgcode=%s]: %s", exc.pgcode, exc.pgerror)

    @contextmanager
    def _get_conn(self) -> Generator:
        conn = self._pool.getconn()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    @contextmanager
    def _cursor(self, conn) -> Generator:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield cur
        finally:
            cur.close()

    def execute_query(self, sql: str, params: Optional[dict] = None) -> list:
        try:
            with self._get_conn() as conn:
                with self._cursor(conn) as cur:
                    cur.execute(sql, params or {})
                    return [dict(row) for row in cur.fetchall()]
        except psycopg2.Error as exc:
            logger.error("execute_query [pgcode=%s]: %s | SQL: %.200s",
                         exc.pgcode, exc.pgerror, sql.strip())
            return []

    def fetch_owner_by_catalog_ids(self, catalog_ids: list) -> str:
        if not catalog_ids:
            return "Unassigned"
        uuid_ids = [str(i) for i in catalog_ids if i is not None]
        if not uuid_ids:
            return "Unassigned"
        sql = """
            SELECT DISTINCT o.name FROM owners o
            WHERE o.id IN (
                SELECT c.owner_id FROM catalogs c
                WHERE c.id = ANY(%(ids)s::uuid[]) AND c.owner_id IS NOT NULL
            )
            ORDER BY o.name
        """
        try:
            rows = self.execute_query(sql, {"ids": uuid_ids})
            names = [r["name"] for r in rows if r.get("name")]
            return ", ".join(names) if names else "Unassigned"
        except Exception as exc:
            logger.error("fetch_owner_by_catalog_ids: %s", exc)
            return "Unassigned"

    def persist_snapshot(self, dashboard: dict) -> bool:
        """
        INSERT one row into compliance_snapshots.
        Stores queryable score columns + full dashboard JSON payload.
        """
        fw_list = dashboard.get("frameworks", [])
        issues  = dashboard.get("open_issues", {})
        sev     = issues.get("severity_summary", {})

        def fw_score(name):
            match = next((f for f in fw_list if f["name"] == name), None)
            return match["score"] if match else None

        sql = """
            INSERT INTO compliance_snapshots (
                recorded_at, overall_score, overall_health_status,
                gdpr_score, soc2_score, hipaa_score,
                open_issues_count, critical_issues_count,
                high_issues_count, medium_issues_count, low_issues_count,
                snapshot_json
            ) VALUES (
                %(recorded_at)s, %(overall_score)s, %(overall_health_status)s,
                %(gdpr_score)s, %(soc2_score)s, %(hipaa_score)s,
                %(open_issues_count)s, %(critical_issues_count)s,
                %(high_issues_count)s, %(medium_issues_count)s, %(low_issues_count)s,
                %(snapshot_json)s
            )
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, {
                        "recorded_at":           dashboard.get("timestamp"),
                        "overall_score":         dashboard["overall_compliance"]["score"],
                        "overall_health_status": dashboard["overall_compliance"]["health_status"],
                        "gdpr_score":            fw_score("GDPR"),
                        "soc2_score":            fw_score("SOC2"),
                        "hipaa_score":           fw_score("HIPAA"),
                        "open_issues_count":     issues.get("count", 0),
                        "critical_issues_count": sev.get("critical", 0),
                        "high_issues_count":     sev.get("high", 0),
                        "medium_issues_count":   sev.get("medium", 0),
                        "low_issues_count":      sev.get("low", 0),
                        "snapshot_json":         psycopg2.extras.Json(dashboard),
                    })
                conn.commit()
            logger.info("persist_snapshot: saved to compliance_snapshots.")
            return True
        except psycopg2.Error as exc:
            logger.error("persist_snapshot [pgcode=%s]: %s", exc.pgcode, exc.pgerror)
            return False

    def load_latest_snapshot(self) -> Optional[dict]:
        """Return the most recent full dashboard payload."""
        sql = """
            SELECT snapshot_json, recorded_at
            FROM compliance_snapshots
            ORDER BY recorded_at DESC LIMIT 1
        """
        rows = self.execute_query(sql)
        if not rows:
            return None
        row  = rows[0]
        data = row["snapshot_json"]
        if isinstance(row.get("recorded_at"), datetime) and isinstance(data, dict):
            last_updated = human_time_ago(row["recorded_at"])
            if "overall_compliance" in data:
                data["overall_compliance"]["last_updated"] = last_updated
        return data

    def load_trend_history(self, months: int = 6) -> list:
        """One row per calendar month — max scores per month."""
        sql = """
            SELECT
                DATE_TRUNC('month', recorded_at)  AS month,
                MAX(overall_score)                AS overall,
                MAX(gdpr_score)                   AS gdpr,
                MAX(soc2_score)                   AS soc2,
                MAX(hipaa_score)                  AS hipaa
            FROM compliance_snapshots
            WHERE recorded_at >= NOW() - (%(months)s || ' months')::INTERVAL
            GROUP BY DATE_TRUNC('month', recorded_at)
            ORDER BY month ASC
        """
        rows = self.execute_query(sql, {"months": months})
        for row in rows:
            if isinstance(row.get("month"), datetime):
                row["month_label"] = month_label(row["month"])
                row["month"]       = row["month"].isoformat()
        return rows

    def get_previous_overall_score(self) -> Optional[float]:
        """Score from the second-most-recent snapshot (for change calculation)."""
        sql = """
            SELECT overall_score FROM compliance_snapshots
            ORDER BY recorded_at DESC LIMIT 2
        """
        rows = self.execute_query(sql)
        if len(rows) >= 2:
            return float(rows[1]["overall_score"])
        elif len(rows) == 1:
            return float(rows[0]["overall_score"])
        return None

    def close(self) -> None:
        self._pool.closeall()
        logger.info("DatabaseManager: pool closed.")


# =============================================================================
# LLM EVALUATOR
# =============================================================================

class LLMEvaluator:
    def __init__(self):
        self.llm = AzureChatOpenAI(
        openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        model_name=os.getenv("AZURE_OPENAI_API_MODEL_NAME"),
        temperature=0.1
    )
        logger.info("LLMEvaluator: ChatGroq ready.")

    def evaluate_rule(self, rule: dict, query_results: list) -> dict:
        if not query_results:
            return {"passed": True, "reason": "No violations found.", "severity": "low"}

        prompt = (rule["eval_prompt"] + "\n\nResults:\n"
                  + json.dumps(query_results, default=str, indent=2))
        try:
            raw = self.llm.invoke(prompt).content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw)
            return {
                "passed":   bool(parsed.get("passed", False)),
                "reason":   str(parsed.get("reason", "No reason provided.")),
                "severity": str(parsed.get("severity", "medium")).lower(),
            }
        except json.JSONDecodeError as exc:
            logger.warning("LLM non-JSON for %s: %s", rule.get("rule_id"), exc)
            return {"passed": False, "reason": "LLM returned non-JSON.", "severity": "medium"}
        except Exception as exc:
            logger.error("LLM error for %s: %s", rule.get("rule_id"), exc)
            return {"passed": False, "reason": f"LLM error: {exc}", "severity": "medium"}

    def generate_insights(self, overall_score: float, issues: list) -> str:
        prompt = (
            f"You are a compliance officer. Write a 2-3 sentence executive summary "
            f"of these compliance results, then give 3-5 prioritized remediation actions. "
            f"Be concise and direct.\n\n"
            f"Overall Score: {overall_score:.1f}%\n"
            f"Open Issues ({len(issues)}): "
            + json.dumps(issues, default=str, indent=2)
        )
        try:
            return self.llm.invoke(prompt).content.strip()
        except Exception as exc:
            logger.error("Insights generation failed: %s", exc)
            return f"Insights unavailable: {exc}"


# =============================================================================
# LANGGRAPH STATE + NODES
# =============================================================================

class ComplianceState(TypedDict):
    frameworks:    dict
    overall_score: float
    issues:        list
    insights:      str
    run_timestamp: str


def make_evaluate_frameworks_node(db: DatabaseManager, llm: LLMEvaluator, rules: dict):
    def evaluate_frameworks(state: ComplianceState) -> ComplianceState:
        logger.info("Node: evaluate_frameworks")
        for framework, fw_rules in rules.items():
            logger.info("  Framework: %s", framework)
            passed_count = 0
            fw_issues    = []

            for rule in fw_rules:
                rule_id = rule.get("rule_id", "UNKNOWN")
                logger.info("    Evaluating %s ...", rule_id)
                query_results = db.execute_query(rule["sql"], rule.get("sql_params") or {})
                eval_result   = llm.evaluate_rule(rule, query_results)

                if eval_result["passed"]:
                    passed_count += 1
                    logger.info("      PASSED")
                else:
                    logger.info("      FAILED  severity=%s", eval_result["severity"])
                    catalog_ids = [
                        row.get("id") or row.get("catalog_id")
                        for row in query_results
                        if row.get("id") or row.get("catalog_id")
                    ]
                    fw_issues.append({
                        "issue":         rule["rule"],
                        "rule_id":       rule_id,
                        "framework":     framework,
                        "severity":      eval_result["severity"].upper(),
                        "reason":        eval_result["reason"],
                        "dataset":       extract_dataset_from_results(query_results),
                        "assignee":      db.fetch_owner_by_catalog_ids(catalog_ids),
                        "due_date":      calculate_due_date(eval_result["severity"]),
                        "affected_rows": len(query_results),
                        "action_url":    f"/issues/{rule_id}",
                    })

            score = round((passed_count / len(fw_rules)) * 100, 2) if fw_rules else 0.0
            logger.info("  %s: %.1f%%  (%d/%d passed, %d issue(s))",
                        framework, score, passed_count, len(fw_rules), len(fw_issues))
            state["frameworks"][framework] = {
                "score":        score,
                "issues":       fw_issues,
                "rules_total":  len(fw_rules),
                "rules_passed": passed_count,
            }
        return state
    return evaluate_frameworks


def aggregate_scores_node(state: ComplianceState) -> ComplianceState:
    logger.info("Node: aggregate_scores")
    scores = [d["score"] for d in state["frameworks"].values()]
    state["overall_score"] = round(sum(scores) / len(scores), 2) if scores else 0.0
    state["issues"] = flatten([d["issues"] for d in state["frameworks"].values()])
    logger.info("Overall: %s%%  |  Issues: %d", state["overall_score"], len(state["issues"]))
    return state


def make_generate_insights_node(llm: LLMEvaluator):
    def generate_insights(state: ComplianceState) -> ComplianceState:
        logger.info("Node: generate_insights")
        state["insights"] = llm.generate_insights(state["overall_score"], state["issues"])
        return state
    return generate_insights


# =============================================================================
# COMPLIANCE ENGINE
# =============================================================================

class ComplianceEngine:
    def __init__(self, db: DatabaseManager, llm: LLMEvaluator,
                 framework_rules: Optional[dict] = None):
        self.db  = db
        self.llm = llm
        self.framework_rules = framework_rules or FRAMEWORK_RULES
        self.graph = self._build_graph()

    def _build_graph(self):
        wf = StateGraph(ComplianceState)
        wf.add_node("evaluate_frameworks",
                    make_evaluate_frameworks_node(self.db, self.llm, self.framework_rules))
        wf.add_node("aggregate_scores",  aggregate_scores_node)
        wf.add_node("generate_insights", make_generate_insights_node(self.llm))
        wf.set_entry_point("evaluate_frameworks")
        wf.add_edge("evaluate_frameworks", "aggregate_scores")
        wf.add_edge("aggregate_scores",    "generate_insights")
        wf.add_edge("generate_insights",   END)
        return wf.compile()

    def run(self) -> dict:
        logger.info("=" * 60)
        logger.info("ComplianceEngine: run started.")
        run_ts = datetime.now(IST)

        initial: ComplianceState = {
            "frameworks":    {},
            "overall_score": 0.0,
            "issues":        [],
            "insights":      "",
            "run_timestamp": run_ts.isoformat(),
        }

        final    = self.graph.invoke(initial)
        dashboard = self._build_dashboard(final, run_ts)
        self.db.persist_snapshot(dashboard)

        logger.info("ComplianceEngine: complete. Score=%.1f%%", final["overall_score"])
        logger.info("=" * 60)
        return dashboard

    # -------------------------------------------------------------------------
    def _build_dashboard(self, state: ComplianceState, run_ts: datetime) -> dict:
        """Build the exact dashboard response format from LangGraph final state."""

        overall  = state["overall_score"]
        issues   = state["issues"]
        fw_data  = state["frameworks"]

        # Severity counts
        sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            key = issue.get("severity", "low").lower()
            sev_counts[key] = sev_counts.get(key, 0) + 1

        # Change vs previous snapshot
        prev_score = self.db.get_previous_overall_score()
        change     = round(overall - prev_score, 1) if prev_score is not None else 0.0

        # Trend data — 6 months history from DB + current run
        trend_rows    = self.db.load_trend_history(months=6)
        labels        = [r.get("month_label", "?") for r in trend_rows]
        overall_data  = [float(r.get("overall") or 0) for r in trend_rows]
        gdpr_data     = [float(r.get("gdpr")    or 0) for r in trend_rows]
        soc2_data     = [float(r.get("soc2")    or 0) for r in trend_rows]
        hipaa_data    = [float(r.get("hipaa")   or 0) for r in trend_rows]

        cur_month = month_label(run_ts)
        # Avoid duplicate month label if last DB row is same month
        if not labels or labels[-1] != cur_month:
            labels.append(cur_month)
            overall_data.append(overall)
            gdpr_data.append(fw_data.get("GDPR",  {}).get("score", 0))
            soc2_data.append(fw_data.get("SOC2",  {}).get("score", 0))
            hipaa_data.append(fw_data.get("HIPAA", {}).get("score", 0))
        else:
            # Update the last entry for the current month
            overall_data[-1] = overall
            gdpr_data[-1]    = fw_data.get("GDPR",  {}).get("score", 0)
            soc2_data[-1]    = fw_data.get("SOC2",  {}).get("score", 0)
            hipaa_data[-1]   = fw_data.get("HIPAA", {}).get("score", 0)

        # Trend label: change since previous data point
        trend_pct  = round(overall_data[-1] - (overall_data[-2] if len(overall_data) >= 2 else overall_data[-1]), 1)
        trend_sign = "+" if trend_pct >= 0 else ""

        # Framework indicators: one entry per rule, success/error based on pass/fail
        def build_indicators(fw_name: str) -> list:
            failed_ids = {i["rule_id"] for i in fw_data.get(fw_name, {}).get("issues", [])}
            return [
                {
                    "text":   rule["rule"],
                    "status": "error" if rule["rule_id"] in failed_ids else "success",
                }
                for rule in FRAMEWORK_RULES.get(fw_name, [])
            ]

        def framework_details(fw_name: str) -> str:
            fw     = fw_data.get(fw_name, {})
            passed = fw.get("rules_passed", 0)
            total  = fw.get("rules_total",  0)
            failed = fw.get("issues", [])
            if failed:
                return f"{passed} of {total} Policies ({len(failed)} issue(s))"
            return f"{passed} of {total} Policies"

        # Final response — exact format requested (without colors)
        return {
            "timestamp": run_ts.isoformat(),

            "overall_compliance": {
                "score":                 overall,
                "change_from_last_month": change,
                "health_status":         health_status(overall),
                "last_updated":          "just now",
            },

            "compliance_health": {
                "score":       overall,
                "trend_label": f"{trend_sign}{trend_pct}% Overall",
            },

            "trends": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Overall",
                        "data":  overall_data,
                    },
                    {
                        "label": "GDPR",
                        "data":  gdpr_data,
                    },
                    {
                        "label": "SOC2",
                        "data":  soc2_data,
                    },
                    {
                        "label": "HIPAA",
                        "data":  hipaa_data,
                    },
                ],
            },

            "frameworks": [
                {
                    "name":         fw_name,
                    "score":        fw_data.get(fw_name, {}).get("score", 0),
                    "status":       health_status(fw_data.get(fw_name, {}).get("score", 0)),
                    "details":      framework_details(fw_name),
                    "last_checked": "just now",
                    "indicators":   build_indicators(fw_name),
                }
                for fw_name in FRAMEWORK_RULES
            ],

            "open_issues": {
                "count":            len(issues),
                "severity_summary": sev_counts,
                "items": [
                    {
                        "issue":      i["issue"],
                        "framework":  i["framework"],
                        "severity":   i["severity"],
                        "dataset":    i["dataset"],
                        "assignee":   i["assignee"],
                        "due_date":   i["due_date"],
                        "action_url": i.get("action_url", f"/issues/{i['rule_id']}"),
                    }
                    for i in issues
                ],
            },

            "ai_insights": {
                "text": state["insights"],
                "beta": True,
            },

            "quick_actions": QUICK_ACTIONS,
        }


# =============================================================================
# FASTAPI APP
# =============================================================================

_db:     Optional[DatabaseManager]  = None
_llm:    Optional[LLMEvaluator]     = None
_engine: Optional[ComplianceEngine] = None


def get_engine() -> ComplianceEngine:
    """Lazily initialise the compliance engine on first use."""
    global _db, _llm, _engine
    if _engine is None:
        logger.info("Compliance: initialising engine...")
        _db     = DatabaseManager(min_conn=1, max_conn=10)
        _llm    = LLMEvaluator()
        _engine = ComplianceEngine(db=_db, llm=_llm)
        logger.info("Compliance: engine ready.")
    return _engine


# CORS is handled globally in app.py — no middleware needed here

# ── FastAPI Router ─────────────────────────────────────────────────────────────
router = APIRouter(
    prefix="/api/compliance",
    tags=["Compliance"]
)


# ── GET /health ───────────────────────────────────────────────────────────────

@router.get("/health", tags=["System"])
def health_check():
    """Liveness check."""
    return {
        "status":    "ok",
        "timestamp": datetime.now(IST).isoformat(),
        "service":   "compliance-dashboard-api",
    }


# ── GET /api/compliance/overview ───────────────────────────────────────────────────

@router.get("/overview", tags=["Compliance"])
def run_compliance_scan():
    """
    Trigger a **full compliance scan**.

    Runs GDPR, SOC2, and HIPAA rules against your database, generates AI insights,
    persists the result to `compliance_snapshots`, and returns the dashboard response.

    This endpoint may take **15–60 seconds** depending on LLM latency.
    """
    try:
        engine = get_engine()
        result = engine.run()
        return JSONResponse(content=result)
    except Exception as exc:
        logger.exception("Compliance scan failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Scan failed: {exc}")

# ── GET /api/compliance/summary ───────────────────────────────────────────────

@router.get("/summary", tags=["Compliance"])
def get_compliance_summary():
    """
    Returns a summary card from the latest compliance_snapshots row:
      - frameworks_scanned  → count of frameworks in snapshot_json
      - issues_found        → open_issues_count column
      - policies_checked    → parsed from details string "X of Y Policies"
      - overall_score       → overall_score column
    """
    engine = get_engine()

    sql = """
        SELECT
            overall_score,
            open_issues_count,
            snapshot_json
        FROM compliance_snapshots
        ORDER BY recorded_at DESC
        LIMIT 1
    """

    rows = engine.db.execute_query(sql)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No compliance snapshot found. Run a scan first."
        )

    row        = rows[0]
    snapshot   = row["snapshot_json"]
    frameworks = snapshot.get("frameworks", [])

    # Count of distinct frameworks
    frameworks_scanned = len(frameworks)
    # Build issue_summary sentence from live data
    issue_summary = (
        f"Compliance scan finished. {row['open_issues_count']} issue"
        f"{'s' if row['open_issues_count'] != 1 else ''} found across "
        f"{frameworks_scanned} framework"
        f"{'s' if frameworks_scanned != 1 else ''}. "
        f"Overall score: {float(row['overall_score']):.0f}%."
    )

    REASONING_STEPS = [
    {
        "title": "Initializing compliance engine",
        "description": "Loading policy definitions and rule sets"
    },
    {
        "title": "Scanning GDPR policies",
        "description": "Checking 24 policies across EU data regulations"
    },
    {
        "title": "Scanning SOC 2 controls",
        "description": "Verifying 32 security and availability controls"
    },
    {
        "title": "Scanning HIPAA requirements",
        "description": "Auditing PHI handling and access controls"
    },
    {
        "title": "Scanning DPDPA regulations",
        "description": "Reviewing India data protection compliance"
    },
    {
        "title": "Scanning EU AI Act",
        "description": "Evaluating AI model governance requirements"
    },
    {
        "title": "Generating compliance report",
        "description": "Compiling findings and recommendations"
    },
]
    # Parse "X of Y Policies" from each framework's details string
    policies_checked = 0
    for fw in frameworks:
        details = fw.get("details", "")
        match = re.search(r"of\s+(\d+)\s+Policies", details)
        if match:
            policies_checked += int(match.group(1))

    return JSONResponse(content={
        "timestamp": datetime.now(IST).isoformat(),
        "summary": {
            "frameworks_scanned": frameworks_scanned,
            "issues_found":       row["open_issues_count"],
            "policies_checked":   policies_checked,
            "overall_score":      float(row["overall_score"]),
            "issue_summary":      issue_summary,
        },
        "reasoning":REASONING_STEPS
    })

@router.get("/loading", tags=["Compliance"])
def get_loading_compliance():
    REASONING_LOAD = [
        "Initializing compliance engine",
        "Scanning GDPR policies",
        "Scanning SOC 2 controls",
        "Scanning HIPAA requirements",
        "Scanning DPDPA regulations",
        "Scanning EU AI Act",
        "Generating compliance report"
]
    return {
        "reasoning_loads":REASONING_LOAD
    }




# ── Colour palette ─────────────────────────────────────────────────────────────
DARK_BLUE   = colors.HexColor("#1A2B4A")
MID_BLUE    = colors.HexColor("#2563EB")
LIGHT_BLUE  = colors.HexColor("#EFF6FF")
GREEN       = colors.HexColor("#16A34A")
GREEN_BG    = colors.HexColor("#F0FDF4")
RED         = colors.HexColor("#DC2626")
RED_BG      = colors.HexColor("#FEF2F2")
ORANGE      = colors.HexColor("#D97706")
ORANGE_BG   = colors.HexColor("#FFFBEB")
GREY_TEXT   = colors.HexColor("#6B7280")
GREY_LIGHT  = colors.HexColor("#F3F4F6")
GREY_BORDER = colors.HexColor("#E5E7EB")
WHITE       = colors.white
BLACK       = colors.HexColor("#111827")


# ── PDF Styles ─────────────────────────────────────────────────────────────────
def _styles():
    return {
        "title": ParagraphStyle("title", fontSize=22, textColor=WHITE,
                                fontName="Helvetica-Bold", alignment=TA_LEFT, leading=28),
        "subtitle": ParagraphStyle("subtitle", fontSize=10, textColor=colors.HexColor("#BFDBFE"),
                                   fontName="Helvetica", alignment=TA_LEFT),
        "section_head": ParagraphStyle("section_head", fontSize=13, textColor=DARK_BLUE,
                                       fontName="Helvetica-Bold", spaceAfter=6, leading=18),
        "body": ParagraphStyle("body", fontSize=9, textColor=BLACK,
                               fontName="Helvetica", leading=14),
        "small": ParagraphStyle("small", fontSize=8, textColor=GREY_TEXT,
                                fontName="Helvetica", leading=12),
        "bold_small": ParagraphStyle("bold_small", fontSize=8, textColor=BLACK,
                                     fontName="Helvetica-Bold", leading=12),
        "indicator": ParagraphStyle("indicator", fontSize=8.5, textColor=BLACK,
                                    fontName="Helvetica", leading=13),
        "insight": ParagraphStyle("insight", fontSize=8.5, textColor=BLACK,
                                  fontName="Helvetica", leading=14, spaceAfter=4),
        "insight_bold": ParagraphStyle("insight_bold", fontSize=9, textColor=DARK_BLUE,
                                       fontName="Helvetica-Bold", leading=14, spaceAfter=2),
        "footer": ParagraphStyle("footer", fontSize=8, textColor=GREY_TEXT,
                                 fontName="Helvetica", alignment=TA_CENTER),
    }


def _status_color(status: str):
    s = (status or "").lower()
    if s in ("critical", "error"):
        return RED, RED_BG
    if s in ("needs_attention", "warning"):
        return ORANGE, ORANGE_BG
    if s in ("excellent", "success"):
        return GREEN, GREEN_BG
    return MID_BLUE, LIGHT_BLUE


def _score_color(score: float):
    if score >= 90:
        return GREEN
    if score >= 60:
        return ORANGE
    return RED


# ── PDF Sections ───────────────────────────────────────────────────────────────
def _header_table(snapshot, st):
    recorded = snapshot.get("recorded_at", datetime.utcnow())
    ts_str = recorded.strftime("%Y-%m-%d %H:%M UTC") if hasattr(recorded, "strftime") else str(recorded)

    left = [
        Paragraph("Compliance Report", st["title"]),
        Spacer(1, 4),
        Paragraph("Data Governance Health &amp; Activities", st["subtitle"]),
        Spacer(1, 4),
        Paragraph(f"Generated: {ts_str}", st["subtitle"]),
    ]
    right_text = ParagraphStyle("rt", fontSize=9, textColor=colors.HexColor("#BFDBFE"),
                                fontName="Helvetica", alignment=TA_RIGHT)
    right = [
        Paragraph("Report Period: Latest Snapshot", right_text),
        Paragraph(f"Record ID: {str(snapshot.get('id', ''))[:8]}...", right_text),
    ]
    t = Table([[left, right]], colWidths=[110*mm, 70*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), DARK_BLUE),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (0,  0),  10*mm),
        ("RIGHTPADDING", (1, 0), (1,  0),  8*mm),
        ("TOPPADDING",   (0, 0), (-1, -1), 8*mm),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8*mm),
    ]))
    return t


def _overall_score_table(snapshot, st):
    overall = float(snapshot.get("overall_score", 0))
    status  = snapshot.get("overall_health_status", "")
    fg, bg  = _status_color(status)
    sc      = _score_color(overall)

    score_cell = [
        Paragraph(f'<font color="#{sc.hexval()[2:]}"><b>{overall:.1f}%</b></font>',
                  ParagraphStyle("sc", fontSize=36, fontName="Helvetica-Bold",
                                 alignment=TA_CENTER, leading=42)),
        Paragraph("Overall Compliance Score",
                  ParagraphStyle("sl", fontSize=10, fontName="Helvetica-Bold",
                                 textColor=DARK_BLUE, alignment=TA_CENTER)),
        Spacer(1, 4),
        Paragraph(status.replace("_", " ").title(),
                  ParagraphStyle("ss", fontSize=9, fontName="Helvetica-Bold",
                                 textColor=fg, alignment=TA_CENTER)),
    ]

    sev_data = [
        [Paragraph("<b>Open Issues Summary</b>", st["bold_small"]), ""],
        ["Total Open Issues", str(snapshot.get("open_issues_count", 0))],
        ["Critical",         str(snapshot.get("critical_issues_count", 0))],
        ["High",             str(snapshot.get("high_issues_count", 0))],
        ["Medium",           str(snapshot.get("medium_issues_count", 0))],
        ["Low",              str(snapshot.get("low_issues_count", 0))],
    ]
    sev_table = Table(sev_data, colWidths=[55*mm, 20*mm])
    sev_table.setStyle(TableStyle([
        ("SPAN",         (0, 0), (1, 0)),
        ("BACKGROUND",   (0, 0), (1, 0), GREY_LIGHT),
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR",    (1, 2), (1, 2),  RED),
        ("FONTNAME",     (1, 2), (1, 2),  "Helvetica-Bold"),
        ("GRID",         (0, 0), (-1, -1), 0.5, GREY_BORDER),
        ("ROWBACKGROUNDS",(0,1), (-1, -1), [WHITE, GREY_LIGHT]),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))

    outer = Table([[score_cell, sev_table]], colWidths=[80*mm, 100*mm])
    outer.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (0, 0), bg),
        ("BACKGROUND",   (1, 0), (1, 0), WHITE),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("BOX",          (0, 0), (-1, -1), 1, GREY_BORDER),
        ("LINEAFTER",    (0, 0), (0, 0),   1, GREY_BORDER),
        ("TOPPADDING",   (0, 0), (-1, -1), 6*mm),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6*mm),
        ("LEFTPADDING",  (0, 0), (0, 0),   6*mm),
        ("LEFTPADDING",  (1, 0), (1, 0),   5*mm),
    ]))
    return outer


def _framework_cards(frameworks, st):
    elements = []
    elements.append(Paragraph("Framework Compliance Status", st["section_head"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=GREY_BORDER, spaceAfter=6))

    for fw in frameworks:
        name    = fw.get("name", "")
        score   = float(fw.get("score", 0))
        status  = fw.get("status", "")
        details = fw.get("details", "")
        fg, bg  = _status_color(status)
        sc      = _score_color(score)

        pill = Table([[Paragraph(f'<b>{score:.1f}%</b>',
                                 ParagraphStyle("p", fontSize=11, textColor=sc,
                                                fontName="Helvetica-Bold", alignment=TA_CENTER))]],
                     colWidths=[22*mm])
        pill.setStyle(TableStyle([
            ("BACKGROUND",   (0,0),(-1,-1), GREY_LIGHT),
            ("BOX",          (0,0),(-1,-1), 1, GREY_BORDER),
            ("TOPPADDING",   (0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ]))

        badge = Table([[Paragraph(status.replace("_", " ").title(),
                                  ParagraphStyle("b", fontSize=8, textColor=fg,
                                                 fontName="Helvetica-Bold", alignment=TA_CENTER))]],
                      colWidths=[30*mm])
        badge.setStyle(TableStyle([
            ("BACKGROUND",   (0,0),(-1,-1), bg),
            ("BOX",          (0,0),(-1,-1), 0.5, fg),
            ("TOPPADDING",   (0,0),(-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ]))

        header_row = Table([
            [Paragraph(f"<b>{name}</b>",
                       ParagraphStyle("fn", fontSize=12, textColor=DARK_BLUE,
                                      fontName="Helvetica-Bold")),
             pill, badge,
             Paragraph(details, st["small"])]
        ], colWidths=[35*mm, 25*mm, 33*mm, 87*mm])
        header_row.setStyle(TableStyle([
            ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
            ("LEFTPADDING",  (0,0),(0,0), 0),
            ("RIGHTPADDING", (0,0),(-1,-1), 4),
        ]))

        ind_rows = []
        for ind in fw.get("indicators", []):
            ist    = ind.get("status", "")
            ifg, _ = _status_color(ist)
            icon   = "✓" if ist == "success" else "✗"
            ind_rows.append([
                Paragraph(f'<font color="#{ifg.hexval()[2:]}"><b>{icon}</b></font>',
                          ParagraphStyle("ic", fontSize=10, fontName="Helvetica-Bold",
                                         alignment=TA_CENTER)),
                Paragraph(ind.get("text", ""), st["indicator"]),
                Paragraph(ist.upper(),
                          ParagraphStyle("is", fontSize=7.5, textColor=ifg,
                                         fontName="Helvetica-Bold", alignment=TA_CENTER)),
            ])

        ind_table = Table(ind_rows, colWidths=[8*mm, 148*mm, 24*mm])
        ind_table.setStyle(TableStyle([
            ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
            ("ROWBACKGROUNDS",(0,0),(-1,-1), [WHITE, GREY_LIGHT]),
            ("TOPPADDING",   (0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
            ("LEFTPADDING",  (1,0),(1,-1),  4),
            ("BOX",          (0,0),(-1,-1), 0.5, GREY_BORDER),
            ("LINEBELOW",    (0,0),(-1,-2), 0.3, GREY_BORDER),
        ]))

        card = Table([[header_row], [Spacer(1, 4)], [ind_table]], colWidths=[180*mm])
        card.setStyle(TableStyle([
            ("BOX",          (0,0),(-1,-1), 1, GREY_BORDER),
            ("BACKGROUND",   (0,0),(-1,-1), WHITE),
            ("TOPPADDING",   (0,0),(-1,-1), 4*mm),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4*mm),
            ("LEFTPADDING",  (0,0),(-1,-1), 4*mm),
            ("RIGHTPADDING", (0,0),(-1,-1), 4*mm),
        ]))

        elements.append(KeepTogether(card))
        elements.append(Spacer(1, 5*mm))

    return elements


def _open_issues_table(issues, st):
    elements = []
    elements.append(Paragraph("Open Issues", st["section_head"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=GREY_BORDER, spaceAfter=6))

    if not issues:
        elements.append(Paragraph("No open issues found.", st["body"]))
        return elements

    header = [
        Paragraph("<b>#</b>",         st["bold_small"]),
        Paragraph("<b>Issue</b>",      st["bold_small"]),
        Paragraph("<b>Framework</b>",  st["bold_small"]),
        Paragraph("<b>Severity</b>",   st["bold_small"]),
        Paragraph("<b>Dataset</b>",    st["bold_small"]),
        Paragraph("<b>Due Date</b>",   st["bold_small"]),
    ]
    rows = [header]
    for i, issue in enumerate(issues, 1):
        sev    = issue.get("severity", "")
        fg, _  = _status_color(sev)
        dataset = issue.get("dataset", "")
        rows.append([
            Paragraph(str(i), st["small"]),
            Paragraph(issue.get("issue", ""), st["small"]),
            Paragraph(issue.get("framework", ""), st["small"]),
            Paragraph(sev, ParagraphStyle("sv", fontSize=7.5, textColor=fg,
                                          fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph(dataset[:120] + ("..." if len(dataset) > 120 else ""), st["small"]),
            Paragraph(issue.get("due_date", ""), st["small"]),
        ])

    t = Table(rows, colWidths=[8*mm, 55*mm, 20*mm, 18*mm, 55*mm, 24*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, GREY_LIGHT]),
        ("GRID",         (0, 0), (-1,-1), 0.4, GREY_BORDER),
        ("VALIGN",       (0, 0), (-1,-1), "TOP"),
        ("TOPPADDING",   (0, 0), (-1,-1), 4),
        ("BOTTOMPADDING",(0, 0), (-1,-1), 4),
        ("LEFTPADDING",  (0, 0), (-1,-1), 4),
        ("RIGHTPADDING", (0, 0), (-1,-1), 4),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 8),
    ]))
    elements.append(t)
    return elements


def _ai_insights_section(ai_text, st):
    elements = []
    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph("AI Insights", st["section_head"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=GREY_BORDER, spaceAfter=6))

    inner = []
    for line in ai_text.split("\n"):
        line = line.strip()
        if not line:
            inner.append(Spacer(1, 3))
            continue
        if line.startswith("**") and line.endswith("**"):
            inner.append(Paragraph(line.replace("**", ""), st["insight_bold"]))
        elif "**" in line:
            clean = line.replace("**", "<b>", 1).replace("**", "</b>", 1)
            inner.append(Paragraph(clean, st["insight"]))
        else:
            inner.append(Paragraph(line, st["insight"]))

    box = Table([[inner]], colWidths=[180*mm])
    box.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), LIGHT_BLUE),
        ("BOX",          (0,0),(-1,-1), 1, MID_BLUE),
        ("TOPPADDING",   (0,0),(-1,-1), 5*mm),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5*mm),
        ("LEFTPADDING",  (0,0),(-1,-1), 5*mm),
        ("RIGHTPADDING", (0,0),(-1,-1), 5*mm),
    ]))
    elements.append(box)
    return elements


def generate_compliance_pdf(snapshot: dict) -> bytes:
    buf  = io.BytesIO()
    doc  = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=15*mm, rightMargin=15*mm,
                             topMargin=12*mm,  bottomMargin=18*mm,
                             title="Compliance Report",
                             author="Data Governance Platform")
    st      = _styles()
    snap    = snapshot.get("snapshot_json", {})
    fw_list = snap.get("frameworks", [])
    issues  = snap.get("open_issues", {}).get("items", [])
    ai_text = snap.get("ai_insights", {}).get("text", "")

    story = []
    story.append(_header_table(snapshot, st))
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("Executive Summary", st["section_head"]))
    story.append(HRFlowable(width="100%", thickness=1, color=GREY_BORDER, spaceAfter=6))
    story.append(_overall_score_table(snapshot, st))
    story.append(Spacer(1, 6*mm))

    story.extend(_framework_cards(fw_list, st))
    story.extend(_open_issues_table(issues, st))
    story.append(Spacer(1, 6*mm))

    if ai_text:
        story.extend(_ai_insights_section(ai_text, st))

    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY_BORDER))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        f"Generated by Data Governance Platform &nbsp;|&nbsp; "
        f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} &nbsp;|&nbsp; Confidential",
        st["footer"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()



def fetch_latest_snapshot():
    rows = get_engine().db.execute_query("""
        SELECT * FROM public.compliance_snapshots
        ORDER BY recorded_at DESC
        LIMIT 1
    """)
    if not rows:
        return None
    data = dict(rows[0])
    if isinstance(data.get("snapshot_json"), str):
        data["snapshot_json"] = json.loads(data["snapshot_json"])
    return data


@router.get(
    "/report/export",
    summary="Export Report",
    description="Export the latest compliance snapshot as a downloadable PDF.",
    response_description="Export Report",
    tags=["Compliance"],
    responses={
        200: {
            "description": "Export Report",
            "content": {"application/pdf": {}},
        }
    },
)
def export_compliance_report():
    snapshot = fetch_latest_snapshot()
    if not snapshot:
        raise HTTPException(status_code=404, detail="No compliance snapshot found in database.")

    pdf_bytes = generate_compliance_pdf(snapshot)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"compliance_report_{timestamp}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )