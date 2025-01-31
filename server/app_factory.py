"""Application factory module."""
import os
from typing import Dict, Any

import socketio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from server.models.game_room import GameRoom

# Global state
rooms: Dict[str, GameRoom] = {}

def create_app():
    """Create and configure the application."""
    # Import here to avoid circular imports
    import asyncio
    from server.database import init_db, Base, engine
    from server.routes import register_routes
    from server.sockets import register_socket_events

    # Initialize database
    Base.metadata.create_all(bind=engine)
    init_db()

    # Initialize rooms dict with lock
    rooms_lock = asyncio.Lock()
    # Create FastAPI app
    app = FastAPI(
        title="Party Games Hub",
        description="A collection of fun multiplayer party games",
        version="1.0.0",
        docs_url=None,  # Disable docs in production
        redoc_url=None  # Disable redoc in production
    )

    # Initialize templates early for exception handler
    SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMPLATES_DIR = os.path.join(SERVER_DIR, "templates")
    templates = Jinja2Templates(directory=TEMPLATES_DIR)

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        print(f"Global exception handler caught: {exc}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "An unexpected error occurred. Please try again.",
                "show_refresh": True
            },
            status_code=500
        )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configure Socket.IO with enhanced settings for mobile support
    sio = socketio.AsyncServer(
        async_mode='asgi',
        cors_allowed_origins='*',
        ping_timeout=60000,  # Increased timeout for mobile networks (in ms)
        ping_interval=25000,  # Ping interval in ms
        max_http_buffer_size=1e8,  # 100MB max message size
        logger=True,
        engineio_logger=True,
        reconnection=True,
        reconnection_attempts=10,  # More retry attempts
        reconnection_delay=1000,
        reconnection_delay_max=5000,
        allow_upgrades=True,  # Allow WebSocket upgrades
        http_compression=True,  # Enable compression
        transports=['websocket', 'polling'],  # Support both WebSocket and polling
        async_handlers=True,  # Enable async handlers
        json=None  # Use default JSON serializer
    )

    # Set up static files
    STATIC_DIR = os.path.join(SERVER_DIR, "static")

    # Create necessary directories with proper permissions
    def ensure_dir(path):
        if not os.path.exists(path):
            os.makedirs(path, mode=0o777, exist_ok=True)
        os.chmod(path, 0o777)  # Ensure write permissions

    ensure_dir(STATIC_DIR)
    ensure_dir(os.path.join(STATIC_DIR, "music"))
    ensure_dir(os.path.join(STATIC_DIR, "profiles"))
    ensure_dir(os.path.join(STATIC_DIR, "qr"))

    # Mount static files
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # Print static directory structure for debugging
    print("\nStatic directory structure:")
    for root, dirs, files in os.walk(STATIC_DIR):
        level = root.replace(STATIC_DIR, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{subindent}{f}")

    # Add static files to templates context
    templates.env.globals.update({
        "static_url": "/static",
        "request": None  # Will be overridden in route handlers
    })

    # Add root route
    @app.get("/")
    async def root(request: Request):
        """Serve the main page."""
        try:
            return templates.TemplateResponse("index.html", {"request": request})
        except Exception as e:
            print(f"Error serving index page: {e}")
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "An error occurred loading the page. Please try again.",
                "show_refresh": True
            })

    # Register routes and socket events
    register_routes(app, templates, rooms)
    register_socket_events(sio, rooms)

    # Create background task for room cleanup
    async def cleanup_rooms(sid, environ):
        print(f"Client connected: {sid}")
        # Don't clean up rooms during connection, only periodically
    
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(300)  # Run every 5 minutes
            print("Running periodic room cleanup")
            for room_id in list(rooms.keys()):
                room = rooms[room_id]
                if not room.host_sid or not room.players.get(room.host_sid, {}).get('connected', False):
                    active_players = sum(1 for p in room.players.values() 
                                    if p.get('connected', False))
                    if active_players == 0:
                        print(f"Removing inactive room: {room_id}")
                        del rooms[room_id]
    
    sio.on('connect', cleanup_rooms)
    
    # Start periodic cleanup task
    @app.on_event("startup")
    async def start_cleanup():
        asyncio.create_task(periodic_cleanup())

    # Mount Socket.IO app
    socket_app = socketio.ASGIApp(
        socketio_server=sio,
        other_asgi_app=app,
        socketio_path='socket.io'
    )

    # Add startup and shutdown handlers
    @app.on_event("startup")
    async def startup_event():
        print("Socket.IO server started")

    @app.on_event("shutdown")
    async def shutdown_event():
        print("Socket.IO server shutting down")

    return socket_app