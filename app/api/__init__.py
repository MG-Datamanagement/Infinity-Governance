"""
API package initialization - register all routers
"""
from .domains import router as domains_router
from .tags import router as tags_router
from .dashboard import router as dashboard_router

__all__ = [
    "domains_router",
    "tags_router",
    "dashboard_router",
]
