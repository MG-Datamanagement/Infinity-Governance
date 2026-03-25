"""
main.py
-------
SQL Chatbot API with:
  - Multi-agent selection via /chatbot (optional: /{agent_names}/{table_names})
  - Default agent: sql_agent | Default table: catalogs
  - Intent classification to enforce capability boundaries
  - Per-agent tool restrictions (no capability bleed)
  - Redis memory with TTL + fallback
  - Full input validation and safe error handling
"""

import os
import re
import ast
import json
import logging
from enum import Enum
from typing import Optional
import uuid

from fastapi import Query, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, Field, validator

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit, create_sql_agent
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from dotenv import load_dotenv

from services.llm import llm_initiate

load_dotenv()

router = APIRouter(tags=["Chatbot"])

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class AgentName(str, Enum):
    SCHEMA_SCOUT        = "schema_scout"
    PII_DETECTIVE       = "pii_detective"
    COMPLIANCE_GUARDIAN = "compliance_guardian"
    LINEAGE_TRACKER     = "lineage_tracker"
    SQL_AGENT           = "sql_agent"


class QueryIntent(str, Enum):
    SCHEMA_INTROSPECTION = "schema_introspection"
    PII_DETECTION        = "pii_detection"
    COMPLIANCE_CHECK     = "compliance_check"
    LINEAGE_MAPPING      = "lineage_mapping"
    DATA_QUERY           = "data_query"


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
MAX_QUERY_LENGTH        = 2000
MAX_TABLES_PER_REQUEST  = 10
MAX_AGENTS_PER_REQUEST  = 5
REDIS_SESSION_TTL       = 3600       # 1 hour
AGENT_MAX_ITERATIONS    = 15
AGENT_MAX_EXEC_TIME     = 35

DEFAULT_AGENT_NAMES = "sql_agent"
DEFAULT_TABLE_NAMES = "catalogs"

VALID_AGENT_NAMES = {a.value for a in AgentName}


# ─────────────────────────────────────────────
# TOOL PERMISSIONS
# ─────────────────────────────────────────────

AGENT_ALLOWED_TOOLS: dict[AgentName, list[str]] = {
    AgentName.SCHEMA_SCOUT:        ["sql_db_schema"],
    AgentName.PII_DETECTIVE:       ["sql_db_list_tables", "sql_db_schema", "sql_db_query"],
    AgentName.COMPLIANCE_GUARDIAN: ["sql_db_list_tables", "sql_db_schema", "sql_db_query"],
    AgentName.LINEAGE_TRACKER:     ["sql_db_list_tables", "sql_db_schema"],
    AgentName.SQL_AGENT:           ["sql_db_list_tables", "sql_db_query", "sql_db_query_checker"],
}


# ─────────────────────────────────────────────
# INTENT PERMISSIONS
# ─────────────────────────────────────────────

AGENT_ALLOWED_INTENTS: dict[AgentName, list[QueryIntent]] = {
    AgentName.SCHEMA_SCOUT:        [QueryIntent.SCHEMA_INTROSPECTION],
    AgentName.PII_DETECTIVE:       [QueryIntent.PII_DETECTION],
    AgentName.COMPLIANCE_GUARDIAN: [QueryIntent.COMPLIANCE_CHECK],
    AgentName.LINEAGE_TRACKER:     [QueryIntent.LINEAGE_MAPPING],
    AgentName.SQL_AGENT:           [QueryIntent.DATA_QUERY],
}

INTENT_OWNER: dict[QueryIntent, AgentName] = {
    QueryIntent.SCHEMA_INTROSPECTION: AgentName.SCHEMA_SCOUT,
    QueryIntent.PII_DETECTION:        AgentName.PII_DETECTIVE,
    QueryIntent.COMPLIANCE_CHECK:     AgentName.COMPLIANCE_GUARDIAN,
    QueryIntent.LINEAGE_MAPPING:      AgentName.LINEAGE_TRACKER,
    QueryIntent.DATA_QUERY:           AgentName.SQL_AGENT,
}

AGENT_DISPLAY_NAMES: dict[AgentName, str] = {
    AgentName.SCHEMA_SCOUT:        "Schema Scout",
    AgentName.PII_DETECTIVE:       "PII Detective",
    AgentName.COMPLIANCE_GUARDIAN: "Compliance Guardian",
    AgentName.LINEAGE_TRACKER:     "Lineage Tracker",
    AgentName.SQL_AGENT:           "SQL Agent",
}


# ─────────────────────────────────────────────
# INTENT CLASSIFIER PROMPT
# ─────────────────────────────────────────────

