# Combined Unified API - Dataset Sync + Semantic Sync + Chat on Single Port
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import requests
import psycopg2
import asyncpg
import json
from datetime import datetime
import os
import logging
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager, asynccontextmanager
import uvicorn
from openai import AsyncAzureOpenAI
from pathlib import Path
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# INITIALIZE FASTAPI APP
# ============================================================================
app = FastAPI(
    title="Unified DataHub API",
    description="Combined Dataset Sync + Semantic Sync + Chatbot Service",
    version="3.0.0"
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
# ENVIRONMENT CONFIGURATION
# ============================================================================
DATAHUB_GRAPHQL_URL = os.getenv("DATAHUB_GRAPHQL_URL", "http://nginx-proxy/graphql")
# DATAHUB_GRAPHQL_URL = os.getenv("DATAHUB_GRAPHQL_URL", "http://nginx-proxy/graphql")

PG_HOST = os.getenv("PG_HOST", "postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "semantic_search")
PG_USER = os.getenv("PG_USER", "semantic_user")
PG_PASS = os.getenv("PG_PASS", "semantic_pass")

# Azure OpenAI Configuration
AZURE_CONFIG = {
    "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
    "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
    "azure_deployment": os.getenv("AZURE_DEPLOYMENT", "gpt-35-turbo-16k")
}

# Initialize Azure client
missing = []
for k, v in [("api_key", AZURE_CONFIG["api_key"]), ("azure_endpoint", AZURE_CONFIG["azure_endpoint"])]:
    if not v:
        missing.append(k)
        logger.error(f"Missing {k}")
    else:
        logger.info(f"{k}: SET (len={len(v)})")

if missing:
    logger.warning("Azure client partially configured - will fail on API calls")
    client = None
else:
    try:
        client = AsyncAzureOpenAI(
            api_key=AZURE_CONFIG["api_key"],
            azure_endpoint=AZURE_CONFIG["azure_endpoint"],
            api_version=AZURE_CONFIG["api_version"]
        )
        logger.info("Azure client ready!")
    except Exception as e:
        logger.error(f"Failed to initialize Azure client: {e}", exc_info=True)
        client = None

# Database configuration
DB_CONFIG = {
    "host": PG_HOST,
    "port": PG_PORT,
    "user": PG_USER,
    "password": PG_PASS,
    "database": PG_DB
}

# Global pools
pg_pool = None
gql_client = None

# ============================================================================
# PYDANTIC MODELS
# ============================================================================
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    conversation_history: List[Message] = []

class ChatResponse(BaseModel):
    answer: str
    query_type: Optional[str] = None
    sql_query: Optional[str] = None
    data: Optional[List[Dict]] = None
    timestamp: str = ""

class SyncResponse(BaseModel):
    status: str
    total_processed: int
    message: str

class DataCardResponse(BaseModel):
    dataset_id: int
    urn: str
    name: str
    data_card: str
    generated_at: datetime
    status: str

class GenerateRequest(BaseModel):
    max_tokens: int = 2000

class SyncStats(BaseModel):
    datasets: int = 0
    domains: int = 0
    tags: int = 0
    glossary_terms: int = 0
    owners: int = 0
    total: int = 0

# Tag Suggestion Models
class ExistingTag(BaseModel):
    urn: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None

class SuggestedTag(BaseModel):
    name: str
    confidence_score: float  # 0.0 to 1.0
    reasoning: str
    category: Optional[str] = None
    similar_tags: List[str] = []
    recommended_count: int = 0  # How many similar datasets have this tag

class DatasetMetadataAnalysis(BaseModel):
    schema_info: Optional[Dict[str, Any]] = None
    column_count: int = 0
    data_types: List[str] = []
    has_lineage: bool = False
    usage_pattern: Optional[str] = None
    platform: str = ""

class TagSuggestionResponse(BaseModel):
    status: str
    dataset_urn: str
    dataset_name: str
    platform: str
    existing_tags: List[ExistingTag] = []
    existing_tag_count: int = 0
    metadata_analysis: Optional[DatasetMetadataAnalysis] = None
    suggested_tags: List[SuggestedTag] = []
    suggestion_count: int = 0
    processing_metadata: Dict[str, Any] = {}
    timestamp: str = ""
    error: Optional[str] = None
    glossary_terms: int = 0
    owners: int = 0
    total: int = 0
    errors: int = 0

# ============================================================================
# SQL UPSERT FOR DATASET SYNC
# ============================================================================
UPSERT_SQL = """
INSERT INTO datahub_dataset_all (
    urn, name, origin, description, domain_urn, domain_name, domain_description,
    row_count, column_count, profile_timestamp, 
    all_field_paths, all_field_types, field_count,
    primary_keys, owner_urn, owner_title, owner_email, tag_urn, tag_name, tag_description,
    glossary_urn, glossary_name, glossary_definition, data_card, raw_json
) VALUES (
    %(urn)s, %(name)s, %(origin)s, %(description)s, %(domain_urn)s, %(domain_name)s, %(domain_description)s,
    %(row_count)s, %(column_count)s, %(profile_timestamp)s,
    COALESCE(%(all_field_paths)s, ARRAY[]::TEXT[]), COALESCE(%(all_field_types)s, ARRAY[]::TEXT[]), %(field_count)s,
    %(primary_keys)s, %(owner_urn)s, %(owner_title)s, %(owner_email)s, %(tag_urn)s, %(tag_name)s, %(tag_description)s,
    %(glossary_urn)s, %(glossary_name)s, %(glossary_definition)s, %(data_card)s, %(raw_json)s
) ON CONFLICT (urn) DO UPDATE SET
    name = EXCLUDED.name, origin = EXCLUDED.origin, description = EXCLUDED.description,
    domain_urn = EXCLUDED.domain_urn, domain_name = EXCLUDED.domain_name, domain_description = EXCLUDED.domain_description,
    row_count = EXCLUDED.row_count, column_count = EXCLUDED.column_count, profile_timestamp = EXCLUDED.profile_timestamp,
    all_field_paths = EXCLUDED.all_field_paths, all_field_types = EXCLUDED.all_field_types, field_count = EXCLUDED.field_count,
    primary_keys = EXCLUDED.primary_keys, owner_urn = EXCLUDED.owner_urn, owner_title = EXCLUDED.owner_title, 
    owner_email = EXCLUDED.owner_email, tag_urn = EXCLUDED.tag_urn, tag_name = EXCLUDED.tag_name, 
    tag_description = EXCLUDED.tag_description, glossary_urn = EXCLUDED.glossary_urn, 
    glossary_name = EXCLUDED.glossary_name, glossary_definition = EXCLUDED.glossary_definition,
    data_card = EXCLUDED.data_card, raw_json = EXCLUDED.raw_json, updated_at = CURRENT_TIMESTAMP
"""

# ============================================================================
# DATAHUB KNOWLEDGE BASE
# ============================================================================
DATAHUB_KNOWLEDGE = {
    "lineage": {
        "description": "Data lineage shows the flow of data from source to target. It helps track data transformations and dependencies.",
        "features": ["Upstream lineage", "Downstream lineage", "Impact analysis", "Data flow tracking"],
        "benefits": "Understand data provenance, debug issues, assess impact of changes"
    },
    "tags": {
        "description": "Tags are simple labels used to classify and organize datasets for easy discovery and governance.",
        "features": ["Custom tags", "Tag propagation", "Tag search", "Tag-based access control"],
        "benefits": "Better organization, faster discovery, consistent classification"
    },
    "glossary": {
        "description": "Business glossary provides standardized business terms and definitions for data governance.",
        "features": ["Term hierarchy", "Term lineage", "Term ownership", "Related terms"],
        "benefits": "Shared vocabulary, metadata standardization, business-IT alignment"
    },
    "ownership": {
        "description": "Data ownership defines who is responsible for managing and maintaining datasets.",
        "features": ["Owner assignment", "Multi-owner support", "Owner notifications", "Ownership hierarchy"],
        "benefits": "Clear responsibility, better accountability, easier escalation"
    },
    "domains": {
        "description": "Domains organize datasets by business function or data area for better governance.",
        "features": ["Domain creation", "Domain hierarchy", "Domain-based access control", "Domain analytics"],
        "benefits": "Logical organization, easier governance, better data discovery"
    },
    "metadata": {
        "description": "Metadata includes information about datasets like schema, statistics, and documentation.",
        "features": ["Schema documentation", "Data profiling", "Custom properties", "Metadata templates"],
        "benefits": "Better data understanding, quality tracking, automated metadata capture"
    },
    "search": {
        "description": "Full-text search allows users to find datasets, dashboards, and metrics across the entire data catalog.",
        "features": ["Full-text search", "Advanced filters", "Faceted search", "Search suggestions"],
        "benefits": "Quick discovery, better exploration, powerful analytics"
    }
}

# ============================================================================
# ENHANCED CHATBOT FUNCTIONS
# ============================================================================# ============================================================================
# GRAPHQL QUERIES FOR SEMANTIC SYNC
# ============================================================================
DATASET_QUERY = gql("""
query DataCatalog {
  search(input: {
    type: DATASET
    query: "*"
    start: 0
    count: 100
  }) {
    total
    searchResults {
      entity {
        ... on Dataset {
          name
          urn
          properties {
            name
            description
            lastModified { time }
            created
            createdActor
          }
          platform { name }
          tags {
            tags {
              tag {
                urn
                properties { name colorHex }
              }
            }
          }
          domain {
            domain {
              urn
              properties { name }
            }
          }
        }
      }
    }
  }
}
""")

DOMAIN_QUERY = gql("""
query listAllDomains {
  listDomains(input: { start: 0, count: 100 }) {
    total
    domains {
      urn
      id
      properties {
        name
        description
        createdOn {
          actor { username }
        }
      }
      ownership {
        owners {
          owner {
            ... on CorpUser { username }
          }
        }
      }
    }
  }
}
""")

TAG_QUERY = gql("""
query ListAllTags {
  searchAcrossEntities(input: {
    types: [TAG]
    query: ""
    start: 0
    count: 100
  }) {
    total
    searchResults {
      entity {
        ... on Tag {
          urn
          name
          properties { description colorHex }
        }
      }
    }
  }
}
""")

GLOSSARY_QUERY = gql("""
query SearchGlossaryTerms {
  searchAcrossEntities(input: {
    types: [GLOSSARY_TERM]
    query: "*"
    start: 0
    count: 100
  }) {
    total
    searchResults {
      entity {
        ... on GlossaryTerm {
          urn
          name
          glossaryTermInfo { definition }
        }
      }
    }
  }
}
""")

USERS_QUERY = gql("""
query ListUsers {
  listUsers(input: { start: 0, count: 100 }) {
    total
    users {
      urn
      type
      username
    }
  }
}
""")

GRAPHQL_QUERY = """
query ListAllDatasetsComplete {
  search(input: { type: DATASET, query: "*", count: 100, start: 0 }) {
    total
    searchResults {
      entity {
        ... on Dataset {
          urn
          name
          origin
          editableProperties { description }
          domain {
            domain {
              urn
              properties { name description }
            }
          }
          datasetProfiles(limit:1){
            rowCount
            columnCount
            timestampMillis
          }
          schemaMetadata {
            fields {
              fieldPath
              type
            }
            primaryKeys
          }
          ownership {
            owners {
              owner {
                ... on CorpUser {
                  urn
                  properties {
                    title
                    email
                  }
                }
              }
            }
          }
          globalTags {
            tags {
              tag {
                urn
                properties {
                  name
                  description
                }
              }
            }
          }
          glossaryTerms {
            terms {
              term {
                urn
                name
                properties { name definition }
              }
            }
          }
        }
      }
    }
  }
}
"""

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def safe_str(value: Any) -> str:
    return str(value) if value is not None else ""

def safe_ts(value: Any) -> Optional[str]:
    if value is None or value == '0':
        return None
    if isinstance(value, str) and value.lower() in ['null', 'none', '']:
        return None
    try:
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace('Z', '+00:00')).isoformat()
        return value.isoformat() if hasattr(value, 'isoformat') else None
    except:
        return None

def safe_dict_access(obj: Any, *keys) -> Any:
    current = obj
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current

async def get_pg_pool():
    return await asyncpg.create_pool(
        host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS,
        min_size=1, max_size=20, command_timeout=60
    )

@contextmanager
def get_db_connection():
    """Get database connection as context manager"""
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        cursor_factory=RealDictCursor
    )
    try:
        yield conn
    finally:
        conn.close()


