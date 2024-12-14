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
    'rounds_per_game': 3,
    'points': {
        'correct_guess': 100,
        'partial_guess': 50,
        'correct_trivia': 100,
        'fast_answer_bonus': 50,  # bonus for answering within 5 seconds
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

# Trivia questions
TRIVIA_QUESTIONS = [
    {
        'question': 'What is the largest planet in our solar system?',
        'options': ['Jupiter', 'Saturn', 'Neptune', 'Mars'],
        'correct': 'Jupiter',
        'category': 'Science'
    },
    {
        'question': 'Which country has the longest coastline in the world?',
        'options': ['Canada', 'Russia', 'Indonesia', 'Australia'],
        'correct': 'Canada',
        'category': 'Geography'
    }
]
from database import get_db, User, GameScore, Achievement

app = FastAPI()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Configure CORS for Socket.IO
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # Allow connections from any origin
    ping_timeout=35,
    ping_interval=25,
    max_http_buffer_size=1e8  # 100MB max message size
)

# Create Socket.IO ASGI app
socket_app = socketio.ASGIApp(
    sio,
    app,
    static_files={
        '/': {'content_type': 'text/html', 'filename': 'index.html'}
    }
)

# Mount static files and templates
# Get the absolute path to the server directory
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(SERVER_DIR, "static")
TEMPLATES_DIR = os.path.join(SERVER_DIR, "templates")

# Create necessary directories if they don't exist
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "music"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "profiles"), exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Game state
rooms = {}
GAME_TOPICS = {
    'animals': ['elephant', 'giraffe', 'penguin', 'kangaroo', 'octopus'],
    'food': ['pizza', 'sushi', 'hamburger', 'ice cream', 'tacos'],
    'places': ['beach', 'mountain', 'city', 'forest', 'desert'],
    'objects': ['telephone', 'bicycle', 'umbrella', 'glasses', 'camera'],
}

TRIVIA_QUESTIONS = [
    {
        'question': 'What is the largest planet in our solar system?',
        'options': ['Jupiter', 'Saturn', 'Neptune', 'Mars'],
        'correct': 'Jupiter',
        'category': 'Science'
    },
    {
        'question': 'Which country has the longest coastline in the world?',
        'options': ['Canada', 'Russia', 'Indonesia', 'Australia'],
        'correct': 'Canada',
        'category': 'Geography'
    },
    # Add more questions here
]

class GameRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players = {}  # {sid: {'name': str, 'user_id': int, 'profile': str}}
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
             for pid, score in self.scores.items()],
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

# User profile and high score endpoints
@app.post("/api/users")
async def create_user(username: str, profile_picture: Optional[str] = None, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    user = User(username=username)
    if profile_picture:
        # Convert base64 to bytes
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
        # Get top scores for specific game type
        scores = db.query(GameScore).filter(GameScore.game_type == game_type)\
                  .order_by(GameScore.score.desc()).limit(10).all()
        return [{
            "username": db.query(User).filter(User.id == score.user_id).first().username,
            "score": score.score,
            "played_at": score.played_at
        } for score in scores]
    else:
        # Get overall top users
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
    room_id = ''.join(random.choices('0123456789', k=6))
    rooms[room_id] = GameRoom(room_id)
    
    # Get local IP address
    def get_local_ip():
        try:
            # Create a socket connection to an external server to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"

    local_ip = get_local_ip()
    host = f"{local_ip}:8000"
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f'http://{host}/join/{room_id}')
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    qr_path = os.path.join(STATIC_DIR, f'qr_{room_id}.png')
    qr_image.save(qr_path)
    
    return templates.TemplateResponse(
        "host.html",
        {"request": request, "room_id": room_id}
    )

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

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def join_room(sid, data):
    room_id = data['room_id']
    player_name = data['player_name']
    profile_picture = data.get('profile_picture')
    
    if room_id in rooms:
        room = rooms[room_id]
        
        # Check if username exists or create new user
        user = room.db.query(User).filter(User.username == player_name).first()
        if not user:
            user = User(username=player_name)
            if profile_picture:
                try:
                    image_data = base64.b64decode(profile_picture.split(',')[1])
                    user.profile_picture = image_data
                except:
                    pass  # Use default profile if conversion fails
            room.db.add(user)
            room.db.commit()
            room.db.refresh(user)
        
        # Store user info in room
        room.players[sid] = {
            'name': player_name,
            'user_id': user.id,
            'profile': profile_picture or '',
            'score': 0
        }
        
        await sio.enter_room(sid, room_id)
        await sio.emit('player_joined', {
            'players': [{
                'name': p['name'],
                'profile': p['profile']
            } for p in room.players.values()]
        }, room=room_id)