INTENT_CLASSIFIER_PROMPT = """\
You are an intent classifier for a database assistant system.

Classify the user query into EXACTLY ONE of these intents:

- data_query            : Fetching rows, counts, aggregations, filtering or retrieving actual data values
- schema_introspection  : Column names, data types, constraints, indexes, table structure, nullability
- pii_detection         : Finding sensitive or personal data columns (emails, SSNs, phone numbers, etc.)
- compliance_check      : Checking policy violations, enforcement rules, regulatory compliance
- lineage_mapping       : Table dependencies, foreign keys, upstream/downstream relationships

Rules:
- Respond with ONLY the intent label. No explanation. No punctuation. Nothing else.
- If the query asks about column names OR data types OR table structure -> schema_introspection, NOT data_query.
- If the query asks about sensitive or personal fields -> pii_detection.
- If the query asks about dependencies or references between tables -> lineage_mapping.
- If in doubt between schema_introspection and data_query -> choose schema_introspection.

Query: "{query}"
"""


# ─────────────────────────────────────────────
# PER-AGENT PROMPTS
# ─────────────────────────────────────────────

SCHEMA_SCOUT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are Schema Scout, a PostgreSQL schema introspection agent.

System Info:
- Dialect: {dialect}
- Available Tables & Schema: {table_info}

YOUR ONLY JOB: Describe table structure — columns, data types, constraints, indexes, nullability.
You MUST NOT fetch or return any actual row data.

Your job is to answer questions about:
- table structure
- column names
- column data types
- schema metadata

IMPORTANT TOOL RULES:

If the user asks about:
- column names
- column types
- table schema
- structure of a table

You MUST use the tool:

sql_db_schema
     

STRICT RULES:
1. Use sql_db_list_tables to discover available tables.
2. Use sql_db_schema to inspect column definitions.
3. NEVER use sql_db_query — you have no access to row data.
4. NEVER guess column names or types — always introspect first.
5. Reasoning Mode: {reasoning_mode}
   - OFF -> set "reasoning" to "".
   - ON  -> explain what schema structure you found.
6. Return ONLY this JSON:
   {{"response": "Human-readable schema description.", "reasoning": "...", "source": ["table"]}}
"""),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="chat_history"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

PII_DETECTIVE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are PII Detective, a sensitive data detection agent.

System Info:
- Dialect: {dialect}
- Available Tables & Schema: {table_info}

YOUR ONLY JOB: Identify columns that likely contain personally identifiable information (PII)
such as emails, phone numbers, SSNs, addresses, names, dates of birth, credit card numbers.

STRICT RULES:
1. Inspect column names and types using sql_db_schema.
2. You MAY sample up to 3 rows ONLY to confirm PII presence — never return bulk data.
3. NEVER return full table contents.
4. Reasoning Mode: {reasoning_mode}
5. Return ONLY this JSON:
   {{"response": "List of PII columns found with explanation.", "reasoning": "...", "source": ["table"]}}
"""),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="chat_history"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

COMPLIANCE_GUARDIAN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are Compliance Guardian, a policy enforcement agent.

System Info:
- Dialect: {dialect}
- Available Tables & Schema: {table_info}

YOUR ONLY JOB: Check for schema-level policy violations such as missing audit columns,
unencrypted PII fields, tables lacking primary keys, or missing NOT NULL constraints.

STRICT RULES:
1. Use sql_db_schema to inspect table definitions.
2. You MAY run read-only SELECT queries to verify compliance conditions.
3. NEVER run INSERT, UPDATE, DELETE, or DROP.
4. Reasoning Mode: {reasoning_mode}
5. Return ONLY this JSON:
   {{"response": "Summary of compliance findings.", "reasoning": "...", "source": ["table"]}}
"""),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="chat_history"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

LINEAGE_TRACKER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are Lineage Tracker, a data dependency mapping agent.

System Info:
- Dialect: {dialect}
- Available Tables & Schema: {table_info}

YOUR ONLY JOB: Map upstream and downstream table dependencies — foreign keys,
references, and relationships between tables.

STRICT RULES:
1. Use sql_db_list_tables and sql_db_schema to discover relationships.
2. NEVER fetch row data.
3. Reasoning Mode: {reasoning_mode}
4. Return ONLY this JSON:
   {{"response": "Description of table lineage and dependencies.", "reasoning": "...", "source": ["table"]}}
"""),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="chat_history"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

SQL_AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are SQL Agent, a PostgreSQL data query agent.

System Info:
- Dialect: {dialect}
- Available Tables & Schema: {table_info}
- Max Rows: {top_k}

