import os
import socketio
import random
import json
import qrcode
import asyncio
import base64
import socket
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, HTTPException, Depends, File, UploadFile, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from sqlalchemy.orm import Session

# Game configuration
GAME_CONFIG = {
    'min_players': 3,
    'max_players': 12,
    'drawing_time': 60,  # seconds
    'guess_time': 30,    # seconds
    'trivia_time': 20,   # seconds
    'chase_time': 15,    # seconds
    'rounds_per_game': 3,
    'chase_board_size': 7,  # steps between chaser and safety
    'points': {
        'correct_guess': 100,
        'partial_guess': 50,
        'correct_trivia': 100,
        'fast_answer_bonus': 50,  # bonus for answering within 5 seconds
        'chase_win': 500,  # contestant escapes chaser
        'chase_catch': 300,  # chaser catches contestant
        'chase_step': 100,  # contestant moves one step closer to safety
    }
}

# Music configuration
MUSIC_CONFIG = {
    'lobby': {
        'file': 'static/music/lobby.mp3',
        'volume': 0.5,
        'loop': True
    },
    'drawing': {
        'file': 'static/music/drawing.mp3',
        'volume': 0.4,
        'loop': True
    },
    'trivia': {
        'file': 'static/music/trivia.mp3',
        'volume': 0.4,
        'loop': True
    },
    'correct_answer': {
        'file': 'static/music/correct.mp3',
        'volume': 0.6,
        'loop': False
    },
    'wrong_answer': {
        'file': 'static/music/wrong.mp3',
        'volume': 0.6,
        'loop': False
    }
}

# Game topics
GAME_TOPICS = {
    'animals': ['elephant', 'giraffe', 'penguin', 'kangaroo', 'octopus'],
    'food': ['pizza', 'sushi', 'hamburger', 'ice cream', 'tacos'],
    'places': ['beach', 'mountain', 'city', 'forest', 'desert'],
    'objects': ['telephone', 'bicycle', 'umbrella', 'glasses', 'camera']
}

from database import get_db, User, GameScore, Achievement

# Create FastAPI app first
fastapi_app = FastAPI(
    title="Party Games Hub",
    description="A collection of fun multiplayer party games",
    version="1.0.0"
)

# Configure CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Socket.IO with proper CORS and error handling
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    ping_timeout=35,
    ping_interval=25,
    max_http_buffer_size=1e8,  # 100MB max message size
    logger=True,
    engineio_logger=True
)

# Create Socket.IO app with FastAPI as the other_asgi_app
app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=fastapi_app
)

# Mount static files and templates
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(SERVER_DIR, "static")
TEMPLATES_DIR = os.path.join(SERVER_DIR, "templates")

# Create necessary directories if they don't exist
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "music"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "profiles"), exist_ok=True)

# Mount static files
fastapi_app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Game state
rooms = {}

class GameRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players = {}  # {sid: {'name': str, 'user_id': int, 'profile': str, 'is_host': bool}}
        self.host_sid = None  # Store the host's socket ID
        self.game_state = 'waiting'
        self.current_game = None
        self.drawings = []
        self.current_word = None
        self.round = 0
        self.total_rounds = GAME_CONFIG['rounds_per_game']
        self.scores = {}
        self.topic = None
        self.player_order = []
        self.current_player_index = 0
        self.round_start_time = None
        self.timer_task = None
        self.used_words = set()
        self.used_questions = set()
        self.current_question = None
        self.player_answers = {}
        self.round_scores = {}
        self.db = next(get_db())

        # Chase game specific attributes
        self.chaser = None  # Store the chaser's socket ID
        self.chase_category = None
        self.chase_position = 0  # Distance between chaser and contestant
        self.chase_questions = []  # List of questions for current chase
        self.chase_contestant = None  # Current contestant's socket ID
        self.chase_scores = {}

    def reset_round(self):
        self.drawings = []
        self.current_word = None
        self.player_answers = {}
        self.round_scores = {}
        self.round_start_time = datetime.now()

    def get_next_word(self):
        available_words = []
        for words in GAME_TOPICS.values():
            available_words.extend([w for w in words if w not in self.used_words])
        if not available_words:
            self.used_words.clear()
            available_words = [w for topic in GAME_TOPICS.values() for w in topic]
        word = random.choice(available_words)
        self.used_words.add(word)
        return word

    def get_next_question(self):
        available_questions = [q for q in TRIVIA_QUESTIONS if q not in self.used_questions]
        if not available_questions:
            self.used_questions.clear()
            available_questions = TRIVIA_QUESTIONS
        question = random.choice(available_questions)
        self.used_questions.add(question)
        return question

    def calculate_score(self, player_id, is_correct, answer_time=None):
        base_score = 0
        if is_correct:
            if self.current_game == 'chinese_whispers':
                base_score = GAME_CONFIG['points']['correct_guess']
            else:  # trivia
                base_score = GAME_CONFIG['points']['correct_trivia']
                if answer_time and answer_time < 5:  # Fast answer bonus
                    base_score += GAME_CONFIG['points']['fast_answer_bonus']
        elif self.current_game == 'chinese_whispers':
            # Check for partial matches
            guess = self.player_answers[player_id].lower()
            target = self.current_word.lower()
            if len(set(guess.split()) & set(target.split())) > 0:
                base_score = GAME_CONFIG['points']['partial_guess']

        self.scores[player_id] = self.scores.get(player_id, 0) + base_score
        self.round_scores[player_id] = base_score
        return base_score

    def get_leaderboard(self):
        return sorted(
            [{'name': self.players[pid]['name'], 'score': score}
             for pid, score in self.scores.items() if not self.players[pid].get('is_host', False)],
            key=lambda x: x['score'],
            reverse=True
        )

    def is_round_complete(self):
        if self.current_game == 'chinese_whispers':
            return len(self.drawings) >= len(self.players)
        else:  # trivia
            return len(self.player_answers) >= len(self.players)

    def advance_round(self):
        self.round += 1
        self.reset_round()
        if self.current_game == 'chinese_whispers':
            random.shuffle(self.player_order)
            self.current_player_index = 0
            self.current_word = self.get_next_word()
        else:  # trivia
            self.current_question = self.get_next_question()

    def is_game_complete(self):
        return self.round >= self.total_rounds