# ============================================================================
# DATABASE SCHEMA INITIALIZATION
# ============================================================================
async def init_schema(conn):
    """Create tables for ALL entities"""
    schema_sql = """
    CREATE TABLE IF NOT EXISTS datahub_datasets (
        id SERIAL PRIMARY KEY,
        urn TEXT UNIQUE NOT NULL,
        name TEXT,
        platform_name TEXT,
        created TIMESTAMPTZ,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS datahub_dataset_properties (
        id SERIAL PRIMARY KEY,
        dataset_urn TEXT REFERENCES datahub_datasets(urn) ON DELETE CASCADE,
        prop_name TEXT,
        description TEXT,
        created TIMESTAMPTZ,
        last_modified_time TIMESTAMPTZ,
        created_actor TEXT
    );

    CREATE TABLE IF NOT EXISTS datahub_domains (
        id SERIAL PRIMARY KEY,
        urn TEXT UNIQUE NOT NULL,
        id_val TEXT,
        name TEXT,
        description TEXT,
        created_actor TEXT
    );

    CREATE TABLE IF NOT EXISTS datahub_tags (
        id SERIAL PRIMARY KEY,
        urn TEXT UNIQUE NOT NULL,
        name TEXT,
        description TEXT,
        color_hex TEXT
    );

    CREATE TABLE IF NOT EXISTS datahub_glossary (
        id SERIAL PRIMARY KEY,
        urn TEXT UNIQUE NOT NULL,
        name TEXT,
        definition TEXT
    );

    CREATE TABLE IF NOT EXISTS datahub_owners (
        id SERIAL PRIMARY KEY,
        urn TEXT UNIQUE NOT NULL,
        type TEXT,
        username TEXT
    );

    CREATE TABLE IF NOT EXISTS datahub_dataset_all (
        id SERIAL PRIMARY KEY,
        urn TEXT UNIQUE NOT NULL,
        name TEXT,
        origin TEXT,
        description TEXT,
        domain_urn TEXT,
        domain_name TEXT,
        domain_description TEXT,
        row_count INTEGER,
        column_count INTEGER,
        profile_timestamp BIGINT,
        all_field_paths TEXT[],
        all_field_types TEXT[],
        field_count INTEGER,
        primary_keys TEXT,
        owner_urn TEXT,
        owner_title TEXT,
        owner_email TEXT,
        tag_urn TEXT,
        tag_name TEXT,
        tag_description TEXT,
        glossary_urn TEXT,
        glossary_name TEXT,
        glossary_definition TEXT,
        data_card TEXT,
        raw_json JSONB,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        await conn.execute(schema_sql)
        logger.info("Schema initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Schema failed: {e}")
        return False

def create_datasets_table():
    """Create datasets table via psycopg2 with retry logic"""
    import time
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS datahub_dataset_all (
                            id SERIAL PRIMARY KEY,
                            urn TEXT UNIQUE NOT NULL,
                            name TEXT,
                            origin TEXT,
                            description TEXT,
                            domain_urn TEXT,
                            domain_name TEXT,
                            domain_description TEXT,
                            row_count INTEGER,
                            column_count INTEGER,
                            profile_timestamp BIGINT,
                            all_field_paths TEXT[],
                            all_field_types TEXT[],
                            field_count INTEGER,
                            primary_keys TEXT,
                            owner_urn TEXT,
                            owner_title TEXT,
                            owner_email TEXT,
                            tag_urn TEXT,
                            tag_name TEXT,
                            tag_description TEXT,
                            glossary_urn TEXT,
                            glossary_name TEXT,
                            glossary_definition TEXT,
                            data_card TEXT,
                            raw_json JSONB,
                            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    conn.commit()
                    logger.info("✅ Dataset table created/verified")
                    return True
                except Exception as e:
                    logger.error(f"Error creating table: {e}")
                    conn.rollback()
                    raise
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to create dataset table after {max_retries} attempts: {e}")
                return False
    return False

# ============================================================================
# SEMANTIC SYNC FUNCTIONS
# ============================================================================
async def safe_truncate(conn, table: str) -> bool:
    try:
        await conn.execute(f"TRUNCATE TABLE {table} CASCADE")
        logger.info(f"Truncated {table}")
        return True
    except Exception as e:
        logger.warning(f"Truncate {table}: {e}")
        return False

async def safe_insert(conn, sql: str, args: tuple, table: str) -> bool:
    try:
        await conn.execute(sql, *args)
        return True
    except Exception as e:
        logger.warning(f"INSERT {table}: {e}")
        return False

async def sync_datasets(conn) -> int:
    """Sync datasets using dataset-specific query"""
    try:
        result = await gql_client.execute_async(DATASET_QUERY)
        data = result['search']
        count = 0
        
        for search_result in data['searchResults']:
            entity = search_result['entity']
            urn = safe_str(entity.get('urn'))
            
            platform_name = safe_str(safe_dict_access(entity, 'platform', 'name'))
            created = safe_ts(safe_dict_access(entity, 'properties', 'created'))
            await safe_insert(conn, """
                INSERT INTO datahub_datasets (urn, name, platform_name, created) 
                VALUES ($1, $2, $3, $4) ON CONFLICT (urn) DO NOTHING
            """, (urn, entity.get('name'), platform_name, created), 'datahub_datasets')
            
            props = safe_dict_access(entity, 'properties')
            if props:
                await safe_insert(conn, """
                    INSERT INTO datahub_dataset_properties (dataset_urn, prop_name, description, 
                        created, last_modified_time, created_actor)
                    VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING
                """, (urn, props.get('name'), props.get('description'),
                      safe_ts(props.get('created')), 
                      safe_ts(safe_dict_access(props, 'lastModified', 'time')),
                      props.get('createdActor')), 'datahub_dataset_properties')
            
            count += 1
        logger.info(f"Synced {count} datasets")
        return count
    except Exception as e:
        logger.error(f"Dataset sync failed: {e}")
        return 0

async def sync_domains(conn) -> int:
    """Sync domains using domain-specific query"""
    try:
        result = await gql_client.execute_async(DOMAIN_QUERY)
        domains_data = result['listDomains']['domains']
        count = 0
        
        for domain in domains_data:
            urn = domain.get('urn')
            props = safe_dict_access(domain, 'properties')
            created_actor = safe_dict_access(props, 'createdOn', 'actor', 'username')
            
            await safe_insert(conn, """
                INSERT INTO datahub_domains (urn, id_val, name, description, created_actor)
                VALUES ($1, $2, $3, $4, $5) ON CONFLICT (urn) DO NOTHING
            """, (urn, domain.get('id'), props.get('name'), 
                  props.get('description'), created_actor), 'datahub_domains')
            count += 1
        logger.info(f"Synced {count} domains")
        return count
    except Exception as e:
        logger.error(f"Domain sync failed: {e}")
        return 0

async def sync_tags(conn) -> int:
    """Sync tags using tag-specific query"""
    try:
        result = await gql_client.execute_async(TAG_QUERY)
        tags_data = result['searchAcrossEntities']['searchResults']
        count = 0
        
        for search_result in tags_data:
            entity = search_result['entity']
            if entity.get('name'):
                urn = entity.get('urn')
                props = safe_dict_access(entity, 'properties')
                
                await safe_insert(conn, """
                    INSERT INTO datahub_tags (urn, name, description, color_hex)
                    VALUES ($1, $2, $3, $4) ON CONFLICT (urn) DO NOTHING
                """, (urn, entity.get('name'), props.get('description'), 
                      props.get('colorHex')), 'datahub_tags')
                count += 1
        logger.info(f"Synced {count} tags")
        return count
    except Exception as e:
        logger.error(f"Tag sync failed: {e}")
        return 0

async def sync_glossary(conn) -> int:
    """Sync glossary terms using glossary-specific query"""
    try:
        result = await gql_client.execute_async(GLOSSARY_QUERY)
        glossary_data = result['searchAcrossEntities']['searchResults']
        count = 0
        
        for search_result in glossary_data:
            entity = search_result['entity']
            glossary_info = safe_dict_access(entity, 'glossaryTermInfo')
            
            await safe_insert(conn, """
                INSERT INTO datahub_glossary (urn, name, definition)
                VALUES ($1, $2, $3) ON CONFLICT (urn) DO NOTHING
            """, (entity.get('urn'), entity.get('name'), 
                  glossary_info.get('definition')), 'datahub_glossary')
            count += 1
        logger.info(f"Synced {count} glossary terms")
        return count
    except Exception as e:
        logger.error(f"Glossary sync failed: {e}")
        return 0

async def sync_owners(conn) -> int:
    """Sync owners using users query + domain ownership"""
    try:
        result = await gql_client.execute_async(USERS_QUERY)
        users_data = result['listUsers']['users']
        count = 0
        
        for user in users_data:
            await safe_insert(conn, """
                INSERT INTO datahub_owners (urn, type, username)
                VALUES ($1, $2, $3) ON CONFLICT (urn) DO NOTHING
            """, (user.get('urn'), user.get('type'), user.get('username')), 'datahub_owners')
            count += 1
        logger.info(f"Synced {count} owners")
        return count
    except Exception as e:
        logger.error(f"Owners sync failed: {e}")
        return 0

# ============================================================================
# DATASET SYNC FUNCTIONS
# ============================================================================
def flatten_dataset_data(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """Stores ALL columns as arrays + data_card=NULL - matches app.py implementation"""
    def safe_get(obj, key, default=''):
        return obj.get(key, default) if obj and isinstance(obj, dict) else default
    
    def safe_list_get(lst, index, default=None):
        return lst[index] if lst and isinstance(lst, list) and index < len(lst) else default or {}
    
    def safe_numeric(value):
        if value == '' or value is None:
            return None
        try:
            return int(value)
        except:
            return None
    
    flattened = {
        'urn': safe_get(dataset, 'urn'),
        'name': safe_get(dataset, 'name'),
        'origin': safe_get(dataset, 'origin'),
        'description': safe_get(safe_get(dataset, 'editableProperties'), 'description'),
        'data_card': None,
        'raw_json': json.dumps(dataset, ensure_ascii=False)
    }
    
    # Domain information
    domain = safe_get(dataset, 'domain')
    flattened.update({
        'domain_urn': safe_get(safe_get(domain, 'domain'), 'urn'),
        'domain_name': safe_get(safe_get(safe_get(domain, 'domain'), 'properties'), 'name'),
        'domain_description': safe_get(safe_get(safe_get(domain, 'domain'), 'properties'), 'description')
    })
    
    # Profile statistics
    profile = safe_list_get(safe_get(dataset, 'datasetProfiles', []), 0)
    flattened.update({
        'row_count': safe_numeric(safe_get(profile, 'rowCount')),
        'column_count': safe_numeric(safe_get(profile, 'columnCount')),
        'profile_timestamp': safe_numeric(safe_get(profile, 'timestampMillis'))
    })
    
    # ALL COLUMNS AS ARRAYS
    schema = safe_get(dataset, 'schemaMetadata')
    fields = safe_get(schema, 'fields', [])
    field_paths = [safe_get(f, 'fieldPath') for f in fields if safe_get(f, 'fieldPath')]
    field_types = [safe_get(f, 'type') for f in fields if safe_get(f, 'type')]
    
    flattened.update({
        'all_field_paths': field_paths,
        'all_field_types': field_types,
        'field_count': len(fields),
        'primary_keys': json.dumps(safe_get(schema, 'primaryKeys', []))
    })
    
    # Owner information
    owners = safe_get(safe_get(dataset, 'ownership'), 'owners', [])
    owner = safe_list_get(owners, 0)
    owner_obj = safe_get(owner, 'owner')
    owner_props = safe_get(owner_obj, 'properties')
    flattened.update({
        'owner_urn': safe_get(owner_obj, 'urn'),
        'owner_title': safe_get(owner_props, 'title'),
        'owner_email': safe_get(owner_props, 'email')
    })
    
    # Tag information
    tags = safe_get(safe_get(dataset, 'globalTags'), 'tags', [])
    tag = safe_list_get(tags, 0)
    tag_obj = safe_get(tag, 'tag')
    tag_props = safe_get(tag_obj, 'properties')
    flattened.update({
        'tag_urn': safe_get(tag_obj, 'urn'),
        'tag_name': safe_get(tag_props, 'name'),
        'tag_description': safe_get(tag_props, 'description')
    })
    
    # Glossary term information
    terms = safe_get(safe_get(dataset, 'glossaryTerms'), 'terms', [])
    term = safe_list_get(terms, 0)
    term_obj = safe_get(term, 'term')
    term_props = safe_get(term_obj, 'properties')
    flattened.update({
        'glossary_urn': safe_get(term_obj, 'urn'),
        'glossary_name': safe_get(term_obj, 'name'),
        'glossary_definition': safe_get(term_props, 'definition')
    })
    
    return flattened


# ============================================================================
# CHAT FUNCTIONS
# ============================================================================
def get_database_schema():
    """Get database schema information"""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        schema_info = []
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table['table_name']
            
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            
            columns = cursor.fetchall()
            
            try:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                samples = cursor.fetchall()
                sample_data = [dict(row) for row in samples]
            except:
                sample_data = []
            
            schema_info.append({
                'table': table_name,
                'columns': [
                    {
                        'name': col['column_name'],
                        'type': col['data_type'],
                        'nullable': col['is_nullable']
                    }
                    for col in columns
                ],
                'sample_data': sample_data
            })
        
        return schema_info

def execute_sql_query(sql_query: str) -> List[Dict]:
    """Execute SQL query safely"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            sql_clean = sql_query.strip().upper()
            if not sql_clean.startswith('SELECT'):
                raise ValueError("Only SELECT queries are allowed")
            
            cursor.execute(sql_query)
            results = cursor.fetchall()
            return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"SQL execution error: {str(e)}")
        raise e

