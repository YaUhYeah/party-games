"""Routes module."""
import os
import random
import base64
from typing import Dict, Optional

import qrcode
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from server.database import get_db, User, GameScore, Achievement
from server.models.game_room import GameRoom
from server.utils.network import get_local_ip

# Get the absolute path to the server directory
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(SERVER_DIR, "static")
QR_DIR = os.path.join(STATIC_DIR, "qr")

# Create necessary directories
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)

def register_routes(app: FastAPI, templates: Jinja2Templates, rooms: Dict[str, GameRoom]):
    """Register all routes with the application."""
    
    @app.post("/api/users")
    async def create_user(username: str, profile_picture: Optional[str] = None, db: Session = Depends(get_db)):
        db_user = db.query(User).filter(User.username == username).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")

        user = User(username=username)
        if profile_picture:
            try:
                image_data = base64.b64decode(profile_picture.split(',')[1])
                user.profile_picture = image_data
            except:
                raise HTTPException(status_code=400, detail="Invalid profile picture format")

        db.add(user)
        db.commit()
        db.refresh(user)
        return {"id": user.id, "username": user.username}

    @app.get("/api/users/{username}")
    async def get_user(username: str, db: Session = Depends(get_db)):
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        profile_picture = None
        if user.profile_picture:
            profile_picture = base64.b64encode(user.profile_picture).decode('utf-8')

        return {
            "id": user.id,
            "username": user.username,
            "profile_picture": profile_picture,
            "games_played": user.games_played,
            "total_score": user.total_score,
            "highest_score": user.highest_score
        }

    @app.get("/api/leaderboard")
    async def get_leaderboard(game_type: Optional[str] = None, db: Session = Depends(get_db)):
        if game_type:
            scores = db.query(GameScore).filter(GameScore.game_type == game_type) \
                .order_by(GameScore.score.desc()).limit(10).all()
            return [{
                "username": db.query(User).filter(User.id == score.user_id).first().username,
                "score": score.score,
                "played_at": score.played_at
            } for score in scores]
        else:
            users = db.query(User).order_by(User.highest_score.desc()).limit(10).all()
            return [{
                "username": user.username,
                "highest_score": user.highest_score,
                "games_played": user.games_played
            } for user in users]

    @app.get("/api/achievements/{username}")
    async def get_achievements(username: str, db: Session = Depends(get_db)):
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        achievements = db.query(Achievement).filter(Achievement.user_id == user.id).all()
        return [{
            "name": achievement.name,
            "description": achievement.description,
            "unlocked_at": achievement.unlocked_at
        } for achievement in achievements]

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return templates.TemplateResponse(
            "index.html",
            {"request": request}
        )

    @app.get("/host", response_class=HTMLResponse)
    async def host_game(request: Request):
        try:
            room_id = ''.join(random.choices('0123456789', k=6))
            rooms[room_id] = GameRoom(room_id)

            # Get local IP address
            local_ip = get_local_ip()
            host = request.headers.get('host', f"{local_ip}:8000")
            protocol = request.headers.get('x-forwarded-proto', 'http')

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            join_url = f"{protocol}://{host}/join/{room_id}"
            qr.add_data(join_url)
            qr.make(fit=True)
            qr_image = qr.make_image(fill_color="black", back_color="white")

            # Save QR code with absolute path
            qr_filename = f'qr_{room_id}.png'
            qr_path = os.path.join(QR_DIR, qr_filename)
            qr_image.save(qr_path)

            # Log paths for debugging
            print(f"QR Code saved to: {qr_path}")
            print(f"QR Code URL: /static/qr/{qr_filename}")
            print(f"Join URL: {join_url}")

            return templates.TemplateResponse(
                "host.html",
                {
                    "request": request,
                    "room_id": room_id,
                    "qr_code": f"/static/qr/{qr_filename}",
                    "join_url": join_url
                }
            )
        except Exception as e:
            print(f"Error in host_game: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/join/{room_id}", response_class=HTMLResponse)
    async def join_game(request: Request, room_id: str):
        if room_id not in rooms:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": "Room not found"}
            )
        return templates.TemplateResponse(
            "player.html",
            {"request": request, "room_id": room_id}
        )