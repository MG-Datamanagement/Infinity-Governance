"""
Configuration settings for Infinity Governance API
"""
import os


# Database Configuration
PG_HOST = os.getenv("PG_HOST", "postgres_ig")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB = os.getenv("PG_DB", "semantic_search")
PG_USER = os.getenv("PG_USER", "semantic_user")
PG_PASS = os.getenv("PG_PASS", "semantic_pass")

# GraphQL Configuration
DATAHUB_GRAPHQL_URL = os.getenv("DATAHUB_GRAPHQL_URL", "http://nginx-proxy/graphql")

# Application Configuration
API_TITLE = "Infinity Governance API"
API_VERSION = "1.0.0"

# Server Configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8001

# Tags for OpenAPI documentation
OPENAPI_TAGS = [
    {
        "name": "dashboard",
        "description": "Dashboard metrics and analytics endpoints"
    },
    {
        "name": "domains",  
        "description": "Endpoints for managing Domains"
    },
    {
        "name": "tags",
        "description": "Endpoints for managing Tags"
    }
]
