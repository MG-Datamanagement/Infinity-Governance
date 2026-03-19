"""
Unified Metadata Ingestion API - Single File Application

"""

import os
import re
import json
import logging
import asyncio
import asyncpg
import uvicorn
import copy
import psycopg2

from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from openai import AsyncAzureOpenAI  
from asyncpg import Pool
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv
from pathlib import Path
# Config
from config import Settings

# DataHub SDK imports
from datahub.ingestion.run.pipeline import Pipeline
from datahub.ingestion.api.common import RecordEnvelope
from datahub.metadata.schema_classes import (
    DatasetSnapshotClass,
    DatasetPropertiesClass,
    SchemaMetadataClass,
    DatasetProfileClass,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

#  AZURE OPENAI CLIENT CONFIGURATION

AZURE_CONFIG = {
    "api_key":          os.getenv("AZURE_OPENAI_API_KEY"),
    "azure_endpoint":   os.getenv("AZURE_OPENAI_ENDPOINT"),
    "api_version":      os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    "azure_deployment": os.getenv("AZURE_DEPLOYMENT", "gpt-35-turbo-16k"),
}

# Azure OpenAI client singleton
_azure_client = None

def get_azure_client():
    """Get or create the Azure OpenAI client"""
    global _azure_client
    if _azure_client is None:
        if not AZURE_CONFIG.get("api_key") or not AZURE_CONFIG.get("azure_endpoint"):
            raise ValueError("Azure OpenAI credentials not configured")
        from openai import AsyncAzureOpenAI
        _azure_client = AsyncAzureOpenAI(
            api_key=AZURE_CONFIG["api_key"],
            azure_endpoint=AZURE_CONFIG["azure_endpoint"],
            api_version=AZURE_CONFIG["api_version"]
        )
    return _azure_client

# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

load_dotenv()
settings = Settings()

# ============================================================================
# DATABASE SCHEMA initialization
# ============================================================================


# Load INIT_DB_SQL from scripts/init.sql
SCRIPT_DIR = Path(__file__).parent  # Directory of app.py
INIT_SQL_PATH = SCRIPT_DIR / 'scripts' / 'init.sql'

if not INIT_SQL_PATH.exists():
    raise FileNotFoundError(f"SQL init file not found: {INIT_SQL_PATH}")

with open(INIT_SQL_PATH, 'r', encoding='utf-8') as f:
    INIT_DB_SQL = f.read()

# ============================================================================
# INGESTION MODULE IMPORTS
# ============================================================================

from ingestion import (
    SOURCE_TEMPLATES,
    PostgresSink,
    PostgresSinkReport,
    Database,
    IngestionManager,
)


db = Database()
ingestion_manager = IngestionManager()

# ============================================================================
# API LOG HELPER
# ============================================================================

async def log_api_action(
    endpoint: str,
    method: str,
    action_summary: str,
    entity_type: str = None,
    entity_id: str = None,
    entity_name: str = None,
    owner_id: str = None,
    status_code: int = 200,
    request_body: dict = None,
    response_summary: str = None
):
    """Write a record to api_logs table (non-blocking, errors are swallowed)"""
    try:
        await db.execute("""
            INSERT INTO api_logs 
                (endpoint, method, action_summary, entity_type, entity_id, entity_name,
                 owner_id, status_code, request_body, response_summary)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
            endpoint, method, action_summary, entity_type, entity_id, entity_name,
            owner_id, status_code,
            json.dumps(request_body) if request_body else None,
            response_summary
        )
    except Exception as e:
        logger.warning(f"Failed to write api_log: {e}")

# ============================================================================
# FASTAPI LIFESPAN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    # Startup
    logger.info("Starting up...")
    await db.connect(settings)
    ingestion_manager.set_db(db)
    ingestion_manager.set_settings(settings)

    try:
        from services.compliance import init_compliance_engine
        await init_compliance_engine()
        logger.info("Compliance engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize compliance engine: {e}")
 
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await db.disconnect()

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Unified Metadata Ingestion API",
    description="Ingest metadata from multiple sources using DataHub SDK",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# API ROUTES
# ============================================================================


from services.dashboard import router as dashboard_router
app.include_router(dashboard_router)

from services.datasource import router as datasource_router
app.include_router(datasource_router)

from services.owner import router as owner_router
app.include_router(owner_router)


from services.tag import router as tag_router
app.include_router(tag_router)


from services.lineage import router as lineage_router
app.include_router(lineage_router)

from services.datacard import router as datacard_router
app.include_router(datacard_router)

from services.tag_classify import router as tag_classify_router
app.include_router(tag_classify_router)


from services.job_logs import router as job_logs_router
app.include_router(job_logs_router)


from services.compliance import router as compliance_router
app.include_router(compliance_router)   

from services.chatbot import router as chatbot_router
app.include_router(chatbot_router)

from services.compliance_overview import router as compliance_overview_router
app.include_router(compliance_overview_router)  

from services.solr_search import router as solr_router
app.include_router(solr_router) 

from services.catalog_properties import router as catalog_properties_router
app.include_router(catalog_properties_router)   

from services.line_of_business import router as line_of_business_router
app.include_router(line_of_business_router) 

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    )