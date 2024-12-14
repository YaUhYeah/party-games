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

# Trivia and Chase questions
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

CHASE_QUESTIONS = {
    'Science': [
        {
            'question': 'What is the chemical symbol for gold?',
            'options': ['Au', 'Ag', 'Fe', 'Cu'],
            'correct': 'Au',
            'difficulty': 1
        },
        {
            'question': 'Which planet is known as the Red Planet?',
            'options': ['Mars', 'Venus', 'Jupiter', 'Mercury'],
            'correct': 'Mars',
            'difficulty': 1
        },
        {
            'question': 'What is the hardest natural substance on Earth?',
            'options': ['Diamond', 'Titanium', 'Platinum', 'Gold'],
            'correct': 'Diamond',
            'difficulty': 2
        },
        {
            'question': 'What is the speed of light in kilometers per second (approximate)?',
            'options': ['300,000', '200,000', '400,000', '500,000'],
            'correct': '300,000',
            'difficulty': 2
        }
    ],
    'History': [
        {
            'question': 'In which year did World War II end?',
            'options': ['1945', '1944', '1946', '1943'],
            'correct': '1945',
            'difficulty': 1
        },
        {
            'question': 'Who was the first President of the United States?',
            'options': ['George Washington', 'Thomas Jefferson', 'John Adams', 'Benjamin Franklin'],
            'correct': 'George Washington',
            'difficulty': 1
        },
        {
            'question': 'Which ancient wonder was located in Alexandria?',
            'options': ['Lighthouse', 'Colossus', 'Hanging Gardens', 'Temple of Artemis'],
            'correct': 'Lighthouse',
            'difficulty': 2
        }
    ],
    'Geography': [
        {
            'question': 'What is the capital of Australia?',
            'options': ['Canberra', 'Sydney', 'Melbourne', 'Perth'],
            'correct': 'Canberra',
            'difficulty': 1
        },
        {
            'question': 'Which is the longest river in the world?',
            'options': ['Nile', 'Amazon', 'Mississippi', 'Yangtze'],
            'correct': 'Nile',
            'difficulty': 1
        },
        {
            'question': 'In which mountain range would you find K2?',
            'options': ['Himalayas', 'Andes', 'Alps', 'Rockies'],
            'correct': 'Himalayas',
            'difficulty': 2
        }
    ],
    'Entertainment': [
        {
            'question': 'Who played Iron Man in the Marvel Cinematic Universe?',
            'options': ['Robert Downey Jr.', 'Chris Evans', 'Chris Hemsworth', 'Mark Ruffalo'],
            'correct': 'Robert Downey Jr.',
            'difficulty': 1
        },
        {
            'question': 'Which band performed "Bohemian Rhapsody"?',
            'options': ['Queen', 'The Beatles', 'Led Zeppelin', 'Pink Floyd'],
            'correct': 'Queen',
            'difficulty': 1
        },
        {
            'question': 'Who wrote "Romeo and Juliet"?',
            'options': ['William Shakespeare', 'Charles Dickens', 'Jane Austen', 'Mark Twain'],
            'correct': 'William Shakespeare',
            'difficulty': 1
        }
    ]
}
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
        
    def start_chase_game(self, chaser_sid: str, category: str):
        """Initialize a new chase game with the given chaser and category"""
        if category not in CHASE_QUESTIONS:
            raise ValueError(f"Invalid category: {category}")
            
        self.current_game = 'chase'
        self.game_state = 'chase_setup'
        self.chaser = chaser_sid
        self.chase_category = category
        self.chase_position = 0
        self.chase_contestant = None
        self.chase_questions = []
        
        # Select questions for this chase game
        available_questions = CHASE_QUESTIONS[category]
        easy_questions = [q for q in available_questions if q['difficulty'] == 1]
        hard_questions = [q for q in available_questions if q['difficulty'] == 2]
        
        # Mix questions to create a balanced set
        self.chase_questions = (
            random.sample(easy_questions, min(3, len(easy_questions))) +
            random.sample(hard_questions, min(2, len(hard_questions)))
        )
        random.shuffle(self.chase_questions)
        
    def select_chase_contestant(self, contestant_sid: str):
        """Select the next contestant for the chase"""
        if contestant_sid not in self.players or contestant_sid == self.chaser:
            raise ValueError("Invalid contestant")
            
        self.chase_contestant = contestant_sid
        self.chase_position = 0
        self.game_state = 'chase_question'
        return self.chase_questions[0]
        
    def process_chase_answer(self, player_sid: str, answer: str) -> dict:
        """Process an answer in the chase game"""
        current_question = self.chase_questions[0]
        is_correct = answer == current_question['correct']
        is_contestant = player_sid == self.chase_contestant
        
        result = {
            'is_correct': is_correct,
            'correct_answer': current_question['correct'],
            'player_type': 'contestant' if is_contestant else 'chaser',
            'position_change': 0
        }
        
        if is_contestant and is_correct:
            self.chase_position += 1
            result['position_change'] = 1
            
        elif not is_contestant and is_correct:  # Chaser
            self.chase_position -= 1
            result['position_change'] = -1
            
        # Check if chase is over
        if self.chase_position >= GAME_CONFIG['chase_board_size']:
            result['game_over'] = True
            result['winner'] = 'contestant'
            self.scores[self.chase_contestant] = self.scores.get(self.chase_contestant, 0) + GAME_CONFIG['chase_win']
            
        elif self.chase_position <= -1:
            result['game_over'] = True
            result['winner'] = 'chaser'
            self.scores[self.chaser] = self.scores.get(self.chaser, 0) + GAME_CONFIG['chase_catch']
            
        else:
            # Move to next question
            self.chase_questions.pop(0)
            if self.chase_questions:
                result['next_question'] = self.chase_questions[0]
            else:
                result['game_over'] = True
                result['winner'] = 'contestant' if self.chase_position > 0 else 'chaser'
                if result['winner'] == 'contestant':
                    self.scores[self.chase_contestant] = self.scores.get(self.chase_contestant, 0) + GAME_CONFIG['chase_win']
                else:
                    self.scores[self.chaser] = self.scores.get(self.chaser, 0) + GAME_CONFIG['chase_catch']
                    
        return result
        
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
    is_host = data.get('is_host', False)
    player_name = 'Host' if is_host else data['player_name']
    profile_picture = data.get('profile_picture')
    
    if room_id in rooms:
        room = rooms[room_id]
        
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
            return
        
        # Check if player is already in the room (rejoin case)
        existing_sid = None
        for s, p in room.players.items():
            if not p.get('is_host') and p['name'] == player_name:
                existing_sid = s
                break
        
        if existing_sid:
            # Remove old connection
            if existing_sid in room.players:
                del room.players[existing_sid]
                await sio.leave_room(existing_sid, room_id)
        
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
            'score': 0,
            'connected': True,
            'is_host': False
        }
        
        await sio.enter_room(sid, room_id)
        
        # Send current game state to rejoining player
        if room.game_state != 'waiting':
            state_data = {
                'state': room.game_state,
                'game_type': room.current_game,
                'round': room.round,
                'total_rounds': room.total_rounds,
            }
            
            if room.current_game == 'chinese_whispers':
                state_data.update({
                    'current_word': room.current_word,
                    'is_your_turn': room.player_order[room.current_player_index] == sid
                })
            elif room.current_game == 'trivia':
                state_data['current_question'] = room.current_question
            elif room.current_game == 'chase':
                state_data.update({
                    'chase_category': room.chase_category,
                    'chase_position': room.chase_position,
                    'is_chaser': room.chaser == sid,
                    'is_contestant': room.chase_contestant == sid,
                    'current_question': room.chase_questions[0] if room.chase_questions else None
                })
            
            await sio.emit('game_state', state_data, room=sid)
        
        # Update all clients with new player list
        player_list = []
        for player_sid, player_data in room.players.items():
            if player_data['connected'] and not player_data.get('is_host'):
                player_list.append({
                    'name': player_data['name'],
                    'score': player_data.get('score', 0)
                })
        
        await sio.emit('player_joined', {
            'players': player_list
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
        
        # Count connected non-host players
        connected_players = sum(1 for p in room.players.values() 
                              if p['connected'] and not p.get('is_host'))
        
        if game_type == 'chase':
            if connected_players < 2:
                await sio.emit('error', {
                    'message': 'Need at least 2 players for Chase game'
                }, room=sid)
                return
                
            # Let players choose roles
            room.game_state = 'chase_setup'
            room.current_game = 'chase'
            await sio.emit('chase_setup', {
                'categories': list(CHASE_QUESTIONS.keys())
            }, room=room_id)
            return
            
        elif connected_players < GAME_CONFIG['min_players']:
            await sio.emit('error', {
                'message': f"Need at least {GAME_CONFIG['min_players']} connected players to start"
            }, room=sid)
            return
            
        room.game_state = 'playing'
        room.current_game = game_type
        
        # Only include connected non-host players in the game order
        room.player_order = [sid for sid, player in room.players.items() 
                           if player['connected'] and not player.get('is_host')]
        random.shuffle(room.player_order)
        room.current_player_index = 0
        
        if game_type == 'chinese_whispers':
            room.current_word = room.get_next_word()
            first_player = room.players[room.player_order[0]]
            
            # Send game start to all players
            await sio.emit('game_started', {
                'game_type': game_type,
                'first_player': first_player['name'],
                'round': room.round + 1,
                'total_rounds': room.total_rounds
            }, room=room_id)
            
            # Send word only to first player
            await sio.emit('your_turn', {
                'word': room.current_word,
                'time_limit': GAME_CONFIG['drawing_time']
            }, room=room.player_order[0])
            
        elif game_type == 'trivia':
            room.current_question = room.get_next_question()
            await sio.emit('game_started', {
                'game_type': game_type,
                'question': room.current_question,
                'round': room.round + 1,
                'total_rounds': room.total_rounds,
                'time_limit': GAME_CONFIG['trivia_time']
            }, room=room_id)
            
        await start_round_timer(room)

@sio.event
async def select_chase_role(sid, data):
    room_id = data['room_id']
    role = data['role']  # 'chaser' or 'contestant'
    category = data.get('category')  # Required for chaser
    
    if room_id not in rooms:
        return
        
    room = rooms[room_id]
    if room.current_game != 'chase' or room.game_state != 'chase_setup':
        return
        
    if role == 'chaser':
        if not category:
            await sio.emit('error', {
                'message': 'Chaser must select a category'
            }, room=sid)
            return
            
        try:
            room.start_chase_game(sid, category)
            await sio.emit('chase_started', {
                'chaser': room.players[sid]['name'],
                'category': category
            }, room=room_id)
        except ValueError as e:
            await sio.emit('error', {
                'message': str(e)
            }, room=sid)
            
    elif role == 'contestant':
        if not room.chaser:
            await sio.emit('error', {
                'message': 'Wait for chaser to select category'
            }, room=sid)
            return
            
        if room.chase_contestant:
            await sio.emit('error', {
                'message': 'Another contestant is currently playing'
            }, room=sid)
            return
            
        try:
            question = room.select_chase_contestant(sid)
            await sio.emit('chase_question', {
                'contestant': room.players[sid]['name'],
                'question': question,
                'position': room.chase_position,
                'board_size': GAME_CONFIG['chase_board_size']
            }, room=room_id)
        except ValueError as e:
            await sio.emit('error', {
                'message': str(e)
            }, room=sid)

@sio.event
async def submit_chase_answer(sid, data):
    room_id = data['room_id']
    answer = data['answer']
    
    if room_id not in rooms:
        return
        
    room = rooms[room_id]
    if room.current_game != 'chase' or room.game_state != 'chase_question':
        return
        
    if sid != room.chaser and sid != room.chase_contestant:
        await sio.emit('error', {
            'message': 'Only chaser and current contestant can answer'
        }, room=sid)
        return
        
    result = room.process_chase_answer(sid, answer)
    
    # Notify all players of the result
    await sio.emit('chase_answer', {
        'player': room.players[sid]['name'],
        'answer': answer,
        'result': result,
        'position': room.chase_position
    }, room=room_id)
    
    if result.get('game_over'):
        # Update achievements
        if result['winner'] == 'contestant':
            achievement = Achievement(
                user_id=room.players[room.chase_contestant]['user_id'],
                name='Chase Escape',
                description='Successfully escaped the chaser'
            )
            room.db.add(achievement)
        elif result['winner'] == 'chaser':
            achievement = Achievement(
                user_id=room.players[room.chaser]['user_id'],
                name='Master Chaser',
                description='Successfully caught a contestant'
            )
            room.db.add(achievement)
        room.db.commit()
        
        # Start new chase or end game
        room.chase_contestant = None
        room.game_state = 'chase_setup'
        await sio.emit('chase_complete', {
            'winner': result['winner'],
            'leaderboard': room.get_leaderboard()
        }, room=room_id)
    elif result.get('next_question'):
        await sio.emit('chase_question', {
            'question': result['next_question'],
            'position': room.chase_position,
            'board_size': GAME_CONFIG['chase_board_size']
        }, room=room_id)

@sio.event
async def submit_drawing(sid, data):
    room_id = data['room_id']
    drawing_data = data['drawing']
    if room_id in rooms:
        room = rooms[room_id]
        if room.game_state != 'playing' or room.current_game != 'chinese_whispers':
            return
            
        # Verify it's the player's turn
        if room.player_order[room.current_player_index] != sid:
            await sio.emit('error', {
                'message': "It's not your turn to draw"
            }, room=sid)
            return
            
        room.drawings.append({
            'player': room.players[sid]['name'],
            'drawing': drawing_data,
            'timestamp': datetime.now().isoformat()
        })
        
        # Move to next player or end round
        if len(room.drawings) >= len(room.player_order):  # Only count connected players
            await sio.emit('all_drawings_complete', {
                'drawings': room.drawings,
                'original_word': room.current_word
            }, room=room_id)
            room.game_state = 'guessing'
        else:
            # Find next connected player
            room.current_player_index = (room.current_player_index + 1) % len(room.player_order)
            next_player_id = room.player_order[room.current_player_index]
            
            # Send game state to all players
            await sio.emit('next_player', {
                'player': room.players[next_player_id]['name'],
                'previous_drawing': drawing_data,
                'round': room.round + 1,
                'total_rounds': room.total_rounds
            }, room=room_id)
            
            # Send word to next player
            await sio.emit('your_turn', {
                'word': room.current_word,
                'time_limit': GAME_CONFIG['drawing_time'],
                'previous_drawing': drawing_data
            }, room=next_player_id)
            
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
            player_data = room.players[sid]
            # Mark player as disconnected instead of removing
            player_data['connected'] = False
            
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