# Routes
@fastapi_app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@fastapi_app.get("/host", response_class=HTMLResponse)
async def host_game(request: Request):
    # Generate a random room ID
    room_id = ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=6))
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Use the actual host URL from the request
    host = request.headers.get('host', request.base_url.hostname)
    protocol = 'https' if request.url.scheme == 'https' else 'http'
    join_url = f"{protocol}://{host}/join/{room_id}"
    qr.add_data(join_url)
    qr.make(fit=True)

    # Create QR code image
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code to static directory with room ID as filename
    qr_path = os.path.join(STATIC_DIR, f"qr_{room_id}.png")
    qr_img.save(qr_path)
    
    # Create room immediately
    rooms[room_id] = GameRoom(room_id)
    
    return templates.TemplateResponse(
        "host.html",
        {
            "request": request,
            "room_id": room_id,
            "qr_code": f"/static/qr_{room_id}.png",
            "join_url": join_url
        }
    )

@fastapi_app.get("/join/{room_id}", response_class=HTMLResponse)
async def join_game(request: Request, room_id: str):
    # Create room if it doesn't exist (for direct URL access)
    if room_id not in rooms:
        rooms[room_id] = GameRoom(room_id)
    
    # Get the actual host URL for WebSocket connection
    host = request.headers.get('host', request.base_url.hostname)
    protocol = 'wss' if request.url.scheme == 'https' else 'ws'
    ws_url = f"{protocol}://{host}"
    
    return templates.TemplateResponse(
        "player.html",
        {
            "request": request,
            "room_id": room_id,
            "ws_url": ws_url
        }
    )

# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def join_room(sid, data):
    """Handle player joining a room"""
    try:
        print(f"Join room request from {sid}: {data}")
        
        # Validate required data
        if not isinstance(data, dict):
            raise ValueError("Invalid data format")
        
        room_id = data.get('room_id')
        player_name = data.get('player_name')
        is_host = data.get('is_host', False)
        
        if not room_id:
            raise ValueError("Room ID is required")
        if not is_host and not player_name:
            raise ValueError("Player name is required")
            
        # Set player name for host
        if is_host:
            player_name = 'Host'
            
        print(f"Joining room {room_id} as {player_name} (host: {is_host})")
        
        # Create room if it doesn't exist
        if room_id not in rooms:
            print(f"Creating new room: {room_id}")
            rooms[room_id] = GameRoom(room_id)
            
        room = rooms[room_id]
        
        # Function to broadcast updated player list
        async def broadcast_player_list():
            player_list = [
                {
                    'name': p['name'],
                    'is_host': p.get('is_host', False),
                    'connected': p.get('connected', True),
                    'score': room.scores.get(s, 0)
                }
                for s, p in room.players.items()
                if p.get('connected', True)  # Only include connected players
            ]
            await sio.emit('player_list_update', {
                'players': player_list
            }, room=room_id)

        if is_host:
            if room.host_sid:
                # Remove old host
                if room.host_sid in room.players:
                    del room.players[room.host_sid]
                    await sio.leave_room(room.host_sid, room_id)
            room.host_sid = sid
            room.players[sid] = {
                'name': 'Host',
                'is_host': True,
                'connected': True
            }
            await sio.enter_room(sid, room_id)
            await sio.emit('join_success', {
                'player_name': 'Host',
                'room_id': room_id,
                'is_host': True
            }, room=sid)
            await broadcast_player_list()  # Broadcast updated player list
            return

        # Check if username is taken by an active player
        existing_sid = None
        for s, p in room.players.items():
            if not p.get('is_host') and p['name'] == player_name:
                if p.get('connected', True):
                    await sio.emit('join_error', {
                        'message': 'Username already taken'
                    }, room=sid)
                    return
                else:
                    # Found a disconnected player with the same name - allow reconnection
                    existing_sid = s
                    break

        if existing_sid:
            # Update the existing player entry
            if existing_sid in room.players:
                old_data = room.players[existing_sid]
                del room.players[existing_sid]
                await sio.leave_room(existing_sid, room_id)
                
                # Preserve scores and other data
                room.players[sid] = {
                    'name': player_name,
                    'connected': True,
                    'is_host': False,
                    'score': room.scores.get(existing_sid, 0)
                }
                if 'profile' in old_data:
                    room.players[sid]['profile'] = old_data['profile']
                
                # Update scores mapping
                if existing_sid in room.scores:
                    room.scores[sid] = room.scores.pop(existing_sid)

        # Check if username exists or create new user
        user = room.db.query(User).filter(User.username == player_name).first()
        if not user:
            user = User(username=player_name)
            room.db.add(user)
            room.db.commit()

        if not existing_sid:
            # Add new player
            room.players[sid] = {
                'name': player_name,
                'connected': True,
                'is_host': False,
                'score': 0,
                'user_id': user.id
            }

        await sio.enter_room(sid, room_id)
        
        # Get current player list
        player_list = [
            {
                'name': p['name'],
                'is_host': p.get('is_host', False),
                'connected': p.get('connected', True),
                'score': room.scores.get(s, 0)
            }
            for s, p in room.players.items()
            if p.get('connected', True)  # Only include connected players
        ]
        
        # Send join success with current player list
        await sio.emit('join_success', {
            'player_name': player_name,
            'room_id': room_id,
            'is_host': False,
            'current_players': player_list,
            'game_state': room.game_state,
            'current_game': room.current_game
        }, room=sid)
        
        # Broadcast updated player list to all clients in the room
        await broadcast_player_list()

    except ValueError as e:
        print(f"Validation error in join_room: {e}")
        await sio.emit('join_error', {
            'message': str(e),
            'type': 'validation_error'
        }, room=sid)
    except Exception as e:
        print(f"Unexpected error in join_room: {e}")
        await sio.emit('join_error', {
            'message': "An unexpected error occurred. Please try again.",
            'type': 'server_error',
            'details': str(e)
        }, room=sid)

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    for room_id, room in rooms.items():
        if sid in room.players:
            player_data = room.players[sid]
            # Mark player as disconnected instead of removing
            player_data['connected'] = False

            # Broadcast updated player list
            player_list = [
                {
                    'name': p['name'],
                    'is_host': p.get('is_host', False),
                    'connected': p.get('connected', True),
                    'score': room.scores.get(s, 0)
                }
                for s, p in room.players.items()
            ]
            await sio.emit('player_list_update', {
                'players': player_list
            }, room=room_id)

            # If this was the host, notify other players
            if sid == room.host_sid:
                await sio.emit('game_cancelled', {
                    'reason': 'Host disconnected from the game'
                }, room=room_id)

            # Handle special cases based on game state
            if room.current_game == 'chase':
                if sid == room.chaser:
                    # Chaser disconnected, reset chase game
                    room.chaser = None
                    room.chase_category = None
                    room.chase_contestant = None
                    room.game_state = 'waiting'
                    await sio.emit('chase_cancelled', {
                        'reason': 'Chaser disconnected'
                    }, room=room.room_id)
                elif sid == room.chase_contestant:
                    # Contestant disconnected, reset current chase
                    room.chase_contestant = None
                    room.game_state = 'chase_setup'
                    await sio.emit('chase_cancelled', {
                        'reason': 'Contestant disconnected'
                    }, room=room.room_id)

            # Update player list for all clients
            player_list = []
            for p_sid, p_data in room.players.items():
                if p_data['connected'] and not p_data.get('is_host'):  # Only include connected non-host players
                    player_list.append({
                        'name': p_data['name'],
                        'score': p_data.get('score', 0)
                    })

            await sio.emit('player_left', {
                'players': player_list,
                'disconnected_player': player_data['name']
            }, room=room.room_id)

            # If not enough players, end the game
            active_players = sum(1 for p in room.players.values()
                                 if p['connected'] and not p.get('is_host'))
            if active_players < 2:  # Minimum 2 players for any game
                room.game_state = 'waiting'
                room.current_game = None
                await sio.emit('game_cancelled', {
                    'reason': 'Not enough players'
                }, room=room.room_id)

            # If it was this player's turn in drawing game, move to next player
            if (room.game_state == 'playing' and
                    room.current_game == 'chinese_whispers' and
                    room.player_order[room.current_player_index] == sid):
                room.current_player_index = (room.current_player_index + 1) % len(room.player_order)
                next_player_id = room.player_order[room.current_player_index]

                # Skip disconnected players
                while not room.players[next_player_id]['connected']:
                    room.current_player_index = (room.current_player_index + 1) % len(room.player_order)
                    next_player_id = room.player_order[room.current_player_index]

                await sio.emit('next_player', {
                    'player': room.players[next_player_id]['name'],
                    'skipped_disconnected': True
                }, room=room.room_id)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"