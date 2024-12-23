"""Main application module."""
from typing import Dict, Any
from server.app_factory import create_app as create_app_factory

def create_app():
    """Create and configure the application."""
    return create_app_factory()

app = create_app()