async def start_round_timer(room: GameRoom):
    """Start the timer for the current round"""
    if room.timer_task:
        room.timer_task.cancel()
    
    time_limit = GAME_CONFIG['drawing_time'] if room.current_game == 'chinese_whispers' else GAME_CONFIG['trivia_time']
    
    async def timer():
        await asyncio.sleep(time_limit)
        if room.game_state == 'playing':
            if room.current_game == 'chinese_whispers':
                # Force submission of current drawing
                if not room.is_round_complete():
                    await sio.emit('time_up', room=room.room_id)
            else:  # trivia
                await handle_round_end(room)
    
    room.timer_task = asyncio.create_task(timer())

async def handle_round_end(room: GameRoom):
    """Handle the end of a round"""
    if room.is_game_complete():
        # Game is over
        leaderboard = room.get_leaderboard()
        
        # Save scores and update user stats
        for sid, player in room.players.items():
            user = room.db.query(User).filter(User.id == player['user_id']).first()
            if user:
                # Update user stats
                user.games_played += 1
                user.total_score += player['score']
                if player['score'] > user.highest_score:
                    user.highest_score = player['score']
                
                # Save game score
                game_score = GameScore(
                    user_id=user.id,
                    game_type=room.current_game,
                    score=player['score'],
                    correct_answers=len([a for a in room.player_answers.values() 
                                      if isinstance(a, dict) and a.get('correct', False)]),
                    total_questions=room.round
                )
                room.db.add(game_score)
                
                # Check for achievements
                await check_achievements(room, user, player['score'])
        
        room.db.commit()
        
        # Get updated leaderboard with profile pictures
        final_leaderboard = [{
            'name': p['name'],
            'score': p['score'],
            'profile': p['profile']
        } for p in sorted(room.players.values(), key=lambda x: x['score'], reverse=True)]
        
        await sio.emit('game_over', {
            'leaderboard': final_leaderboard,
            'final_scores': room.scores,
            'achievements': await get_latest_achievements(room)
        }, room=room.room_id)
        room.game_state = 'finished'
    else:
        # Start next round
        room.advance_round()
        if room.current_game == 'chinese_whispers':
            await sio.emit('round_start', {
                'round': room.round,
                'total_rounds': room.total_rounds,
                'current_player': room.players[room.player_order[0]]['name'],
                'word': room.current_word
            }, room=room.room_id)
        else:  # trivia
            await sio.emit('trivia_question', {
                'round': room.round,
                'total_rounds': room.total_rounds,
                'question': room.current_question
            }, room=room.room_id)
        await start_round_timer(room)

@sio.event
async def start_game(sid, data):
    room_id = data['room_id']
    game_type = data['game_type']
    if room_id in rooms:
        room = rooms[room_id]
        
        if len(room.players) < GAME_CONFIG['min_players']:
            await sio.emit('error', {
                'message': f"Need at least {GAME_CONFIG['min_players']} players to start"
            }, room=sid)
            return
            
        room.game_state = 'playing'
        room.current_game = game_type
        room.player_order = list(room.players.keys())
        random.shuffle(room.player_order)
        
        if game_type == 'chinese_whispers':
            room.current_word = room.get_next_word()
            await sio.emit('game_started', {
                'game_type': game_type,
                'first_player': room.players[room.player_order[0]]['name'],
                'word': room.current_word,
                'round': room.round + 1,
                'total_rounds': room.total_rounds
            }, room=room_id)
        elif game_type == 'trivia':
            room.current_question = room.get_next_question()
            await sio.emit('game_started', {
                'game_type': game_type,
                'question': room.current_question,
                'round': room.round + 1,
                'total_rounds': room.total_rounds
            }, room=room_id)
            
        await start_round_timer(room)

@sio.event
async def submit_drawing(sid, data):
    room_id = data['room_id']
    drawing_data = data['drawing']
    if room_id in rooms:
        room = rooms[room_id]
        if room.game_state != 'playing' or room.current_game != 'chinese_whispers':
            return
            
        room.drawings.append({
            'player': room.players[sid]['name'],
            'drawing': drawing_data,
            'timestamp': datetime.now().isoformat()
        })
        
        # Move to next player or end round
        if room.is_round_complete():
            await sio.emit('all_drawings_complete', {
                'drawings': room.drawings,
                'original_word': room.current_word
            }, room=room_id)
            room.game_state = 'guessing'
        else:
            next_player_id = room.player_order[(room.current_player_index + 1) % len(room.player_order)]
            await sio.emit('next_player', {
                'player': room.players[next_player_id]['name'],
                'previous_drawing': drawing_data
            }, room=room_id)
            room.current_player_index += 1
            await start_round_timer(room)

