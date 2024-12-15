"""Application factory module."""
import os
from typing import Dict

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from server.models.game_room import GameRoom

# Global state
rooms: Dict[str, GameRoom] = {}

def create_app() -> socketio.ASGIApp:
    """Create and configure the application."""
    # Create FastAPI app
    app = FastAPI(
        title="Party Games Hub",
        description="A collection of fun multiplayer party games",
        version="1.0.0"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configure Socket.IO
    sio = socketio.AsyncServer(
        async_mode='asgi',
        cors_allowed_origins='*',
        ping_timeout=35,
        ping_interval=25,
        max_http_buffer_size=1e8,  # 100MB max message size
        logger=True,
        engineio_logger=True
    )

    # Set up static files and templates
    SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
    STATIC_DIR = os.path.join(SERVER_DIR, "static")
    TEMPLATES_DIR = os.path.join(SERVER_DIR, "templates")

    # Create necessary directories
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, "music"), exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, "profiles"), exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, "qr"), exist_ok=True)

    # Mount static files
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    templates = Jinja2Templates(directory=TEMPLATES_DIR)

    # Add static files to templates context
    templates.env.globals["static_url"] = "/static"

    # Import and register routes and socket events
    from server.routes import register_routes
    from server.sockets import register_socket_events

    register_routes(app, templates, rooms)
    register_socket_events(sio, rooms)

    # Create Socket.IO app
    socket_app = socketio.ASGIApp(
        sio,
        app,
        static_files={
            '/': {'content_type': 'text/html', 'filename': 'index.html'}
        }
    )

    return socket_app