# ============================================================================
# TAG SUGGESTION FUNCTIONS
# ============================================================================

def validate_dataset_urn(urn: str) -> tuple:
    """
    Validate URN format: urn:li:dataset:(urn:li:dataPlatform:platform,name,environment)
    Returns: (is_valid, error_message)
    """
    if not urn or not isinstance(urn, str):
        return False, "URN must be a non-empty string"
    
    if not urn.startswith("urn:li:dataset:("):
        return False, "Invalid URN format. Expected format: urn:li:dataset:(urn:li:dataPlatform:platform,name,environment)"
    
    if not urn.endswith(")"):
        return False, "Invalid URN format - missing closing parenthesis"
    
    return True, None

def get_dataset_by_urn(urn: str) -> Optional[Dict]:
    """Get dataset details from database by URN"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT id, urn, name, origin, description, 
                       domain_name, owner_urn, tag_urn, tag_name, raw_json,
                       field_count, all_field_types, all_field_paths
                FROM datahub_dataset_all
                WHERE urn = %s
            """, (urn,))
            result = cursor.fetchone()
            
            if result:
                result_dict = dict(result)
                # Extract platform from URN
                # Format: urn:li:dataset:(urn:li:dataPlatform:PLATFORM,name,env)
                try:
                    platform_part = urn.split("urn:li:dataPlatform:")[1].split(",")[0]
                    result_dict['platform'] = platform_part
                except:
                    result_dict['platform'] = 'unknown'
                return result_dict
            return None
    except Exception as e:
        logger.error(f"Error fetching dataset: {e}")
        return None