@sio.event
async def submit_guess(sid, data):
    room_id = data['room_id']
    guess = data['guess']
    timestamp = datetime.now()
    
    if room_id in rooms:
        room = rooms[room_id]
        if room.game_state != 'guessing' and room.game_state != 'playing':
            return
            
        if room.current_game == 'chinese_whispers':
            room.player_answers[sid] = guess
            is_correct = guess.lower() == room.current_word.lower()
            score = room.calculate_score(sid, is_correct)
            
            await sio.emit('guess_result', {
                'correct': is_correct,
                'player': room.players[sid]['name'],
                'guess': guess,
                'score': score,
                'scores': room.get_leaderboard()
            }, room=room_id)
            
            if len(room.player_answers) >= len(room.players):
                await handle_round_end(room)
        else:  # trivia
            answer_time = (timestamp - room.round_start_time).total_seconds()
            is_correct = guess == room.current_question['correct']
            score = room.calculate_score(sid, is_correct, answer_time)
            
            await sio.emit('answer_result', {
                'correct': is_correct,
                'player': room.players[sid]['name'],
                'score': score,
                'answer_time': answer_time,
                'scores': room.get_leaderboard()
            }, room=room_id)
            
            room.player_answers[sid] = {
                'answer': guess,
                'correct': is_correct,
                'time': answer_time
            }
            
            if room.is_round_complete():
                await handle_round_end(room)

@sio.event
async def check_achievements(room: GameRoom, user: User, score: int):
    """Check and award achievements"""
    achievements = []
    
    # First game achievement
    if user.games_played == 1:
        achievements.append({
            'name': 'First Steps',
            'description': 'Complete your first game'
        })
    
    # High score achievements
    if score >= 1000:
        achievements.append({
            'name': 'Score Master',
            'description': 'Score 1000+ points in a single game'
        })
    
    # Games played achievements
    if user.games_played == 10:
        achievements.append({
            'name': 'Dedicated Player',
            'description': 'Play 10 games'
        })
    
    # Perfect round achievement
    if room.current_game == 'trivia' and all(
        answer.get('correct', False) for answer in room.player_answers.values()
        if isinstance(answer, dict)
    ):
        achievements.append({
            'name': 'Perfect Round',
            'description': 'Answer all questions correctly in a trivia round'
        })
    
    # Add achievements to database
    for achievement in achievements:
        existing = room.db.query(Achievement).filter(
            Achievement.user_id == user.id,
            Achievement.name == achievement['name']
        ).first()
        
        if not existing:
            new_achievement = Achievement(
                user_id=user.id,
                name=achievement['name'],
                description=achievement['description']
            )
            room.db.add(new_achievement)

async def get_latest_achievements(room: GameRoom):
    """Get achievements earned in the current game"""
    achievements = []
    for player in room.players.values():
        user_achievements = room.db.query(Achievement)\
            .filter(Achievement.user_id == player['user_id'])\
            .order_by(Achievement.unlocked_at.desc())\
            .limit(5)\
            .all()
        
        if user_achievements:
            achievements.append({
                'player': player['name'],
                'achievements': [{
                    'name': a.name,
                    'description': a.description,
                    'unlocked_at': a.unlocked_at
                } for a in user_achievements]
            })
    
    return achievements

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    for room in rooms.values():
        if sid in room.players:
            del room.players[sid]
            await sio.emit('player_left', {
                'players': [{
                    'name': p['name'],
                    'profile': p['profile']
                } for p in room.players.values()]
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

if __name__ == "__main__":
    import uvicorn
    
    local_ip = get_local_ip()
    print(f"\nServer running on:")
    print(f"Local:   http://localhost:8000")
    print(f"Network: http://{local_ip}:8000")
    print("\nShare these URLs with players:")
    print(f"1. Local players:  http://localhost:8000")
    print(f"2. Network/Mobile: http://{local_ip}:8000")
    print("\nPress CTRL+C to quit\n")
    
    uvicorn.run(
        "main:socket_app",
        host="0.0.0.0",  # Listen on all network interfaces
        port=8000,
        reload=True,
        reload_excludes=["*.log", "*.db"],  # Don't reload on log or database changes
        log_level="info"
    )