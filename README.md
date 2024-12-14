# Party Games Hub

A collection of fun multiplayer party games including Drawing Chinese Whispers and Trivia!

## Features

- Drawing Chinese Whispers: Players take turns drawing and guessing what others have drawn
- Trivia Game: Test your knowledge across various categories
- Easy to join with QR codes
- Real-time multiplayer gameplay
- Responsive design that works on all devices
- Background music and sound effects

## Setup and Installation

1. Install the required dependencies:
```bash
cd server
pip install -r requirements.txt
```

2. Start the server:
```bash
python main.py
```

3. Open a web browser and navigate to:
```
http://localhost:8000
```

4. To host a game:
   - Click "Host a Game"
   - Share the room code or QR code with players
   - Players can join by scanning the QR code or entering the room code

## Customizing Music

The game uses background music and sound effects that can be customized. To change the music:

1. Place your MP3 files in the `server/static/music/` directory
2. Update the music configuration in `server/config.py`
3. The music config supports:
   - `file`: Path to the MP3 file
   - `volume`: Volume level (0.0 to 1.0)
   - `loop`: Whether the music should loop

Example music configuration:
```python
MUSIC_CONFIG = {
    'lobby': {
        'file': 'static/music/your_lobby_music.mp3',
        'volume': 0.5,
        'loop': True
    },
    # ... other music settings
}
```

## Game Modes

### Drawing Chinese Whispers
- Players take turns drawing a given word
- Each player sees the previous player's drawing and tries to recreate it
- At the end, everyone tries to guess the original word
- Points are awarded for correct guesses

### Trivia Game
- Multiple choice questions from various categories
- Quick-fire rounds with time limits
- Points awarded for correct answers
- Leaderboard tracking

## Tips for Hosts

1. Use a TV or large screen to display the host view
2. Ensure all players have a stable internet connection
3. Keep the room code visible for players who need to rejoin
4. Test the audio levels before starting the game

## Requirements

- Python 3.7+
- Modern web browser
- Internet connection for multiplayer functionality
- Device with camera for QR code scanning (optional)