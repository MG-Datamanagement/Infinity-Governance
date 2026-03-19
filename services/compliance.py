# =============================================================================
#  COMPLIANCE ENGINE — GDPR-Only with Detection & Reporting (NO AUTO-FIX)
#
#  GDPR Rules (detection & reporting only - NO AUTO-FIX):
#    - GDPR-001: AI generates retention policy descriptions for PII catalogs ✓
#    - GDPR-002: User-provided source ID → assign owners to catalogs ✓
#    - GDPR-003: All catalogs must have governance metadata ✓
#    - GDPR-004: Catalogs must have last_seen_at tracking ✓
#    - GDPR-005: Cross-database PII catalogs require DPIA documentation ✓
#    - GDPR-007: Catalog metadata audit timestamps must be current ✓
#    - GDPR-008: Source data lineage must be tracked ✓
#    - GDPR-009: Schema isolation must be enforced for personal data ✓
#    - GDPR-010: Orphaned catalogs must be assigned or marked for deletion ✓
# =============================================================================

import io
import json
import logging
import os
import re
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from itertools import chain
from typing import Any, Dict, Generator, List, Optional, TypedDict
from langchain_openai import AzureChatOpenAI
from langchain.prompts import PromptTemplate
from fastapi import FastAPI, HTTPException, APIRouter
import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langgraph.graph import END, StateGraph
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

IST = timezone.utc



# =============================================================================
# CONSTANTS
# =============================================================================

QUICK_ACTIONS = [
    {"label": "Run Full Scan",  "action": "run_full_scan"},
    {"label": "Export Report",  "action": "export_report"},
]

SEVERITY_DUE_DAYS = {"critical": 3, "high": 7, "medium": 14, "low": 30}

# Colour palette for PDF
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

# =============================================================================
# AI PROMPT TEMPLATES (For insights & descriptions only - NO AUTO-FIX)
# =============================================================================

GDPR_DESCRIPTION_GENERATOR = PromptTemplate(
    input_variables=["table_name", "columns"],
    template="""
You are a GDPR compliance expert. Generate a recommended retention policy description for a PII data table.
This is for REFERENCE ONLY - not auto-applied.

Table Name: {table_name}
Columns: {columns}

Write a single-paragraph description (max 150 words) that covers:
1. Data retention period (recommend 3-7 years depending on regulation)
2. Processing purpose under GDPR Article 5(1)(a)
3. Legal basis for processing
4. Data subject rights
5. Disposal/archival procedures

Format: Professional, technical, suitable for data governance records.
Example: "Customer transaction data retained for 7 years per financial regulations. Processing based on
legitimate business interest for fraud prevention and regulatory compliance. Data subjects can exercise
access, rectification, and erasure rights. Data archived after 7 years and securely destroyed."

Generate recommended description for the table:
"""
)

# =============================================================================
# FRAMEWORK RULES — GDPR ONLY (001-010, excl. 006) - DETECTION ONLY
# =============================================================================

