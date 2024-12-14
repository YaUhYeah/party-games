import os
import socketio
import random
import json
import qrcode
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path

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
        self.scores = {}
        self.topic = None

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

@sio.event
async def start_game(sid, data):
    room_id = data['room_id']
    game_type = data['game_type']
    if room_id in rooms:
        room = rooms[room_id]
        room.game_state = 'playing'
        room.current_game = game_type
        
        if game_type == 'chinese_whispers':
            topic = random.choice(list(GAME_TOPICS.keys()))
            word = random.choice(GAME_TOPICS[topic])
            room.current_word = word
            room.topic = topic
            player_order = list(room.players.keys())
            random.shuffle(player_order)
            await sio.emit('game_started', {
                'game_type': game_type,
                'first_player': room.players[player_order[0]]['name'],
                'word': word
            }, room=room_id)
        elif game_type == 'trivia':
            question = random.choice(TRIVIA_QUESTIONS)
            await sio.emit('trivia_question', question, room=room_id)

@sio.event
async def submit_drawing(sid, data):
    room_id = data['room_id']
    drawing_data = data['drawing']
    if room_id in rooms:
        room = rooms[room_id]
        room.drawings.append({
            'player': room.players[sid]['name'],
            'drawing': drawing_data
        })
        
        if len(room.drawings) == len(room.players):
            await sio.emit('all_drawings_complete', {
                'drawings': room.drawings,
                'original_word': room.current_word
            }, room=room_id)

@sio.event
async def submit_guess(sid, data):
    room_id = data['room_id']
    guess = data['guess']
    if room_id in rooms:
        room = rooms[room_id]
        if guess.lower() == room.current_word.lower():
            room.players[sid]['score'] += 100
            await sio.emit('guess_result', {
                'correct': True,
                'player': room.players[sid]['name'],
                'scores': {p['name']: p['score'] for p in room.players.values()}
            }, room=room_id)

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