"""
FastAPI application factory and configuration
"""
from fastapi import FastAPI
from app.config import API_TITLE, API_VERSION, OPENAPI_TAGS
from app.api import domains_router, tags_router, dashboard_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        openapi_tags=OPENAPI_TAGS
    )
    
    # Register routers
    app.include_router(domains_router)
    app.include_router(tags_router)
    app.include_router(dashboard_router)
    
    return app
