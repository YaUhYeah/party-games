"""Main application module."""
from typing import Dict, Any
from server.app_factory import create_app

app = create_app()