def get_existing_tags_for_dataset(dataset_urn: str) -> List[ExistingTag]:
    """Get all existing tags assigned to a dataset with metadata"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT DISTINCT urn, name, description
                FROM datahub_tags
                WHERE urn IN (
                    SELECT DISTINCT tag_urn 
                    FROM datahub_dataset_all 
                    WHERE urn = %s AND tag_urn IS NOT NULL
                )
                ORDER BY name
            """, (dataset_urn,))
            
            tags = cursor.fetchall()
            return [
                ExistingTag(
                    urn=tag.get('urn', ''),
                    name=tag.get('name', ''),
                    description=tag.get('description'),
                    category="custom_tag"
                )
                for tag in tags
            ]
    except Exception as e:
        logger.error(f"Error fetching existing tags: {e}")
        return []

def extract_metadata_analysis(dataset: Dict) -> DatasetMetadataAnalysis:
    """Extract and analyze dataset metadata for tag recommendations"""
    try:
        schema_info = {}
        column_count = dataset.get('field_count', 0)
        data_types = []
        
        # Parse field types
        if dataset.get('all_field_types'):
            try:
                field_types_str = dataset.get('all_field_types', '[]')
                if isinstance(field_types_str, str):
                    data_types = json.loads(field_types_str) if field_types_str.startswith('[') else field_types_str.split(',')
                else:
                    data_types = field_types_str if isinstance(field_types_str, list) else []
            except:
                data_types = []
        
        # Extract schema info from raw_json if available
        if dataset.get('raw_json'):
            try:
                raw = json.loads(dataset['raw_json']) if isinstance(dataset['raw_json'], str) else dataset['raw_json']
                if 'schemaMetadata' in raw:
                    schema_info = {'fields': len(raw.get('schemaMetadata', {}).get('fields', []))}
            except:
                pass
        
        return DatasetMetadataAnalysis(
            schema_info=schema_info or None,
            column_count=column_count,
            data_types=list(set(data_types))[:10],  # Top 10 unique types
            has_lineage=bool(dataset.get('origin')),
            usage_pattern=None,  # Could be enriched with query logs
            platform=dataset.get('platform', 'unknown')
        )
    except Exception as e:
        logger.error(f"Error analyzing metadata: {e}")
        return DatasetMetadataAnalysis()

def find_similar_datasets(dataset: Dict, limit: int = 5) -> List[Dict]:
    """Find similar datasets by domain and naming patterns"""
    try:
        domain = dataset.get('domain_name', '')
        
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Find similar datasets by domain
            cursor.execute("""
                SELECT DISTINCT urn, name, tag_urn, tag_name, tag_description
                FROM datahub_dataset_all
                WHERE domain_name = %s
                AND urn != %s
                AND tag_urn IS NOT NULL
                AND tag_name IS NOT NULL
                LIMIT %s
            """, (domain, dataset.get('urn'), limit * 3))
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error finding similar datasets: {e}")
        return []

def find_matching_tag(input_tag: str, available_tags: List[str]) -> Optional[str]:
    """
    Find matching tag from available tags using fuzzy matching.
    Handles variations like 'hr-data', 'hr_data', 'hr data'
    Returns the exact tag name from database or None if no match
    """
    input_normalized = input_tag.strip().lower()
    input_normalized = input_normalized.replace('-', ' ').replace('_', ' ')
    
    # First try exact match
    for available in available_tags:
        if available.lower() == input_tag.strip().lower():
            return available
    
    # Then try fuzzy match (normalized spaces)
    for available in available_tags:
        available_normalized = available.lower().replace('-', ' ').replace('_', ' ')
        if available_normalized == input_normalized:
            return available
    
    # Partial match as last resort
    for available in available_tags:
        available_normalized = available.lower().replace('-', ' ').replace('_', ' ')
        if input_normalized in available_normalized or available_normalized in input_normalized:
            return available
    
    return None

def calculate_tag_score_and_reasoning(
    tag_name: str, 
    dataset: Dict, 
    similar_datasets: List[Dict],
    metadata: DatasetMetadataAnalysis,
    existing_tags: List[ExistingTag]
) -> tuple:
    """
    Calculate confidence score and reasoning for a tag suggestion
    Returns: (confidence_score, reasoning, recommended_count)
    """
    score = 0.5  # Base score
    reasoning_parts = []
    recommended_count = 0
    
    # Check if tag exists in similar datasets
    similar_tag_count = sum(1 for ds in similar_datasets if ds.get('tag_name') == tag_name)
    if similar_tag_count > 0:
        score += 0.2
        recommended_count = similar_tag_count
        reasoning_parts.append(f"Found in {similar_tag_count} similar dataset(s)")
    
    # Domain relevance
    domain = dataset.get('domain_name', '').lower()
    tag_lower = tag_name.lower()
    if domain and domain in tag_lower:
        score += 0.15
        reasoning_parts.append(f"Aligns with domain: {domain}")
    
    # Platform relevance
    platform = dataset.get('platform_name', '').lower()
    if platform and platform in tag_lower:
        score += 0.1
        reasoning_parts.append(f"Specific to platform: {platform}")
    
    # Schema complexity
    if metadata.column_count > 50:
        score += 0.05
        reasoning_parts.append("Applies to complex schema")
    elif metadata.column_count > 20:
        score += 0.02
        reasoning_parts.append("Moderate schema complexity")
    
    # Data lineage detection
    if metadata.has_lineage:
        score += 0.08
        reasoning_parts.append("Dataset has lineage information")
    
    # Avoid overscoring
    score = min(score, 0.95)
    
    reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Contextually relevant based on metadata"
    
    return score, reasoning, recommended_count