YOUR ONLY JOB: Answer questions by querying actual row data — counts, filters,
aggregations, lookups. You do NOT describe schema structure.

STRICT RULES:
1. Always run queries through sql_db_query_checker before executing.
2. NEVER describe column types or table structure — that belongs to Schema Scout.
3. NEVER run INSERT, UPDATE, DELETE, or DROP.
4. Limit results to {top_k} rows unless specified otherwise.
5. Only query tables listed in {table_info}. Never touch system schemas.
6. Reasoning Mode: {reasoning_mode}
   - OFF -> set "reasoning" to "".
   - ON  -> explain your findings.
7. Return ONLY this JSON:
   {{"response": "Direct answer to the user's question.", "reasoning": "...", "source": ["table"]}}
"""),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="chat_history"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

AGENT_PROMPTS: dict[AgentName, ChatPromptTemplate] = {
    AgentName.SCHEMA_SCOUT:        SCHEMA_SCOUT_PROMPT,
    AgentName.PII_DETECTIVE:       PII_DETECTIVE_PROMPT,
    AgentName.COMPLIANCE_GUARDIAN: COMPLIANCE_GUARDIAN_PROMPT,
    AgentName.LINEAGE_TRACKER:     LINEAGE_TRACKER_PROMPT,
    AgentName.SQL_AGENT:           SQL_AGENT_PROMPT,
}


# ─────────────────────────────────────────────
# DB / LLM — initialised ONCE at startup
# ─────────────────────────────────────────────
POSTGRES_URI = (
    f"postgresql://{os.getenv('PG_USER')}:"
    f"{os.getenv('PG_PASS')}@"
    f"{os.getenv('PG_HOST')}:"
    f"{os.getenv('PG_PORT')}/"
    f"{os.getenv('PG_DB')}"
)

_validation_db: SQLDatabase | None = None
_llm = None


def get_validation_db() -> SQLDatabase:
    global _validation_db
    if _validation_db is None:
        logger.info("Initialising shared DB connection...")
        _validation_db = SQLDatabase.from_uri(POSTGRES_URI)
    return _validation_db


def get_llm():
    global _llm
    if _llm is None:
        logger.info("Initialising LLM...")
        _llm = llm_initiate()
    return _llm


# ─────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────




# ─────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    reasoning: str = Field(default="on", regex="^(on|off)$")
    memory: str    = Field(default="on", regex="^(on|off)$")

    @validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query must not be empty or whitespace.")
        if len(v) > MAX_QUERY_LENGTH:
            raise ValueError(f"query exceeds maximum length of {MAX_QUERY_LENGTH} characters.")
        return v

    @validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("session_id must not be empty.")
        if not re.fullmatch(r"[a-zA-Z0-9_\-]+", v):
            raise ValueError(
                "session_id may only contain letters, numbers, hyphens, and underscores."
            )
        return v


class ChatResponseWithReasoning(BaseModel):
    agent_used: str
    intent_detected: str
    response: str
    reasoning: str
    source: list[str] = Field(default_factory=list)


class ChatResponseWithoutReasoning(BaseModel):
    agent_used: str
    intent_detected: str
    response: str
    source: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────
# REDIS HELPERS
# ─────────────────────────────────────────────

def get_redis_history(session_id: str) -> RedisChatMessageHistory:
    return RedisChatMessageHistory(
        session_id=session_id,
        url=os.getenv("REDIS_URL"),
        ttl=REDIS_SESSION_TTL,
    )


def get_redis_history_safe(session_id: str):
    try:
        history = get_redis_history(session_id)
        _ = history.messages
        return history
    except Exception as err:
        logger.warning("Redis unavailable (%s). Falling back to in-memory history.", err)
        from langchain_core.chat_history import InMemoryChatMessageHistory
        return InMemoryChatMessageHistory()


def build_scoped_session_id(session_id: str, agents: list[str], tables: list[str]) -> str:
    """Scope Redis key to session + agents + tables to prevent memory bleed."""
    agent_key = ":".join(sorted(agents))
    table_key = ":".join(sorted(tables))
    return f"{session_id}:{agent_key}:{table_key}"


# ─────────────────────────────────────────────
# INTENT CLASSIFIER
# ─────────────────────────────────────────────

def classify_intent(query: str) -> QueryIntent:
    """Classify query intent via LLM. Falls back to DATA_QUERY if unrecognised."""
    prompt = INTENT_CLASSIFIER_PROMPT.format(query=query)
    result = get_llm().invoke([HumanMessage(content=prompt)])
    raw = result.content.strip().lower()

    intent_map = {i.value: i for i in QueryIntent}
    intent = intent_map.get(raw)

    if intent is None:
        logger.warning("Classifier returned unknown intent '%s', defaulting to data_query.", raw)
        intent = QueryIntent.DATA_QUERY

    return intent


# ─────────────────────────────────────────────
# AGENT BUILDER
# ─────────────────────────────────────────────

def build_agent(agent_name: AgentName, table_names: list[str], use_memory: bool):
    """Build a scoped SQL agent. Only tools permitted for that agent are loaded."""

    restricted_db = SQLDatabase.from_uri(POSTGRES_URI, include_tables=table_names)

    class ScopedToolkit(SQLDatabaseToolkit):
        def get_tools(self):
            all_tools = super().get_tools()
            allowed = set(AGENT_ALLOWED_TOOLS[agent_name])
            return [t for t in all_tools if t.name in allowed]

    scoped_toolkit = ScopedToolkit(db=restricted_db, llm=get_llm())
    prompt = AGENT_PROMPTS[agent_name]

    agent_executor = create_sql_agent(
        llm=get_llm(),
        toolkit=scoped_toolkit,
        agent_type="tool-calling",
        prompt=prompt,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=AGENT_MAX_ITERATIONS,
        max_execution_time=AGENT_MAX_EXEC_TIME,
    )

    if use_memory:
        return RunnableWithMessageHistory(
            agent_executor,
            get_redis_history_safe,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

    return agent_executor


# ─────────────────────────────────────────────
# OUTPUT PARSER
# ─────────────────────────────────────────────

def format_response_value(value) -> str:
    """Convert agent output to a clean string."""
    if isinstance(value, (list, dict)):
        return json.dumps(value, indent=2)
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                return json.dumps(parsed, indent=2)
        except Exception:
            pass
    return str(value)


def parse_agent_output(text) -> dict:
    """Safely parse the agent's JSON output into a structured dict."""
    if isinstance(text, dict):
        return text

    raw = str(text)
    for m in re.finditer(r"\{[\s\S]+?\}", raw):
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            continue

    return {"response": raw, "reasoning": "", "source": []}