FRAMEWORK_RULES: dict = {

    "GDPR": [
        # ------------------------------------------------------------------
        # GDPR-001
        # ------------------------------------------------------------------
        {
            "rule_id": "GDPR-001",
            "rule": "PII/sensitive catalogs must have a retention policy description",
            "description": (
                "All catalogs tagged as PII, sensitive, or containing personal data must have a "
                "documented description explaining retention policies and processing purposes per "
                "GDPR Article 5(1)(e)"
            ),
            "sql": """
                SELECT c.id, c.table_name AS name, c.full_name, c.schema_name,
                       c.database_name, c.description, c.owner_id,
                       t.name AS tag_name, c.updated_at
                FROM catalogs c
                JOIN tag_catalog_assignments tca ON tca.catalog_id = c.id
                JOIN tags t ON t.id = tca.tag_id
                WHERE LOWER(t.name) = ANY(%(tags)s)
                  AND (c.description IS NULL OR c.description = '')
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
            "gdpr_article": "5(1)(e)",
            "severity": "critical",
        },
        # ------------------------------------------------------------------
        # GDPR-002
        # ------------------------------------------------------------------
        {
            "rule_id": "GDPR-002",
            "rule": "PII/sensitive catalogs must have an assigned owner (data steward accountability)",
            "description": (
                "All catalogs containing personal data must have an assigned owner/data steward "
                "for accountability per GDPR Article 5(2) and GDPR Article 4(7)"
            ),
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
            "gdpr_article": "5(2)",
            "severity": "critical",
        },
        # ------------------------------------------------------------------
        # GDPR-003
        # ------------------------------------------------------------------
        {
            "rule_id": "GDPR-003",
            "rule": "All catalogs must have metadata tracking for data governance",
            "description": (
                "GDPR Article 5(1)(a) requires documented lawful basis. Metadata field must "
                "contain governance info including processing purpose, lawful basis, and data categories"
            ),
            "sql": """
                SELECT c.id, c.table_name AS name, c.full_name, c.schema_name,
                       c.database_name, c.metadata, c.description, c.owner_id,
                       c.created_at, c.updated_at
                FROM catalogs c
                WHERE c.metadata IS NULL
                   OR (c.metadata::text = 'null'::text)
                   OR (c.metadata @> '{"lawful_basis": null}'::jsonb)
                   OR (c.metadata @> '{"processing_purpose": null}'::jsonb)
                ORDER BY c.created_at DESC LIMIT 100
            """,
            "sql_params": {},
            "eval_prompt": (
                "You are a GDPR compliance auditor. "
                "These tables lack complete governance metadata. "
                "GDPR Article 5(1)(a) requires documented lawful basis for all processing. "
                "Metadata must include: lawful_basis, processing_purpose, and data_categories. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
            "gdpr_article": "5(1)(a)",
            "severity": "high",
        },
        # ------------------------------------------------------------------
        # GDPR-004
        # ------------------------------------------------------------------
        {
            "rule_id": "GDPR-004",
            "rule": "Catalogs must have last_seen_at tracking for data lifecycle management",
            "description": (
                "GDPR Article 5(1)(e) requires storage limitation principle - data must not be "
                "kept longer than necessary. last_seen_at tracking enables data cleanup automation"
            ),
            "sql": """
                SELECT c.id, c.table_name AS name, c.full_name, c.schema_name,
                       c.database_name, c.last_seen_at, c.owner_id,
                       EXTRACT(DAY FROM NOW() - c.last_seen_at) AS days_since_access
                FROM catalogs c
                WHERE c.last_seen_at IS NULL
                   OR c.last_seen_at < NOW() - INTERVAL '90 days'
                ORDER BY c.last_seen_at ASC NULLS FIRST LIMIT 100
            """,
            "sql_params": {},
            "eval_prompt": (
                "You are a GDPR compliance auditor. "
                "These tables have not been accessed recently (>90 days) or have no access tracking. "
                "GDPR Article 5(1)(e) storage limitation principle requires periodic review of inactive data. "
                "Data retention policies must be enforced. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
            "gdpr_article": "5(1)(e)",
            "severity": "medium",
        },
        # ------------------------------------------------------------------
        # GDPR-005
        # ------------------------------------------------------------------
        {
            "rule_id": "GDPR-005",
            "rule": "Cross-database personal data catalogs require privacy impact assessment documentation",
            "description": (
                "GDPR Article 35 requires DPIA for cross-database personal data processing. "
                "Database replication or federation of PII requires formal assessment"
            ),
            "sql": """
                SELECT c.id, c.table_name AS name, c.full_name, c.schema_name,
                       c.database_name, c.description, c.owner_id,
                       COUNT(*) OVER (PARTITION BY c.source_id) AS tables_in_source,
                       t.name AS tag_name, c.metadata
                FROM catalogs c
                JOIN tag_catalog_assignments tca ON tca.catalog_id = c.id
                JOIN tags t ON t.id = tca.tag_id
                WHERE LOWER(t.name) = ANY(%(tags)s)
                  AND c.database_name IS NOT NULL
                  AND (
                    c.metadata IS NULL
                    OR (c.metadata @> '{"dpia_completed": false}'::jsonb)
                    OR NOT (c.metadata ? 'dpia_initiated_at')
                  )
                ORDER BY c.full_name LIMIT 100
            """,
            "sql_params": {"tags": ["pii", "personal data", "sensitive"]},
            "eval_prompt": (
                "You are a GDPR compliance auditor. "
                "These PII/personal data tables span multiple databases without documented DPIA. "
                "GDPR Article 35 mandates Data Protection Impact Assessment for cross-database "
                "personal data processing due to high risk. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
            "gdpr_article": "35",
            "severity": "critical",
        },
        # ------------------------------------------------------------------
        # GDPR-007
        # ------------------------------------------------------------------
        {
            "rule_id": "GDPR-007",
            "rule": "Catalog metadata audit timestamps must be current",
            "description": (
                "GDPR Article 32 requires updated security and governance measures. "
                "Stale metadata indicates lack of active data governance"
            ),
            "sql": """
                SELECT c.id, c.table_name AS name, c.full_name, c.schema_name,
                       c.database_name, c.updated_at, c.owner_id,
                       EXTRACT(DAY FROM NOW() - c.updated_at) AS days_since_update
                FROM catalogs c
                WHERE c.updated_at < NOW() - INTERVAL '180 days'
                   OR c.updated_at IS NULL
                ORDER BY c.updated_at ASC NULLS LAST LIMIT 100
            """,
            "sql_params": {},
            "eval_prompt": (
                "You are a GDPR compliance auditor. "
                "These catalogs have not been updated in 6+ months. "
                "GDPR Article 32 requires regular review of security and governance measures. "
                "Stale metadata indicates lack of active data stewardship. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
            "gdpr_article": "32",
            "severity": "medium",
        },
        # ------------------------------------------------------------------
        # GDPR-008
        # ------------------------------------------------------------------
        {
            "rule_id": "GDPR-008",
            "rule": "Source data lineage must be tracked for right-to-be-forgotten implementation",
            "description": (
                "GDPR Article 17 (right to erasure) requires ability to trace data origins and "
                "implement cascading deletions. source_id linkage must be maintained"
            ),
            "sql": """
                SELECT c.id, c.table_name AS name, c.full_name, c.schema_name,
                       c.database_name, c.source_id, ds.id AS source_exists,
                       c.owner_id, c.metadata
                FROM catalogs c
                LEFT JOIN data_sources ds ON ds.id = c.source_id
                JOIN tag_catalog_assignments tca ON tca.catalog_id = c.id
                JOIN tags t ON t.id = tca.tag_id
                WHERE LOWER(t.name) = ANY(%(tags)s)
                  AND (c.source_id IS NULL OR ds.id IS NULL)
                ORDER BY c.full_name LIMIT 100
            """,
            "sql_params": {"tags": ["pii", "personal data", "sensitive"]},
            "eval_prompt": (
                "You are a GDPR compliance auditor. "
                "These PII tables have missing or orphaned source data links. "
                "GDPR Article 17 (right to be forgotten) requires ability to trace and cascade deletions. "
                "Broken data lineage prevents proper erasure implementation. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
            "gdpr_article": "17",
            "severity": "critical",
        },
        # ------------------------------------------------------------------
        # GDPR-009
        # ------------------------------------------------------------------
        {
            "rule_id": "GDPR-009",
            "rule": "Schema isolation must be enforced for personal data separation",
            "description": (
                "GDPR Article 5(1)(f) integrity and confidentiality - personal data must be "
                "segregated in distinct schemas for access control"
            ),
            "sql": """
                SELECT c.schema_name,
                       COUNT(c.id)             AS table_count,
                       COUNT(DISTINCT c.owner_id) AS owner_count,
                       STRING_AGG(DISTINCT t.name, ', ')     AS tags,
                       MAX(c.updated_at)       AS last_update,
                       STRING_AGG(DISTINCT c.full_name, ', ') AS sample_tables
                FROM catalogs c
                LEFT JOIN tag_catalog_assignments tca ON tca.catalog_id = c.id
                LEFT JOIN tags t ON t.id = tca.tag_id
                WHERE LOWER(t.name) = ANY(%(tags)s)
                GROUP BY c.schema_name
                HAVING COUNT(DISTINCT CASE WHEN LOWER(t.name) != ALL(%(tags)s) THEN c.id END) > 0
                ORDER BY table_count DESC
            """,
            "sql_params": {"tags": ["pii", "personal data", "sensitive"]},
            "eval_prompt": (
                "You are a GDPR compliance auditor. "
                "These schemas mix personal data with non-personal data in the same schema. "
                "GDPR Article 5(1)(f) requires proper isolation through schema segregation. "
                "Mixed schemas prevent fine-grained access controls and increase breach risk. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
            "gdpr_article": "5(1)(f)",
            "severity": "high",
        },
        # ------------------------------------------------------------------
        # GDPR-010
        # ------------------------------------------------------------------
        {
            "rule_id": "GDPR-010",
            "rule": "Orphaned catalogs without owners must be assigned or marked for deletion",
            "description": (
                "GDPR Article 5(2) accountability requires all data assets to have ownership. "
                "Orphaned tables may indicate inactive data that violates storage limitation"
            ),
            "sql": """
                SELECT c.id, c.table_name AS name, c.full_name, c.schema_name,
                       c.database_name, c.row_count, c.created_at, c.updated_at,
                       c.owner_id, o.id AS owner_exists
                FROM catalogs c
                LEFT JOIN owners o ON o.id = c.owner_id
                WHERE c.owner_id IS NULL
                   OR o.id IS NULL
                ORDER BY c.created_at ASC LIMIT 100
            """,
            "sql_params": {},
            "eval_prompt": (
                "You are a GDPR compliance auditor. "
                "These tables have no assigned owner or the owner record is missing. "
                "GDPR Article 5(2) accountability principle requires clear ownership. "
                "Orphaned tables cannot be properly managed, audited, or deleted. "
                "If any rows are returned, this rule has FAILED. "
                "Respond ONLY with valid JSON: "
                "{\"passed\": true, \"reason\": \"explanation\", \"severity\": \"low|medium|high|critical\"}. "
                "No markdown, no extra text. Query Results:"
            ),
            "gdpr_article": "5(2)",
            "severity": "high",
        },
    ],
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_due_date(severity: str) -> str:
    days = SEVERITY_DUE_DAYS.get(severity.lower(), 14)
    return (datetime.utcnow() + timedelta(days=days)).strftime("%b %d, %Y")

def extract_dataset_from_results(query_results: list) -> str:
    datasets: set = set()
    for row in query_results:
        name = (row.get("full_name") or row.get("name")
                or row.get("table_name") or row.get("column_name")
                or row.get("schema_name"))
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
    if secs < 60:         return "just now"
    elif secs < 3600:
        m = secs // 60;   return f"{m} minute{'s' if m != 1 else ''} ago"
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
        "host":               os.getenv("PG_HOST"),
        "port":               int(os.getenv("PG_PORT", "5432")),
        "dbname":             os.getenv("PG_DB"),
        "user":               os.getenv("PG_USER"),
        "password":           os.getenv("PG_PASS"),
        "sslmode":            os.getenv("PG_SSLMODE",  "prefer"),
        "keepalives":          1,
        "keepalives_idle":     30,
        "keepalives_interval": 10,
        "keepalives_count":    5,
        "options":            "-c statement_timeout=30000",
    }


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
        """Placeholder for table creation logic if needed"""
        pass

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
                    if cur.description:
                        return [dict(row) for row in cur.fetchall()]
                    conn.commit()
                    return []
        except psycopg2.Error as exc:
            logger.error("SQL ERROR [pgcode=%s]: %s", exc.pgcode, exc.pgerror)
            return []

    def close(self) -> None:
        self._pool.closeall()
        logger.info("DatabaseManager: pool closed.")


# =============================================================================
# LLM EVALUATOR (Detection & Recommendations Only)
# =============================================================================

class LLMEvaluator:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            model_name=os.getenv("AZURE_OPENAI_API_MODEL_NAME"),
            temperature=0.1,
        )
        logger.info("LLMEvaluator: AzureChatOpenAI ready.")

    def evaluate_rule(self, rule: dict, query_results: list) -> dict:
        """Evaluate rule violations - DETECTION ONLY, NO AUTO-FIX."""
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
        """Generate executive summary and remediation recommendations."""
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
# LANGGRAPH STATE
# =============================================================================

class ComplianceState(TypedDict):
    frameworks:    dict
    overall_score: float
    issues:        list
    insights:      str
    run_timestamp: str


# =============================================================================
# LANGGRAPH NODES
# =============================================================================

def make_evaluate_frameworks_node(db: DatabaseManager, llm: LLMEvaluator, rules: dict):
    def evaluate_frameworks(state: ComplianceState) -> ComplianceState:
        logger.info("Node: evaluate_frameworks (DETECTION ONLY)")
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
                    fw_issues.append({
                        "issue":         rule["rule"],
                        "rule_id":       rule_id,
                        "framework":     framework,
                        "severity":      eval_result["severity"].upper(),
                        "reason":        eval_result["reason"],
                        "dataset":       extract_dataset_from_results(query_results),
                        "assignee":      "Manual Review Required",
                        "due_date":      calculate_due_date(eval_result["severity"]),
                        "affected_rows": len(query_results),
                        "action_url":    f"/issues/{rule_id}",
                        "query_results": query_results,
                        "status":        "OPEN - AWAITING MANUAL REMEDIATION",
                    })

            score = round((passed_count / len(fw_rules)) * 100, 2) if fw_rules else 0.0
            logger.info(
                "  %s: %.1f%%  (%d/%d passed, %d issue(s))",
                framework, score, passed_count, len(fw_rules), len(fw_issues),
            )
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
    logger.info("Overall: %s%%  |  Issues: %d (all awaiting manual remediation)",
                state["overall_score"], len(state["issues"]))
    return state


def make_generate_insights_node(llm: LLMEvaluator):
    def generate_insights(state: ComplianceState) -> ComplianceState:
        logger.info("Node: generate_insights")
        state["insights"] = llm.generate_insights(state["overall_score"], state["issues"])
        return state
    return generate_insights


# =============================================================================
# COMPLIANCE ENGINE (Detection & Reporting Only)
# =============================================================================

class ComplianceEngine:
    def __init__(self, db: DatabaseManager, llm: LLMEvaluator,
                 framework_rules: Optional[dict] = None):
        self.db              = db
        self.llm             = llm
        self.framework_rules = framework_rules or FRAMEWORK_RULES
        self.graph           = self._build_graph()

    def _build_graph(self):
        wf = StateGraph(ComplianceState)
        wf.add_node("evaluate_frameworks",
                    make_evaluate_frameworks_node(self.db, self.llm, self.framework_rules))
        wf.add_node("aggregate_scores", aggregate_scores_node)
        wf.add_node("generate_insights", make_generate_insights_node(self.llm))

        wf.set_entry_point("evaluate_frameworks")
        wf.add_edge("evaluate_frameworks",   "aggregate_scores")
        wf.add_edge("aggregate_scores",      "generate_insights")
        wf.add_edge("generate_insights",     END)
        return wf.compile()

    def run(self) -> dict:
        logger.info("=" * 60)
        logger.info("ComplianceEngine: run started (DETECTION & REPORTING ONLY)")
        run_ts = datetime.now(IST)
        initial: ComplianceState = {
            "frameworks":    {},
            "overall_score": 0.0,
            "issues":        [],
            "insights":      "",
            "run_timestamp": run_ts.isoformat(),
        }
        final     = self.graph.invoke(initial)
        dashboard = self._build_dashboard(final, run_ts)
        logger.info("ComplianceEngine: complete  Score=%.1f%%", final["overall_score"])
        logger.info("=" * 60)
        return dashboard

    def _build_dashboard(self, state: ComplianceState, run_ts: datetime) -> dict:
        overall  = state["overall_score"]
        issues   = state["issues"]
        fw_data  = state["frameworks"]

        sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            key = issue.get("severity", "low").lower()
            sev_counts[key] = sev_counts.get(key, 0) + 1

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
            total  = fw.get("rules_total", 0)
            failed = fw.get("issues", [])
            if failed:
                return f"{passed} of {total} Policies ({len(failed)} issue(s))"
            return f"{passed} of {total} Policies"

        return {
            "timestamp": run_ts.isoformat(),
            "mode": "DETECTION & REPORTING ONLY - NO AUTO-FIX",
            "overall_compliance": {
                "score":                  overall,
                "change_from_last_month": 0.0,
                "health_status":          health_status(overall),
                "last_updated":           "just now",
            },
            "compliance_health": {
                "score":       overall,
                "trend_label": "Latest scan",
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
                        "assignee":   i.get("assignee", "Manual Review Required"),
                        "due_date":   i["due_date"],
                        "action_url": i.get("action_url", f"/issues/{i.get('rule_id', 'unknown')}"),
                        "status":     i.get("status", "OPEN"),
                    }
                    for i in issues
                ],
            },
            "ai_insights":   {"text": state["insights"], "beta": True},
            "quick_actions": QUICK_ACTIONS,
        }


# =============================================================================
# INITIALIZATION FUNCTION (Required by app.py)
# =============================================================================

_global_engine: Optional[ComplianceEngine] = None
_global_db: Optional[DatabaseManager] = None
_global_llm: Optional[LLMEvaluator] = None


async def init_compliance_engine() -> None:
    """
    Initialize the compliance engine on startup.
    Called from app.py during the lifespan startup phase.
    """
    global _global_engine, _global_db, _global_llm, _engine, _db, _llm
    try:
        logger.info("Initializing Compliance Engine...")
        # Initialize database manager (blocking, but fast)
        _global_db = DatabaseManager(min_conn=1, max_conn=10)
        _db = _global_db  # Also set module-level variable for router access
        # Initialize LLM evaluator
        _global_llm = LLMEvaluator()
        _llm = _global_llm
        # Initialize compliance engine
        _global_engine = ComplianceEngine(db=_global_db, llm=_global_llm)
        _engine = _global_engine
        logger.info("Compliance Engine initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Compliance Engine: {e}")
        raise
# =============================================================================
# PDF GENERATION HELPERS
# =============================================================================

def _pdf_styles() -> dict:
    return {
        "title": ParagraphStyle("title", fontSize=22, textColor=WHITE,
                                fontName="Helvetica-Bold", alignment=TA_LEFT, leading=28),
        "subtitle": ParagraphStyle("subtitle", fontSize=10,
                                   textColor=colors.HexColor("#BFDBFE"),
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
    if s in ("critical", "error"):   return RED,     RED_BG
    if s in ("needs_attention", "warning"): return ORANGE, ORANGE_BG
    if s in ("excellent", "good", "success"): return GREEN, GREEN_BG
    return MID_BLUE, LIGHT_BLUE


def _score_color(score: float):
    if score >= 90: return GREEN
    if score >= 60: return ORANGE
    return RED


def _header_table(snapshot: dict, st: dict):
    recorded = snapshot.get("recorded_at", datetime.utcnow())
    ts_str = recorded.strftime("%Y-%m-%d %H:%M UTC") if hasattr(recorded, "strftime") else str(recorded)
    right_text = ParagraphStyle("rt", fontSize=9, textColor=colors.HexColor("#BFDBFE"),
                                fontName="Helvetica", alignment=TA_RIGHT)
    left = [
        Paragraph("Compliance Report", st["title"]),
        Spacer(1, 4),
        Paragraph("GDPR Data Governance Health &amp; Detection Report", st["subtitle"]),
        Spacer(1, 4),
        Paragraph(f"Generated: {ts_str}", st["subtitle"]),
    ]
    right = [
        Paragraph("Report Period: Latest Snapshot", right_text),
        Paragraph(f"Record ID: {str(snapshot.get('id', ''))[:8]}...", right_text),
        Paragraph("<b>Detection & Reporting Only - No Auto-Fix</b>", right_text),
    ]
    t = Table([[left, right]], colWidths=[110*mm, 70*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), DARK_BLUE),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (0,  0),  10*mm),
        ("RIGHTPADDING",  (1, 0), (1,  0),  8*mm),
        ("TOPPADDING",    (0, 0), (-1, -1), 8*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8*mm),
    ]))
    return t


def _overall_score_table(snapshot: dict, st: dict):
    overall = float(snapshot.get("overall_score", 0))
    status  = snapshot.get("overall_health_status", "")
    fg, bg  = _status_color(status)
    sc      = _score_color(overall)

    hex_sc = sc.hexval()[2:]
    score_cell = [
        Paragraph(f'<font color="#{hex_sc}"><b>{overall:.1f}%</b></font>',
                  ParagraphStyle("sc", fontSize=36, fontName="Helvetica-Bold",
                                 alignment=TA_CENTER, leading=42)),
        Paragraph("Overall GDPR Compliance Score",
                  ParagraphStyle("sl", fontSize=10, fontName="Helvetica-Bold",
                                 textColor=DARK_BLUE, alignment=TA_CENTER)),
        Spacer(1, 4),
        Paragraph(status.replace("_", " ").title(),
                  ParagraphStyle("ss", fontSize=9, fontName="Helvetica-Bold",
                                 textColor=fg, alignment=TA_CENTER)),
    ]
    sev_data = [
        [Paragraph("<b>Issues Requiring Remediation</b>", st["bold_small"]), ""],
        ["Total Open Issues", str(snapshot.get("open_issues_count", 0))],
        ["Critical",         str(snapshot.get("critical_issues_count", 0))],
        ["High",             str(snapshot.get("high_issues_count", 0))],
        ["Medium",           str(snapshot.get("medium_issues_count", 0))],
        ["Low",              str(snapshot.get("low_issues_count", 0))],
    ]
    sev_table = Table(sev_data, colWidths=[55*mm, 20*mm])
    sev_table.setStyle(TableStyle([
        ("SPAN",          (0, 0), (1, 0)),
        ("BACKGROUND",    (0, 0), (1, 0), GREY_LIGHT),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR",     (1, 2), (1, 2),  RED),
        ("FONTNAME",      (1, 2), (1, 2),  "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1), 0.5, GREY_BORDER),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GREY_LIGHT]),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    outer = Table([[score_cell, sev_table]], colWidths=[80*mm, 100*mm])
    outer.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), bg),
        ("BACKGROUND",    (1, 0), (1, 0), WHITE),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BOX",           (0, 0), (-1, -1), 1, GREY_BORDER),
        ("LINEAFTER",     (0, 0), (0, 0),   1, GREY_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 6*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6*mm),
        ("LEFTPADDING",   (0, 0), (0, 0),   6*mm),
        ("LEFTPADDING",   (1, 0), (1, 0),   5*mm),
    ]))
    return outer


def _framework_cards(frameworks: list, st: dict) -> list:
    elements: list = []
    elements.append(Paragraph("GDPR Framework Compliance Status", st["section_head"]))
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
                                                fontName="Helvetica-Bold",
                                                alignment=TA_CENTER))]],
                     colWidths=[22*mm])
        pill.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), GREY_LIGHT),
            ("BOX",           (0, 0), (-1, -1), 1, GREY_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))

        badge = Table([[Paragraph(status.replace("_", " ").title(),
                                  ParagraphStyle("b", fontSize=8, textColor=fg,
                                                 fontName="Helvetica-Bold",
                                                 alignment=TA_CENTER))]],
                      colWidths=[30*mm])
        badge.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("BOX",           (0, 0), (-1, -1), 0.5, fg),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))

        header_row = Table([
            [Paragraph(f"<b>{name}</b>",
                       ParagraphStyle("fn", fontSize=12, textColor=DARK_BLUE,
                                      fontName="Helvetica-Bold")),
             pill, badge,
             Paragraph(details, st["small"])]
        ], colWidths=[35*mm, 25*mm, 33*mm, 87*mm])
        header_row.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (0,  0),  0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
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
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS",(0, 0), (-1, -1), [WHITE, GREY_LIGHT]),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (1, 0), (1, -1),  4),
            ("BOX",           (0, 0), (-1, -1), 0.5, GREY_BORDER),
            ("LINEBELOW",     (0, 0), (-1, -2), 0.3, GREY_BORDER),
        ]))

        card = Table([[header_row], [Spacer(1, 4)], [ind_table]], colWidths=[180*mm])
        card.setStyle(TableStyle([
            ("BOX",           (0, 0), (-1, -1), 1, GREY_BORDER),
            ("BACKGROUND",    (0, 0), (-1, -1), WHITE),
            ("TOPPADDING",    (0, 0), (-1, -1), 4*mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4*mm),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4*mm),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4*mm),
        ]))

        elements.append(KeepTogether(card))
        elements.append(Spacer(1, 5*mm))

    return elements


def _open_issues_table(issues: list, st: dict) -> list:
    elements: list = []
    elements.append(Paragraph("Open Issues (Awaiting Manual Remediation)", st["section_head"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=GREY_BORDER, spaceAfter=6))

    if not issues:
        elements.append(Paragraph("No open issues found.", st["body"]))
        return elements

    header = [
        Paragraph("<b>#</b>",        st["bold_small"]),
        Paragraph("<b>Issue</b>",     st["bold_small"]),
        Paragraph("<b>Framework</b>", st["bold_small"]),
        Paragraph("<b>Severity</b>",  st["bold_small"]),
        Paragraph("<b>Dataset</b>",   st["bold_small"]),
        Paragraph("<b>Due Date</b>",  st["bold_small"]),
    ]
    rows = [header]
    for i, issue in enumerate(issues, 1):
        sev   = issue.get("severity", "")
        fg, _ = _status_color(sev)
        dataset = issue.get("dataset", "")
        rows.append([
            Paragraph(str(i), st["small"]),
            Paragraph(issue.get("issue", ""), st["small"]),
            Paragraph(issue.get("framework", ""), st["small"]),
            Paragraph(sev, ParagraphStyle("sv", fontSize=7.5, textColor=fg,
                                          fontName="Helvetica-Bold",
                                          alignment=TA_CENTER)),
            Paragraph(dataset[:80] + ("..." if len(dataset) > 80 else ""), st["small"]),
            Paragraph(issue.get("due_date", ""), st["small"]),
        ])

    tbl = Table(rows, colWidths=[8*mm, 62*mm, 22*mm, 20*mm, 44*mm, 24*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.3, GREY_BORDER),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GREY_LIGHT]),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
    ]))
    elements.append(tbl)
    return elements


def _ai_insights_section(insights_text: str, st: dict) -> list:
    elements: list = []
    if not insights_text:
        return elements
    elements.append(Spacer(1, 6*mm))
    elements.append(Paragraph("AI Insights & Remediation Recommendations (Beta)", st["section_head"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=GREY_BORDER, spaceAfter=6))
    for line in insights_text.split("\n"):
        line = line.strip()
        if not line:
            elements.append(Spacer(1, 3))
            continue
        if line.startswith("**") and line.endswith("**"):
            elements.append(Paragraph(line.strip("*"), st["insight_bold"]))
        else:
            elements.append(Paragraph(line, st["insight"]))
    return elements


def _build_pdf(dashboard: dict) -> bytes:
    """Render the compliance dashboard dict as a PDF and return raw bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=10*mm,  bottomMargin=15*mm,
    )
    st  = _pdf_styles()

    snap: dict = {
        "id":                    "live",
        "recorded_at":           datetime.now(timezone.utc),
        "overall_score":         dashboard.get("overall_compliance", {}).get("score", 0),
        "overall_health_status": dashboard.get("overall_compliance", {}).get("health_status", ""),
        "open_issues_count":     dashboard.get("open_issues", {}).get("count", 0),
        "critical_issues_count": dashboard.get("open_issues", {}).get("severity_summary", {}).get("critical", 0),
        "high_issues_count":     dashboard.get("open_issues", {}).get("severity_summary", {}).get("high", 0),
        "medium_issues_count":   dashboard.get("open_issues", {}).get("severity_summary", {}).get("medium", 0),
        "low_issues_count":      dashboard.get("open_issues", {}).get("severity_summary", {}).get("low", 0),
    }

    story: list = []
    story.append(_header_table(snap, st))
    story.append(Spacer(1, 6*mm))
    story.append(_overall_score_table(snap, st))
    story.append(Spacer(1, 6*mm))
    story += _framework_cards(dashboard.get("frameworks", []), st)
    story.append(Spacer(1, 4*mm))
    story += _open_issues_table(dashboard.get("open_issues", {}).get("items", []), st)
    story += _ai_insights_section(
        dashboard.get("ai_insights", {}).get("text", ""), st
    )

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GREY_TEXT)
        canvas.drawCentredString(
            A4[0] / 2,
            10*mm,
            f"GDPR Compliance Report (Detection & Reporting Only)  •  Page {doc.page}  •  "
            f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


# =============================================================================
# SNAPSHOT PERSISTENCE HELPER
# =============================================================================

def _save_snapshot(db: DatabaseManager, dashboard: dict) -> None:
    """Persist the latest dashboard result to compliance_snapshots."""
    try:
        overall   = dashboard.get("overall_compliance", {})
        issues    = dashboard.get("open_issues", {})
        sev       = issues.get("severity_summary", {})
        ai        = dashboard.get("ai_insights", {})

        fw_map: dict = {}
        for fw in dashboard.get("frameworks", []):
            fw_map[fw["name"].lower()] = fw

        def fw_val(name: str, key: str):
            fw = fw_map.get(name, {})
            if key == "score":
                return fw.get("score")
            if key == "status":
                return fw.get("status")
            details = fw.get("details", "")
            import re as _re
            m = _re.match(r"(\d+) of (\d+)", details)
            if m:
                return int(m.group(1)) if key == "rules_passed" else int(m.group(2))
            return None

        sql = """
            INSERT INTO compliance_snapshots (
                overall_score, overall_health_status,
                gdpr_score, gdpr_status, gdpr_rules_passed, gdpr_rules_total,
                open_issues_count, critical_issues_count, high_issues_count,
                medium_issues_count, low_issues_count,
                compliance_health_score,
                ai_insights_text, ai_insights_beta,
                snapshot_json
            ) VALUES (
                %(overall_score)s, %(overall_health_status)s,
                %(gdpr_score)s, %(gdpr_status)s, %(gdpr_passed)s, %(gdpr_total)s,
                %(open_count)s, %(critical)s, %(high)s, %(medium)s, %(low)s,
                %(overall_score)s,
                %(ai_text)s, %(ai_beta)s,
                %(snap_json)s
            )
        """
        logger.info("Snapshot persistence disabled (Detection & Reporting only).")
    except Exception as exc:
        logger.error("Snapshot processing note: %s", exc)


def _load_latest_snapshot(db: DatabaseManager) -> Optional[dict]:
    """Retrieve the most recent snapshot row as a dict."""
    rows = db.execute_query(
        "SELECT * FROM compliance_snapshots ORDER BY recorded_at DESC LIMIT 1"
    )
    return rows[0] if rows else None


# =============================================================================
# FASTAPI APP
# =============================================================================

_db:     Optional[DatabaseManager]  = None
_llm:    Optional[LLMEvaluator]     = None
_engine: Optional[ComplianceEngine] = None
_latest_dashboard: Optional[dict]   = None





router = APIRouter(prefix="/api/compliance",tags=["Compliance"])

def generate_rule_name(issue: str) -> str:
    """
    Generates a concise rule name from the issue text.
    Takes the first two words of the issue description.
    
    Args:
        issue: Full issue description text
        
    Returns:
        First two words of the issue or the full issue if less than 2 words
    """
    words = issue.split()
    return " ".join(words[:2]) if len(words) >= 2 else issue
 
 
def extract_rule_id(action_url: Optional[str], fallback: str) -> str:
    """
    Extracts the rule ID from the action URL.
    Expected URL format: /issues/RULE-XXX
    
    Args:
        action_url: URL from the compliance issue (e.g., "/issues/GDPR-001")
        fallback: Default rule ID to use if URL is invalid (e.g., "RULE-1")
        
    Returns:
        Extracted rule ID or fallback value
    """
    if action_url and "/issues/" in action_url:
        return action_url.split("/issues/")[-1]
    return fallback
 
 
def calculate_health_status(compliance_score: float) -> str:
    """
    Determines the health status based on compliance score.
    
    Args:
        compliance_score: Percentage score (0-100)
        
    Returns:
        Health status: "excellent", "needs_attention", or "critical"
    """
    if compliance_score == 100:
        return "excellent"
    elif compliance_score >= 70:
        return "needs_attention"
    else:
        return "critical"
 



@router.get("/run", tags=["Compliance"])
def run_compliance_scan():
    """
    Trigger a full GDPR compliance scan (detection & reporting only).
    
    All violations are reported. No automatic remediation is applied.
    Manual action required for all flagged issues.
    """
    global _latest_dashboard
    if _engine is None:
        raise HTTPException(status_code=503, detail="Compliance engine not initialised.")
    try:
        result = _engine.run()
        _latest_dashboard = result
        if _db:
            _save_snapshot(_db, result)
        return JSONResponse(content=result)
    except Exception as exc:
        logger.exception("Compliance scan failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Scan failed: {exc}")


@router.get("/summary", tags=["Compliance"])
def get_compliance_summary():
    """Return the most recent GDPR compliance snapshot summary from the database."""
    if _db:
        snap = _load_latest_snapshot(_db)
        if snap:
            return JSONResponse(content={
                "recorded_at":           str(snap.get("recorded_at", "")),
                "overall_score":         float(snap.get("overall_score", 0)),
                "overall_health_status": snap.get("overall_health_status", ""),
                "open_issues_count":     snap.get("open_issues_count", 0),
                "critical_issues_count": snap.get("critical_issues_count", 0),
                "high_issues_count":     snap.get("high_issues_count", 0),
                "medium_issues_count":   snap.get("medium_issues_count", 0),
                "low_issues_count":      snap.get("low_issues_count", 0),
                "gdpr_score":            float(snap.get("gdpr_score") or 0),
                "ai_insights":           snap.get("ai_insights_text", ""),
                "source": "database",
                "mode": "Detection & Reporting Only",
            })

    if _latest_dashboard:
        oc = _latest_dashboard.get("overall_compliance", {})
        oi = _latest_dashboard.get("open_issues", {})
        sv = oi.get("severity_summary", {})
        return JSONResponse(content={
            "overall_score":         oc.get("score", 0),
            "overall_health_status": oc.get("health_status", ""),
            "open_issues_count":     oi.get("count", 0),
            "critical_issues_count": sv.get("critical", 0),
            "high_issues_count":     sv.get("high", 0),
            "medium_issues_count":   sv.get("medium", 0),
            "low_issues_count":      sv.get("low", 0),
            "source": "cache",
            "mode": "Detection & Reporting Only",
        })

    raise HTTPException(
        status_code=404,
        detail="No snapshot available. Run a compliance scan first via GET /api/compliance/run.",
    )


@router.get("/loading", tags=["Compliance"])
def get_loading_state():
    """Returns the current loading / readiness state of the compliance engine."""
    return JSONResponse(content={
        "engine_ready":    _engine is not None,
        "database_ready":  _db is not None,
        "llm_ready":       _llm is not None,
        "scan_available":  _latest_dashboard is not None,
        "timestamp":       datetime.now(IST).isoformat(),
        "mode": "Detection & Reporting Only - No Auto-Fix",
        "message": (
            "Engine ready. Trigger a scan via GET /api/compliance/run. All issues require manual remediation."
            if _engine else "Engine initialising, please wait."
        ),
    })


@router.get("/report/export", tags=["Compliance"])
def export_compliance_report():
    """Export the latest GDPR compliance detection report as a formatted PDF."""
    dashboard: Optional[dict] = _latest_dashboard

    if dashboard is None and _db:
        snap = _load_latest_snapshot(_db)
        if snap and snap.get("snapshot_json"):
            raw = snap["snapshot_json"]
            dashboard = raw if isinstance(raw, dict) else json.loads(raw)

    if dashboard is None:
        raise HTTPException(
            status_code=404,
            detail="No compliance data available. Run a scan first via GET /api/compliance/run.",
        )

    try:
        pdf_bytes = _build_pdf(dashboard)
        filename  = f"gdpr_compliance_detection_report_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        logger.exception("PDF generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

@router.get("/dataset/{catalog_id}", tags=["Compliance"])
def get_dataset_compliance_report(catalog_id: str):
    if _db is None:
        raise HTTPException(status_code=503, detail="Database not initialised")

    dataset_sql = """
        SELECT id, table_name, full_name, owner_id
        FROM catalogs
        WHERE id = %(catalog_id)s
    """
    dataset_rows = _db.execute_query(dataset_sql, {"catalog_id": catalog_id})

    if not dataset_rows:
        raise HTTPException(status_code=404, detail="Dataset not found")

    dataset = dataset_rows[0]
    dataset_full_name = dataset["full_name"]

    snapshot_sql = """
        SELECT snapshot_json, recorded_at
        FROM compliance_snapshots
        ORDER BY recorded_at DESC
        LIMIT 1
    """
    rows = _db.execute_query(snapshot_sql)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No compliance snapshot found. Run compliance scan first."
        )

    snapshot = rows[0]["snapshot_json"]
    snapshot_timestamp = rows[0]["recorded_at"]

    open_issues = snapshot.get("open_issues", {}).get("items", [])

    dataset_issues = []
    for issue in open_issues:
        datasets_str = issue.get("dataset") or ""
        datasets = [d.strip() for d in datasets_str.split(",") if d.strip()]
        if dataset_full_name in datasets:
            dataset_issues.append(issue)

    issue_lookup: Dict[tuple, Dict[str, Any]] = {
        (issue.get("framework"), issue.get("issue")): issue
        for issue in dataset_issues
    }

    frameworks = snapshot.get("frameworks", [])
    rules: List[Dict[str, Any]] = []
    rule_counter = 1

    for framework in frameworks:
        framework_name = framework.get("name")
        indicators = framework.get("indicators", [])

        for indicator in indicators:
            issue_text = indicator.get("text", "")
            matched_issue = issue_lookup.get((framework_name, issue_text))

            if matched_issue:
                status = "VIOLATED"
                severity = matched_issue.get("severity")
                action_url = matched_issue.get("action_url")
                violations = [
                    {
                        "dataset": dataset_full_name,
                        "assignee": matched_issue.get("assignee"),
                        "due_date": matched_issue.get("due_date"),
                        "action_url": action_url
                    }
                ]
            else:
                status = "COMPLIANT"
                severity = "PASS"
                action_url = None
                violations = []

            rule_id = extract_rule_id(action_url, f"RULE-{rule_counter}")

            rule_obj = {
                "rule_id": rule_id,
                "framework": framework_name,
                "rule_name": generate_rule_name(issue_text),
                "description": issue_text,
                "status": status,
                "severity": severity,
                "violations": violations
            }

            rules.append(rule_obj)
            rule_counter += 1

    column_sql = """
        SELECT COUNT(*) AS column_count
        FROM columns
        WHERE catalog_id = %(catalog_id)s
    """
    column_result = _db.execute_query(column_sql, {"catalog_id": catalog_id})
    column_count = column_result[0]["column_count"] if column_result else 0

    compliant_count = sum(1 for r in rules if r["status"] == "COMPLIANT")
    violated_count = sum(1 for r in rules if r["status"] == "VIOLATED")
    critical_violations = sum(
        1 for r in rules
        if r["status"] == "VIOLATED" and (r.get("severity") or "").upper() == "CRITICAL"
    )

    total_rules = len(rules)
    compliance_score = round((compliant_count / total_rules) * 100, 2) if total_rules else 0
    h_status = calculate_health_status(compliance_score)

    return {
        "dataset": {
            "catalog_id": dataset["id"],
            "name": dataset["table_name"],
            "full_name": dataset["full_name"],
            "owner": dataset["owner_id"]
        },
        "summary": {
            "compliance_score": compliance_score,
            "status": h_status,
            "policies_checked": total_rules,
            "compliant_rules": compliant_count,
            "violated_rules": violated_count,
            "protected_assets": column_count,
            "critical_violations": critical_violations,
            "last_updated": snapshot_timestamp.isoformat() if snapshot_timestamp else None
        },
        "rules": rules
    }


 

