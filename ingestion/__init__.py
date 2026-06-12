"""
Ingestion Module

Provides database connection, ingestion pipeline management, and metadata sink.
"""

from .core import (
    SOURCE_TEMPLATES,
    PostgresSink,
    PostgresSinkReport,
    Database,
    IngestionManager,
)

__all__ = [
    "SOURCE_TEMPLATES",
    "PostgresSink",
    "PostgresSinkReport",
    "Database",
    "IngestionManager",
]