async def generate_ai_tag_suggestions(
    dataset: Dict,
    metadata: DatasetMetadataAnalysis,
    existing_tags: List[ExistingTag],
    similar_datasets: List[Dict]
) -> List[SuggestedTag]:
    """Generate tag suggestions using AI semantic analysis, constrained to available tags in database"""
    if not client or not dataset:
        return []
    
    try:
        # Get all available tags from database
        available_tags = get_available_tags()  # Returns all tags in system
        available_tag_names = [tag.get('name', '').strip() for tag in available_tags if tag.get('name')]  # Keep original case
        
        if not available_tag_names:
            logger.warning("No tags available in database - cannot generate AI suggestions")
            return []
        
        logger.info(f"AI suggestions constrained to {len(available_tag_names)} available tags: {available_tag_names}")
        
        existing_tag_names = [tag.name for tag in existing_tags]
        similar_tags_in_dataset = list(set([ds.get('tag_name') for ds in similar_datasets if ds.get('tag_name')]))
        
        # Build context prompt with available tags constraint
        available_tags_str = ', '.join(available_tag_names[:50])  # Show first 50 available tags
        context = f"""
Dataset Analysis for Tag Suggestion:
- Name: {dataset.get('name')}
- Platform: {metadata.platform}
- Domain: {dataset.get('domain_name', 'Unknown')}
- Description: {dataset.get('description', 'No description')}
- Column Count: {metadata.column_count}
- Data Types: {', '.join(metadata.data_types) if metadata.data_types else 'Not analyzed'}
- Has Lineage: {metadata.has_lineage}
- Existing Tags: {', '.join(existing_tag_names) if existing_tag_names else 'None'}
- Tags in Similar Datasets: {', '.join(similar_tags_in_dataset[:10]) if similar_tags_in_dataset else 'None'}

AVAILABLE TAGS IN SYSTEM:
{available_tags_str}

Based on this dataset analysis, select 3-5 of the MOST RELEVANT tags from the available tags list above.
IMPORTANT: Only suggest tags that are in the available list. Do not invent new tags.
For each selected tag, provide:
1. Tag name (must be from available list)
2. Confidence level (HIGH/MEDIUM/LOW)
3. Brief reason why this tag fits this dataset

Format as JSON array with keys: name, confidence, reason
"""
        
        response = await client.chat.completions.create(
            model=AZURE_CONFIG["azure_deployment"],
            messages=[{"role": "user", "content": context}],
            temperature=0.6,
            max_tokens=500
        )
        
        response_text = response.choices[0].message.content
        
        # Parse AI response - try JSON extraction
        suggestions = []
        try:
            # Try to find JSON array in response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                tags_data = json.loads(json_str)
                
                for tag_data in tags_data:
                    if isinstance(tag_data, dict):
                        ai_suggested_name = tag_data.get('name', '').strip()
                        confidence_text = tag_data.get('confidence', 'medium').upper()
                        confidence_map = {'HIGH': 0.85, 'MEDIUM': 0.65, 'LOW': 0.45}
                        confidence = confidence_map.get(confidence_text, 0.65)
                        reasoning = tag_data.get('reason', 'AI recommended based on dataset characteristics')
                        
                        # Try to find matching tag in database (with fuzzy matching)
                        matched_tag = find_matching_tag(ai_suggested_name, available_tag_names)
                        
                        existing_tag_names_lower = [tag.name.lower() for tag in existing_tags]
                        
                        # IMPORTANT: Only include tags that exist in the database
                        if matched_tag and ai_suggested_name.lower() not in existing_tag_names_lower and len(matched_tag) >= 2:
                            score, db_reasoning, rec_count = calculate_tag_score_and_reasoning(
                                matched_tag, dataset, similar_datasets, metadata, existing_tags
                            )
                            # Combine AI score with database-derived score
                            final_score = (confidence * 0.6) + (score * 0.4)
                            
                            suggestions.append(SuggestedTag(
                                name=matched_tag,  # Use matched database tag name
                                confidence_score=min(final_score, 0.95),
                                reasoning=f"{reasoning}; {db_reasoning}",
                                category="ai_recommended",
                                similar_tags=similar_tags_in_dataset[:5],
                                recommended_count=rec_count
                            ))
                            logger.info(f"Matched AI suggestion '{ai_suggested_name}' → '{matched_tag}'")
                        elif not matched_tag:
                            logger.debug(f"AI suggested tag '{ai_suggested_name}' not found in database (tried fuzzy match), filtering out")
        except json.JSONDecodeError:
            logger.warning("Could not parse AI response as JSON")
        
        # Sort by confidence score
        suggestions.sort(key=lambda x: x.confidence_score, reverse=True)
        return suggestions[:6]  # Return top 6
        
    except Exception as e:
        logger.error(f"Error generating AI suggestions: {e}")
        return []

async def generate_database_tag_suggestions(
    dataset: Dict,
    metadata: DatasetMetadataAnalysis,
    similar_datasets: List[Dict],
    existing_tags: List[ExistingTag]
) -> List[SuggestedTag]:
    """Generate tag suggestions based on database patterns and similar datasets"""
    suggestions = {}
    existing_tag_names = [tag.name for tag in existing_tags]
    
    # Get available tags from database to validate suggestions
    available_tags = get_available_tags()
    available_tag_names = [tag.get('name', '') for tag in available_tags]
    
    # Extract tags from similar datasets (only those in datahub_tags)
    for similar_ds in similar_datasets:
        tag_name = similar_ds.get('tag_name', '').strip()
        if tag_name and tag_name not in existing_tag_names and tag_name in available_tag_names and len(tag_name) >= 2:
            if tag_name not in suggestions:
                score, reasoning, rec_count = calculate_tag_score_and_reasoning(
                    tag_name, dataset, similar_datasets, metadata, existing_tags
                )
                suggestions[tag_name] = SuggestedTag(
                    name=tag_name,
                    confidence_score=score,
                    reasoning=reasoning,
                    category="pattern_based",
                    similar_tags=list(set([ds.get('tag_name') for ds in similar_datasets if ds.get('tag_name') != tag_name]))[:5],
                    recommended_count=rec_count
                )
    
    # Sort by confidence and return top 4
    sorted_suggestions = sorted(suggestions.values(), key=lambda x: x.confidence_score, reverse=True)
    return sorted_suggestions[:4]

# ============================================================================
# ADVANCED CHATBOT FUNCTIONS
# ============================================================================

def get_datasets_without_tags() -> List[Dict]:
    """Get datasets that don't have any tags assigned"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT id, urn, name, platform_name, description 
                FROM datahub_datasets 
                WHERE tag_urn IS NULL OR tag_urn = ''
                ORDER BY updated_at DESC
                LIMIT 20
            """)
            results = cursor.fetchall()
            return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error fetching untagged datasets: {e}")
        return []

def get_available_tags() -> List[Dict]:
    """Get all available tags for recommendations"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT DISTINCT urn, name, description
                FROM datahub_tags
                WHERE urn IS NOT NULL
                ORDER BY name
                LIMIT 50
            """)
            results = cursor.fetchall()
            return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error fetching tags: {e}")
        return []

def get_dataset_statistics() -> Dict:
    """Get statistics about datasets for quantitative answers"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Datasets by platform
            cursor.execute("""
                SELECT platform_name, COUNT(*) as count 
                FROM datahub_datasets 
                GROUP BY platform_name
            """)
            platform_stats = {row['platform_name']: row['count'] for row in cursor.fetchall()}
            
            # Datasets with tags vs without
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN tag_urn IS NOT NULL AND tag_urn != '' THEN 1 ELSE 0 END) as tagged,
                    SUM(CASE WHEN tag_urn IS NULL OR tag_urn = '' THEN 1 ELSE 0 END) as untagged
                FROM datahub_datasets
            """)
            tag_stats = dict(cursor.fetchone() or {})
        
            # Datasets by domain
            cursor.execute("""
                SELECT domain_name, COUNT(*) as count 
                FROM datahub_datasets 
                WHERE domain_name IS NOT NULL AND domain_name != ''
                GROUP BY domain_name
            """)
            domain_stats = {row['domain_name']: row['count'] for row in cursor.fetchall()}
            
            return {
                "platform_stats": platform_stats,
                "tag_stats": tag_stats,
                "domain_stats": domain_stats
            }
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        return {}

def get_datahub_feature_info(feature: str) -> str:
    """Get information about DataHub features from knowledge base"""
    feature = feature.lower()
    for key, info in DATAHUB_KNOWLEDGE.items():
        if key in feature or feature in key:
            features_str = ", ".join(info.get("features", []))
            return f"""
**{key.upper()}**
{info.get('description', '')}

Key Features:
- {features_str}

Benefits:
{info.get('benefits', '')}
"""
    return None

async def classify_question_enhanced(question: str) -> Dict[str, str]:
    """Enhanced classification: sql, descriptive, recommendation, or datahub-feature"""
    if not client:
        return {"type": "descriptive", "reason": "No Azure client"}
    
    classification_prompt = f"""Classify this question into ONE category:

1. "sql" - Questions needing data queries (e.g., "show all datasets", "list postgres datasets", "how many datasets", "find datasets with tag X")
2. "recommendation" - Questions asking for suggestions (e.g., "suggest tags for", "recommend domains", "what tags should", "suggest owners")
3. "datahub_feature" - Questions about DataHub features/concepts (e.g., "what is lineage", "how does glossary work", "explain tags")
4. "descriptive" - General questions about data/metadata (e.g., "what datasets exist", "tell me about snowflake")

Question: {question}

Respond with ONLY the category name, nothing else."""

    response = await client.chat.completions.create(
        model=AZURE_CONFIG["azure_deployment"],
        messages=[{"role": "user", "content": classification_prompt}],
        temperature=0,
        max_tokens=20
    )
    
    classification = response.choices[0].message.content.strip().lower()
    for valid_type in ["sql", "recommendation", "datahub_feature", "descriptive"]:
        if valid_type in classification:
            return {"type": valid_type, "reason": "Classified by Azure"}
    return {"type": "descriptive", "reason": "Default fallback"}