# ─────────────────────────────────────────────
# TABLE VALIDATOR
# ─────────────────────────────────────────────

def validate_tables(table_list: list[str]) -> list[str]:
    """Return list of table names that do not exist in the DB."""
    existing = get_validation_db().get_usable_table_names()
    return [t for t in table_list if t not in existing]


# ─────────────────────────────────────────────
# ENDPOINT
# POST /chatbot
#
# Query params (both optional):
#   agent_names — comma-separated, default: "sql_agent"
#   table_names — comma-separated, default: "catalogs"
# ─────────────────────────────────────────────

@router.post("/chatbot")
async def chatbot(
    req: ChatRequest,
    agent_names: str = Query(default=DEFAULT_AGENT_NAMES, description="Comma-separated agent names"),
    table_names: str = Query(default=DEFAULT_TABLE_NAMES, description="Comma-separated table names"),
):
    # ── 1. Parse & validate agent names ─────────────────────────────────────
    raw_agents = [a.strip().lower() for a in agent_names.split(",")]
    agent_list = list(dict.fromkeys(a for a in raw_agents if a))   # dedup, preserve order

    if not agent_list:
        return JSONResponse(status_code=400, content={
            "response": "No agent names provided.", "reasoning": "", "source": []
        })

    if len(agent_list) > MAX_AGENTS_PER_REQUEST:
        return JSONResponse(status_code=400, content={
            "response": f"Too many agents. Maximum allowed is {MAX_AGENTS_PER_REQUEST}.",
            "reasoning": "", "source": []
        })

    invalid_agents = [a for a in agent_list if a not in VALID_AGENT_NAMES]
    if invalid_agents:
        return JSONResponse(status_code=400, content={
            "response": (
                f"Unknown agent(s): {invalid_agents}. "
                f"Valid options are: {sorted(VALID_AGENT_NAMES)}."
            ),
            "reasoning": "", "source": []
        })

    selected_agents = [AgentName(a) for a in agent_list]

    # ── 2. Parse & validate table names ─────────────────────────────────────
    raw_tables = [t.strip() for t in table_names.split(",")]
    table_list = list(dict.fromkeys(t for t in raw_tables if t))   # dedup

    if not table_list:
        return JSONResponse(status_code=400, content={
            "response": "No table names provided.", "reasoning": "", "source": []
        })

    if len(table_list) > MAX_TABLES_PER_REQUEST:
        return JSONResponse(status_code=400, content={
            "response": f"Too many tables. Maximum allowed is {MAX_TABLES_PER_REQUEST}.",
            "reasoning": "", "source": []
        })

    invalid_tables = validate_tables(table_list)
    if invalid_tables:
        return JSONResponse(status_code=400, content={
            "response": f"Table(s) {invalid_tables} do not exist.",
            "reasoning": "", "source": []
        })

    include_reasoning = req.reasoning.lower() == "on"
    include_memory    = req.memory.lower() == "on"

    try:
        # ── 3. Classify intent ───────────────────────────────────────────────
        intent = classify_intent(req.query)
        logger.info("Classified intent: %s", intent.value)

        # ── 4. Compute allowed intents across all selected agents ────────────
        allowed_intents: set[QueryIntent] = set()
        for agent in selected_agents:
            allowed_intents.update(AGENT_ALLOWED_INTENTS[agent])

        # ── 5. Gate: block if intent not covered by any selected agent ───────
        if intent not in allowed_intents:
            owner_agent      = INTENT_OWNER[intent]
            owner_name       = AGENT_DISPLAY_NAMES[owner_agent]
            selected_display = [AGENT_DISPLAY_NAMES[a] for a in selected_agents]
            return JSONResponse(status_code=422, content={
                "response": (
                    f"Your question is about '{intent.value.replace('_', ' ')}', "
                    f"which is handled by '{owner_name}'. "
                    f"You selected: {selected_display}. "
                    f"Please select '{owner_name}' to answer this question."
                ),
                "reasoning": "",
                "source": [],
                "intent_detected": intent.value,
                "agent_used": "none",
            })

        # ── 6. Route to the responsible agent ────────────────────────────────
        responsible_agent = INTENT_OWNER[intent]
        if responsible_agent not in selected_agents:
            responsible_agent = selected_agents[0]

        logger.info(
            "Routing to agent '%s' for intent '%s'",
            responsible_agent.value, intent.value
        )

        # ── 7. Build session ID & config ─────────────────────────────────────
        session_id = req.session_id or str(uuid.uuid4())
        scoped_sid = build_scoped_session_id(session_id, agent_list, table_list)
        config = {
            "configurable": {"session_id": scoped_sid},
        }

        # ── 8. Build & invoke agent ───────────────────────────────────────────
        agent = build_agent(
            agent_name=responsible_agent,
            table_names=table_list,
            use_memory=include_memory,
        )

        result = agent.invoke(
            {
                "input": req.query,
                "reasoning_mode": "ON" if include_reasoning else "OFF",
            },
            config=config if include_memory else None,
        )

        # ── 9. Parse & return response ────────────────────────────────────────
        text       = result.get("output", "")
        agent_data = parse_agent_output(text)
        cleaned    = format_response_value(agent_data.get("response", ""))

        if include_reasoning:
            response_obj = ChatResponseWithReasoning(
                agent_used=AGENT_DISPLAY_NAMES[responsible_agent],
                intent_detected=intent.value,
                response=cleaned,
                reasoning=agent_data.get("reasoning", ""),
                source=agent_data.get("source", []),
            )
        else:
            response_obj = ChatResponseWithoutReasoning(
                agent_used=AGENT_DISPLAY_NAMES[responsible_agent],
                intent_detected=intent.value,
                response=cleaned,
                source=agent_data.get("source", []),
            )

        return JSONResponse(content=response_obj.dict())

    except TimeoutError:
        logger.error(
            "Agent timed out | session=%s agents=%s tables=%s",
            req.session_id, agent_list, table_list,
        )
        return JSONResponse(status_code=504, content={
            "response": "The query took too long. Please simplify your request.",
            "reasoning": "Request timed out." if include_reasoning else "",
            "source": [],
        })

    except Exception:
        logger.exception(
            "Unhandled error | session=%s agents=%s tables=%s query=%s",
            req.session_id, agent_list, table_list, req.query,
        )
        return JSONResponse(status_code=500, content={
            "response": "I encountered an error while processing your request.",
            "reasoning": "An internal server error occurred." if include_reasoning else "",
            "source": [],
        })


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

# @router.get("/health")
# async def health_check():
#     redis_ok = True
#     try:
#         get_redis_history("__healthcheck__").messages
#     except Exception:
#         redis_ok = False

#     return {
#         "status": "ok",
#         "redis": "ok" if redis_ok else "degraded",
#         "available_agents": sorted(VALID_AGENT_NAMES),
#         "defaults": {
#             "agent": DEFAULT_AGENT_NAMES,
#             "table": DEFAULT_TABLE_NAMES,
#         },
#     }