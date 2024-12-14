import os
import socketio
import random
import json
import qrcode
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
from config import MUSIC_CONFIG, TRIVIA_QUESTIONS, GAME_TOPICS

app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi')
socket_app = socketio.ASGIApp(sio, app)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
        self.players = {}
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

@app.get("/", response_class=HTMLResponse)
async def home(request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.get("/host")
async def host_game(request):
    room_id = ''.join(random.choices('0123456789', k=6))
    rooms[room_id] = GameRoom(room_id)
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f'http://{request.client.host}:8000/join/{room_id}')
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    qr_path = f'static/qr_{room_id}.png'
    qr_image.save(qr_path)
    
    return templates.TemplateResponse(
        "host.html",
        {"request": request, "room_id": room_id}
    )

@app.get("/join/{room_id}")
async def join_game(request, room_id: str):
    if room_id not in rooms:
        return {"error": "Room not found"}
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
    if room_id in rooms:
        room = rooms[room_id]
        room.players[sid] = {
            'name': player_name,
            'score': 0
        }
        await sio.enter_room(sid, room_id)
        await sio.emit('player_joined', {
            'players': [p['name'] for p in room.players.values()]
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
        await sio.emit('game_over', {
            'leaderboard': leaderboard,
            'final_scores': room.scores
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
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    for room in rooms.values():
        if sid in room.players:
            del room.players[sid]
            await sio.emit('player_left', {
                'players': [p['name'] for p in room.players.values()]
            }, room=room.room_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:socket_app", host="0.0.0.0", port=8000, reload=True)