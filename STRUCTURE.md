"""
Infinity Governance API - Project Structure

This is a clean, modular FastAPI application with separated concerns.

## Directory Structure

```
Microservices/
├── app.py                          # Main entry point (9 lines)
├── app/                            # Application package
│   ├── __init__.py                 # App factory export
│   ├── core.py                     # FastAPI app creation & router registration
│   ├── models/                     # Data models & schemas
│   │   ├── __init__.py
│   │   └── schemas.py              # Pydantic models & Enums
│   ├── config/                     # Configuration & settings
│   │   ├── __init__.py
│   │   └── settings.py             # Environment variables & API config
│   ├── utils/                      # Utility functions
│   │   ├── __init__.py
│   │   ├── database.py             # Database pool management
│   │   └── graphql.py              # GraphQL query execution
│   └── api/                        # API routes & endpoints
│       ├── __init__.py
│       ├── domains/                # Domain management endpoints
│       │   ├── __init__.py
│       │   └── routes.py           # Domain CRUD operations
│       ├── tags/                   # Tag management endpoints
│       │   ├── __init__.py
│       │   └── routes.py           # Tag CRUD operations
│       └── dashboard/              # Dashboard & utility endpoints
│           ├── __init__.py
│           └── routes.py           # Metrics, health, recommendations
```

## Modules Overview

### app/models/schemas.py
- Pydantic models for request/response validation
- Enums for domain states and entity types
- Models: OwnerInput, CreateDomainInput, UpdateDomainInput, DomainResponse
- Models: CreateTagInput, UpdateTagInput, TagResponse

### app/config/settings.py
- Environment variables (PG_HOST, PG_PORT, PG_DB, etc.)
- GraphQL endpoint configuration
- API metadata (title, version, tags)
- Server configuration (HOST, PORT)

### app/utils/
- **database.py**: Async database pool management
  - get_db_pool(): Get or create connection pool
  - close_db_pool(): Clean shutdown
  
- **graphql.py**: GraphQL query execution
  - execute_graphql_query(): Execute queries/mutations against DataHub

### app/api/
- **domains/routes.py**: Domain endpoints
  - POST /domains/create - Create domain
  - GET /domains/list - List all domains
  - PUT /domains/{urn} - Update domain
  - DELETE /domains/{urn} - Delete domain

- **tags/routes.py**: Tag endpoints
  - POST /tags/create - Create tag
  - GET /tags/list - List all tags
  - PUT /tags/{urn} - Update tag
  - DELETE /tags/{urn} - Delete tag

- **dashboard/routes.py**: Utility endpoints
  - GET /health - Health check
  - GET /corp-users - Get corp users dropdown
  - GET /ownership-types - Get ownership types dropdown
  - GET /dashboard/entitymetrics - Entity counts
  - GET /dashboard/platforms - Dataset counts by platform
  - GET /dashboard/domain_with_counts - Domains with asset counts
  - GET /dashboard/recent - Recently viewed datasets
  - GET /dashboard/recent-assets - Raw recommendations data

## Running the Application

```bash
# Development
python app.py

# Production with Uvicorn
uvicorn app:app --host 0.0.0.0 --port 8001

# With Docker
docker-compose up
```

## Environment Variables

```
PG_HOST=postgres_ig
PG_PORT=5432
PG_DB=semantic_search
PG_USER=semantic_user
PG_PASS=semantic_pass
DATAHUB_GRAPHQL_URL=http://nginx-proxy/graphql
```

## Benefits of This Structure

**Separation of Concerns** - Models, config, utils, and routes are isolated
**Scalability** - Easy to add new features (new route files)
**Testability** - Each module can be tested independently
**Maintainability** - Clear organization by domain
**Reusability** - Utils can be imported anywhere
**Clean Code** - Main app.py is just 9 lines
"""
