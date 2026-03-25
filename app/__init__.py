"""
App package initialization
"""
from .core import create_app

app = create_app()

__all__ = ["app"]