async def generate_recommendation(question: str) -> str:
    """Generate recommendations based on database data and domain knowledge"""
    if not client:
        return "Please configure Azure OpenAI credentials"
    
    # Get context from database
    untagged = get_datasets_without_tags()
    all_tags = get_available_tags()
    
    context = f"""
Available Tags in System:
{json.dumps([{'name': t.get('tag_name'), 'description': t.get('tag_description')} for t in all_tags[:10]], indent=2)}

Datasets Without Tags (Need Recommendations):
{json.dumps([{'name': d.get('name'), 'platform': d.get('platform_name')} for d in untagged[:5]], indent=2)}
"""
    
    prompt = f"""You are a DataHub expert recommending tags and metadata for datasets.

{context}

User Question: {question}

Provide specific, actionable recommendations based on:
1. Dataset names and platforms
2. Available tags in the system
3. DataHub best practices

Be concise and practical."""

    response = await client.chat.completions.create(
        model=AZURE_CONFIG["azure_deployment"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content

async def generate_feature_explanation(feature: str) -> str:
    """Generate detailed explanation of DataHub features"""
    if not client:
        info = get_datahub_feature_info(feature)
        return info if info else f"Feature '{feature}' information not available without Azure client"
    
    info = get_datahub_feature_info(feature)
    context = info if info else f"Feature: {feature}"
    
    prompt = f"""You are a DataHub expert. Explain this feature in a way that's:
- Accurate to the DataHub documentation
- Easy for non-technical users to understand
- Includes practical examples

Feature Information:
{context}

Original User Question implied they wanted to learn about: {feature}

Provide a comprehensive but concise explanation."""

    response = await client.chat.completions.create(
        model=AZURE_CONFIG["azure_deployment"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=600
    )
    
    return response.choices[0].message.content

async def classify_question(question: str) -> str:

    """Determine if question needs SQL query or descriptive answer"""
    if not client:
        return "descriptive"
    
    classification_prompt = f"""Classify this question as either "sql" or "descriptive":

SQL questions: Questions that need to query database data (e.g., "show all datasets", "how many users", "list domains", "find datasets with tag X")
Descriptive questions: Questions about concepts, explanations, how-to guides (e.g., "what is DataHub?", "how does lineage work?", "explain metadata management")

Question: {question}

Respond with only one word: "sql" or "descriptive"."""

    response = await client.chat.completions.create(
        model=AZURE_CONFIG["azure_deployment"],
        messages=[{"role": "user", "content": classification_prompt}],
        temperature=0,
        max_tokens=10
    )
    
    classification = response.choices[0].message.content.strip().lower()
    return "sql" if "sql" in classification else "descriptive"

async def generate_sql_query(question: str, schema_info: List[Dict]) -> str:
    """Generate PostgreSQL query from natural language"""
    if not client:
        raise ValueError("Azure client not configured")
    
    schema_text = ""
    for table in schema_info:
        columns_text = ", ".join([f"{col['name']} ({col['type']})" for col in table['columns']])
        schema_text += f"\nTable: {table['table']}\nColumns: {columns_text}\n"
        
        if table['sample_data']:
            schema_text += f"Sample data: {json.dumps(table['sample_data'][:2], default=str)}\n"
    
    system_prompt = f"""You are a PostgreSQL expert for a DataHub metadata database.

Database Schema:
{schema_text}

Generate a PostgreSQL query to answer the user's question.
- Use proper JOINs when relating tables
- Limit results to 100 rows unless specified
- Return ONLY the SQL query, no explanation or markdown"""

    response = await client.chat.completions.create(
        model=AZURE_CONFIG["azure_deployment"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        temperature=0.1,
        max_tokens=600
    )
    
    sql_query = response.choices[0].message.content.strip()
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
    
    return sql_query

async def generate_sql_answer(question: str, sql_query: str, data: List[Dict], 
                              conversation_history: List[Message]) -> str:
    """Convert SQL results into natural language answer"""
    if not client:
        return json.dumps(data[:10], indent=2, default=str)
    
    data_summary = json.dumps(data[:10], indent=2, default=str) if data else "No data returned"
    row_count = len(data)
    
    messages = [
        {
            "role": "system", 
            "content": """You are a concise DataHub assistant. Provide brief, structured answers."""
        }
    ]
    
    for msg in conversation_history[-4:]:
        messages.append({"role": msg.role, "content": msg.content})
    
    user_message = f"""Q: {question}
Results: {row_count} rows
Data: {data_summary}"""

    messages.append({"role": "user", "content": user_message})
    
    response = await client.chat.completions.create(
        model=AZURE_CONFIG["azure_deployment"],
        messages=messages,
        temperature=0.7,
        max_tokens=300
    )
    
    return response.choices[0].message.content

async def generate_descriptive_answer(question: str, conversation_history: List[Message]) -> str:
    """Answer descriptive/explanatory questions about DataHub"""
    if not client:
        return "Please configure Azure OpenAI credentials"
    
    messages = [
        {
            "role": "system",
            "content": """You are a professional DataHub consultant. Provide expert-level responses."""
        }
    ]
    
    for msg in conversation_history[-4:]:
        messages.append({"role": msg.role, "content": msg.content})
    
    messages.append({"role": "user", "content": question})
    
    response = await client.chat.completions.create(
        model=AZURE_CONFIG["azure_deployment"],
        messages=messages,
        temperature=0.7,
        max_tokens=250
    )
    
    return response.choices[0].message.content

# ============================================================================
# CHAT HISTORY MANAGEMENT
# ============================================================================
RESULTS_DIR = Path("results")
CHAT_HISTORY_FILE = RESULTS_DIR / "chat.json"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

if not CHAT_HISTORY_FILE.exists():
    with open(CHAT_HISTORY_FILE, 'w') as f:
        json.dump([], f, indent=2)

def save_chat_to_history(question: str, answer: str, query_type: str, 
                         sql_query: Optional[str] = None, session_id: Optional[str] = None):
    """Save question and answer to chat history file"""
    try:
        with open(CHAT_HISTORY_FILE, 'r') as f:
            history = json.load(f)
        
        entry = {
            "question": question,
            "answer": answer,
            "query_type": query_type,
            "sql_query": sql_query,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id
        }
        
        history.append(entry)
        
        with open(CHAT_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved chat entry to {CHAT_HISTORY_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving chat history: {str(e)}")
        return False

def load_chat_history() -> List[Dict]:
    """Load all chat history"""
    try:
        with open(CHAT_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading chat history: {str(e)}")
        return []

def clear_chat_history():
    """Clear all chat history"""
    try:
        with open(CHAT_HISTORY_FILE, 'w') as f:
            json.dump([], f, indent=2)
        logger.info("Chat history cleared")
        return True
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")
        return False

# ============================================================================
# LIFESPAN AND STARTUP/SHUTDOWN
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, cleanup on shutdown"""
    global pg_pool, gql_client
    
    # Startup
    logger.info("Starting Unified DataHub API...")
    pg_pool = await get_pg_pool()
    
    async with pg_pool.acquire() as conn:
        await init_schema(conn)
    
    transport = AIOHTTPTransport(url=DATAHUB_GRAPHQL_URL)
    gql_client = Client(transport=transport)
    logger.info("🚀 Unified API Ready on Port 8000!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await pg_pool.close()

app.router.lifespan_context = lifespan

# ============================================================================
# API ENDPOINTS - HEALTH & INFO
# ============================================================================
@app.get("/", tags=["health"])
async def root():
    """Root endpoint - API info"""
    return {
        "service": "Unified DataHub API",
        "version": "3.0.0",
        "status": "running",
        "port": 8000,
        "features": ["Dataset Sync", "Semantic Sync", "Chatbot", "Data Cards"],
        "endpoints": {
            "health": "/health",
            "stats": "/stats",
            "chat": "/chat",
            "datacard": "/datacard/{urn}",
            "sync_full": "/sync/full",
            "sync_datasets": "/sync/datasets"
        }
    }

@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint"""
    try:
        async with pg_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# ============================================================================
# API ENDPOINTS - SEMANTIC SYNC (from semantic-sync)
# ============================================================================
@app.post("/init-schema", tags=["semantic-sync"])
async def run_init_schema():
    """Initialize database schema"""
    async with pg_pool.acquire() as conn:
        await init_schema(conn)
    return {"status": "schema_created"}

@app.post("/sync/full", response_model=SyncStats, tags=["semantic-sync"])
async def sync_full():
    """Full sync of all DataHub entities"""
    stats = SyncStats()
    
    async with pg_pool.acquire() as conn:
        tables = ['datahub_dataset_properties', 'datahub_datasets', 
                 'datahub_domains', 'datahub_tags', 'datahub_glossary', 'datahub_owners']
        for table in tables:
            await safe_truncate(conn, table)
        
        stats.datasets = await sync_datasets(conn)
        stats.domains = await sync_domains(conn)
        stats.tags = await sync_tags(conn)
        stats.glossary_terms = await sync_glossary(conn)
        stats.owners = await sync_owners(conn)
        stats.total = stats.datasets + stats.domains + stats.tags + stats.glossary_terms + stats.owners
        
    logger.info(f"FULL SYNC COMPLETE: {stats}")
    return stats

@app.post("/sync/datasets", response_model=Dict[str, int], tags=["semantic-sync"])
async def sync_datasets_only():
    """Sync only datasets"""
    async with pg_pool.acquire() as conn:
        await safe_truncate(conn, 'datahub_datasets')
        await safe_truncate(conn, 'datahub_dataset_properties')
        count = await sync_datasets(conn)
    return {"datasets": count}

@app.get("/stats", tags=["semantic-sync"])
async def stats():
    """Get statistics on synced entities"""
    async with pg_pool.acquire() as conn:
        tables = {
            'datasets': 'COUNT(*) FROM datahub_datasets',
            'domains': 'COUNT(*) FROM datahub_domains',
            'tags': 'COUNT(*) FROM datahub_tags',
            'glossary': 'COUNT(*) FROM datahub_glossary',
            'owners': 'COUNT(*) FROM datahub_owners'
        }
        result = {}
        for k, v in tables.items():
            try:
                count = await conn.fetchval(f"SELECT {v}")
                result[k] = int(count) if count else 0
            except:
                result[k] = 0
        return {"counts": result}

# ============================================================================
# API ENDPOINTS - DATASET SYNC (from dataset-sync)
# ============================================================================
@app.post("/sync/blocking", response_model=SyncResponse, tags=["dataset-sync"])
async def sync_blocking():
    """Sync datasets in blocking mode using UPSERT to datahub_dataset_all"""
    try:
        logger.info("Starting BLOCKING sync...")
        create_datasets_table()
        
        # Fetch datasets from DataHub GraphQL
        response = requests.post(DATAHUB_GRAPHQL_URL, json={'query': GRAPHQL_QUERY}, 
                               headers={'Content-Type': 'application/json'}, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        datasets = [r.get('entity', {}) for r in data.get('data', {}).get('search', {}).get('searchResults', [])
                   if 'dataset' in r.get('entity', {}).get('urn', '').lower()]
        
        logger.info(f"📦 Processing {len(datasets)} datasets")
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                total_inserted = total_updated = 0
                for dataset in datasets:
                    flattened = flatten_dataset_data(dataset)
                    cursor.execute("SELECT COUNT(*) as exists FROM datahub_dataset_all WHERE urn = %s", 
                                 (flattened['urn'],))
                    exists = cursor.fetchone()['exists']
                    cursor.execute(UPSERT_SQL, flattened)
                    if exists == 0: total_inserted += 1
                    else: total_updated += 1
                conn.commit()
        
        logger.info(f"✅ Sync complete: {total_inserted} new, {total_updated} updated")
        
        return SyncResponse(
            status="completed",
            total_processed=len(datasets),
            message=f"Synced {len(datasets)} datasets ({total_inserted} new, {total_updated} updated)"
        )
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sync/status", tags=["dataset-sync"])
async def sync_status():
    """Get sync status from datahub_dataset_all"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count, MAX(updated_at) as last_sync,
                           AVG(field_count) as avg_fields
                    FROM datahub_dataset_all
                """)
                result = cursor.fetchone()
                
                if result:
                    return {
                        "total_datasets": result['count'] if result['count'] else 0,
                        "last_sync": str(result['last_sync']) if result['last_sync'] else "Never",
                        "avg_field_count": result['avg_fields'] if result['avg_fields'] else 0,
                        "status": "ready"
                    }
                else:
                    return {
                        "total_datasets": 0,
                        "last_sync": "Never",
                        "avg_field_count": 0,
                        "status": "ready"
                    }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-datacard/{urn}", response_model=DataCardResponse, tags=["datacard"])
async def generate_datacard(urn: str, request: GenerateRequest):
    """Generate data card for a dataset"""
    if not client:
        raise HTTPException(status_code=503, detail="Azure OpenAI not configured")
    
    try:
        async with pg_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, urn, name FROM datahub_dataset_all WHERE urn = $1
            """, urn)
            
            if not row:
                raise HTTPException(status_code=404, detail="Dataset not found")
        
        dataset = dict(row)
        
        prompt = f"""Generate a professional data card for dataset: {dataset['name']}
        
Please provide a concise data card with:
1. Dataset Overview
2. Key Fields
3. Data Quality
4. Business Value"""

        response = await client.chat.completions.create(
            model=AZURE_CONFIG["azure_deployment"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=request.max_tokens,
            temperature=0.7
        )
        
        data_card = response.choices[0].message.content
        
        async with pg_pool.acquire() as conn:
            await conn.execute("""
                UPDATE datahub_dataset_all 
                SET data_card = $1, updated_at = CURRENT_TIMESTAMP 
                WHERE urn = $2
            """, data_card, urn)
        
        logger.info(f"Generated data card for {urn}")
        
        return DataCardResponse(
            dataset_id=dataset['id'],
            urn=dataset['urn'],
            name=dataset['name'],
            data_card=data_card,
            generated_at=datetime.now(),
            status="generated"
        )
        
    except Exception as e:
        logger.error(f"Data card generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.get("/datacard/{urn}", tags=["datacard"])
async def get_datacard(urn: str):
    """Get existing data card"""
    try:
        async with pg_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, urn, name, data_card, updated_at
                FROM datahub_dataset_all WHERE urn = $1 AND data_card IS NOT NULL
            """, urn)
            
            if not row:
                raise HTTPException(status_code=404, detail="Data card not found")
        
        return {
            "dataset_id": row['id'],
            "urn": row['urn'],
            "name": row['name'],
            "data_card": row['data_card'],
            "generated_at": row['updated_at']
        }
    except Exception as e:
        logger.error(f"Get datacard failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# API ENDPOINTS - CHATBOT (from dataset-sync chat)
# ============================================================================
@app.get("/schema", tags=["chat"])
async def get_schema():
    """Get database schema information"""
    try:
        schema = get_database_schema()
        return {
            "schema": schema,
            "table_count": len(schema)
        }
    except Exception as e:
        logger.error(f"Schema fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching schema: {str(e)}")

@app.get("/history", tags=["chat"])
async def get_history():
    """Get all chat history"""
    try:
        history = load_chat_history()
        return {
            "history": history,
            "total_entries": len(history),
            "file_path": str(CHAT_HISTORY_FILE)
        }
    except Exception as e:
        logger.error(f"Error fetching history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")

@app.delete("/history", tags=["chat"])
async def delete_history():
    """Clear all chat history"""
    try:
        success = clear_chat_history()
        if success:
            return {
                "message": "Chat history cleared successfully",
                "file_path": str(CHAT_HISTORY_FILE)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to clear chat history")
    except Exception as e:
        logger.error(f"Error clearing history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")

@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest):
    """Enhanced chat endpoint - handles SQL, descriptive, recommendations, and DataHub features"""
    try:
        logger.info(f"Received question: {request.question}")
        
        # Enhanced classification
        classification = await classify_question_enhanced(request.question)
        query_type = classification["type"]
        logger.info(f"Question classified as: {query_type}")
        
        if query_type == "sql":
            # SQL Query Path
            schema_info = get_database_schema()
            sql_query = await generate_sql_query(request.question, schema_info)
            logger.info(f"Generated SQL: {sql_query}")
            
            data = execute_sql_query(sql_query)
            logger.info(f"Query returned {len(data)} rows")
            
            answer = await generate_sql_answer(
                request.question,
                sql_query,
                data,
                request.conversation_history
            )
            
            save_chat_to_history(
                question=request.question,
                answer=answer,
                query_type="sql",
                sql_query=sql_query
            )
            
            return ChatResponse(
                answer=answer,
                query_type="sql",
                sql_query=sql_query,
                data=data[:50],
                timestamp=datetime.utcnow().isoformat()
            )
        
        elif query_type == "recommendation":
            # Recommendation Path (tags, owners, domains, etc.)
            logger.info("Generating recommendations based on database...")
            answer = await generate_recommendation(request.question)
            
            save_chat_to_history(
                question=request.question,
                answer=answer,
                query_type="recommendation"
            )
            
            return ChatResponse(
                answer=answer,
                query_type="recommendation",
                timestamp=datetime.utcnow().isoformat()
            )
        
        elif query_type == "datahub_feature":
            # DataHub Feature Explanation Path
            logger.info("Generating DataHub feature explanation...")
            answer = await generate_feature_explanation(request.question)
            
            save_chat_to_history(
                question=request.question,
                answer=answer,
                query_type="datahub_feature"
            )
            
            return ChatResponse(
                answer=answer,
                query_type="datahub_feature",
                timestamp=datetime.utcnow().isoformat()
            )
        
        else:
            # Descriptive Path (default)
            answer = await generate_descriptive_answer(
                request.question,
                request.conversation_history
            )
            
            save_chat_to_history(
                question=request.question,
                answer=answer,
                query_type="descriptive"
            )
            
            return ChatResponse(
                answer=answer,
                query_type="descriptive",
                timestamp=datetime.utcnow().isoformat()
            )
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.post("/tags/suggest", response_model=TagSuggestionResponse, tags=["tags"])
async def suggest_tags_for_dataset(dataset_urn: str) -> TagSuggestionResponse:
    """
    Generate intelligent tag suggestions for a dataset based on comprehensive analysis.
    
    This endpoint performs the following operations:
    1. Validates the dataset URN format
    2. Verifies the dataset exists in the system
    3. Retrieves and analyzes existing tags to identify coverage gaps
    4. Analyzes dataset metadata (schema, columns, platform, domain, lineage)
    5. Finds similar datasets to identify tagging patterns
    6. Generates tag suggestions using ML-based semantic analysis
    7. Scores suggestions with confidence levels and detailed reasoning
    8. Returns structured response with complete analysis
    
    Args:
        dataset_urn: URN in format urn:li:dataset:(urn:li:dataPlatform:platform,name,environment)
    
    Returns:
        TagSuggestionResponse with detailed tag recommendations and metadata analysis
    
    Raises:
        400: Invalid URN format
        404: Dataset not found
        500: Internal processing error
    """
    start_time = datetime.utcnow()
    
    try:
        # Step 1: Validate URN format
        is_valid, validation_error = validate_dataset_urn(dataset_urn)
        if not is_valid:
            logger.warning(f"Invalid URN format: {dataset_urn} - {validation_error}")
            raise HTTPException(status_code=400, detail=validation_error)
        
        # Step 2: Verify dataset exists
        dataset = get_dataset_by_urn(dataset_urn)
        if not dataset:
            logger.warning(f"Dataset not found: {dataset_urn}")
            raise HTTPException(status_code=404, detail=f"Dataset '{dataset_urn}' not found in system")
        
        logger.info(f"Processing tag suggestions for dataset: {dataset.get('name')}")
        
        # Step 3: Retrieve existing tags and analyze coverage
        existing_tags = get_existing_tags_for_dataset(dataset_urn)
        existing_tag_count = len(existing_tags)
        
        # Step 4: Analyze dataset metadata
        metadata_analysis = extract_metadata_analysis(dataset)
        
        # Step 5: Find similar datasets for pattern analysis
        similar_datasets = find_similar_datasets(dataset, limit=10)
        
        # Step 6: Generate suggestions from both AI and database patterns
        ai_suggestions = []
        db_suggestions = []
        
        if client:
            try:
                ai_suggestions = await generate_ai_tag_suggestions(
                    dataset, metadata_analysis, existing_tags, similar_datasets
                )
                logger.info(f"Generated {len(ai_suggestions)} AI-based suggestions")
            except Exception as e:
                logger.error(f"AI suggestion generation failed: {e}")
        
        # Always generate database-based suggestions
        db_suggestions = await generate_database_tag_suggestions(
            dataset, metadata_analysis, similar_datasets, existing_tags
        )
        logger.info(f"Generated {len(db_suggestions)} database-based suggestions")
        
        # Step 7: Get all available tags for final validation
        all_available_tags = get_available_tags()
        available_tag_names = [tag.get('name', '') for tag in all_available_tags]
        
        # Step 8: Merge and deduplicate suggestions
        all_suggestions = {}
        
        for tag in ai_suggestions:
            if tag.name not in all_suggestions:
                all_suggestions[tag.name] = tag
        
        for tag in db_suggestions:
            if tag.name not in all_suggestions:
                all_suggestions[tag.name] = tag
        
        # Filter to only include tags that exist in datahub_tags
        validated_suggestions = {
            name: tag for name, tag in all_suggestions.items() 
            if name in available_tag_names
        }
        
        if not validated_suggestions:
            logger.warning(f"No valid suggestions found for {dataset.get('name')}")
        
        # Sort by confidence and take top 8
        suggested_tags = sorted(validated_suggestions.values(), key=lambda x: x.confidence_score, reverse=True)[:8]
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        response = TagSuggestionResponse(
            status="success",
            dataset_urn=dataset_urn,
            dataset_name=dataset.get('name', 'Unknown'),
            platform=metadata_analysis.platform,
            existing_tags=existing_tags,
            existing_tag_count=existing_tag_count,
            metadata_analysis=metadata_analysis,
            suggested_tags=suggested_tags,
            suggestion_count=len(suggested_tags),
            processing_metadata={
                "processing_time_seconds": round(processing_time, 2),
                "similar_datasets_analyzed": len(similar_datasets),
                "ai_suggestions_generated": len(ai_suggestions),
                "database_patterns_found": len(db_suggestions),
                "analysis_timestamp": start_time.isoformat()
            },
            timestamp=datetime.utcnow().isoformat(),
            error=None
        )
        
        logger.info(f"Successfully generated {len(suggested_tags)} tag suggestions for {dataset.get('name')} in {processing_time:.2f}s")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tag suggestion error: {str(e)}", exc_info=True)
        error_response = TagSuggestionResponse(
            status="error",
            dataset_urn=dataset_urn,
            dataset_name="Unknown",
            platform="unknown",
            existing_tags=[],
            existing_tag_count=0,
            metadata_analysis=None,
            suggested_tags=[],
            suggestion_count=0,
            processing_metadata={
                "error_type": type(e).__name__,
                "error_timestamp": datetime.utcnow().isoformat()
            },
            timestamp=datetime.utcnow().isoformat(),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=error_response.dict())

@app.get("/chat/suggestions/tags", tags=["chat"])
async def get_tag_suggestions():
    """Get suggestions for datasets that need tags"""
    try:
        untagged = get_datasets_without_tags()
        all_tags = get_available_tags()
        
        if not untagged:
            return {
                "status": "success",
                "message": "All datasets have tags",
                "untagged_datasets": [],
                "available_tags": []
            }
        
        recommendations = []
        for dataset in untagged:
            if client:
                prompt = f"""Given this dataset:
Name: {dataset.get('name')}
Platform: {dataset.get('platform_name')}
Description: {dataset.get('description', 'N/A')}

Available tags: {json.dumps([t.get('tag_name') for t in all_tags[:15]])}

Suggest 2-3 most relevant tags for this dataset. Be specific and practical."""
                
                response = await client.chat.completions.create(
                    model=AZURE_CONFIG["azure_deployment"],
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=100
                )
                suggested_tags = response.choices[0].message.content
            else:
                suggested_tags = "Azure client not configured. Available tags: " + ", ".join([t.get('tag_name') for t in all_tags[:5]])
            
            recommendations.append({
                "dataset_id": dataset.get('id'),
                "dataset_name": dataset.get('name'),
                "platform": dataset.get('platform_name'),
                "suggested_tags": suggested_tags
            })
        
        return {
            "status": "success",
            "untagged_count": len(untagged),
            "recommendations": recommendations,
            "available_tags": [{"name": t.get('tag_name'), "description": t.get('tag_description')} for t in all_tags[:20]]
        }
    except Exception as e:
        logger.error(f"Error generating tag suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/statistics", tags=["chat"])
async def get_chat_statistics():
    """Get statistics useful for chatbot responses"""
    try:
        stats = get_dataset_statistics()
        return {
            "status": "success",
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/datahub-features", tags=["chat"])
async def get_datahub_features():
    """Get list of DataHub features with descriptions"""
    try:
        features = {}
        for feature_name, feature_info in DATAHUB_KNOWLEDGE.items():
            features[feature_name] = {
                "description": feature_info.get("description"),
                "features": feature_info.get("features"),
                "benefits": feature_info.get("benefits")
            }
        return {
            "status": "success",
            "features": features,
            "count": len(features)
        }
    except Exception as e:
        logger.error(f"Error fetching features: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    import time
    logger.info(" Waiting for database to be ready...")
    time.sleep(3)  # Give docker network time to resolve
    logger.info(" Initializing database tables...")
    create_datasets_table()
    logger.info("Starting Unified API Server on 0.0.0.0:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
