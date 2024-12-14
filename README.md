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

### Easy Setup (Recommended)

#### Windows:
1. Download and install Python 3.7+ from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation
2. Double-click `setup.bat`
3. Follow the instructions shown in the terminal

#### Linux/macOS:
1. Open terminal in the project directory
2. Make the setup script executable:
   ```bash
   chmod +x setup.sh
   ```
3. Run the setup script:
   ```bash
   ./setup.sh
   ```
4. Follow the instructions shown in the terminal

### Manual Setup

If the automatic setup doesn't work, follow these steps:

1. Install Python 3.7+ from [python.org](https://www.python.org/downloads/)

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   python -m pip install -r server/requirements.txt
   ```

4. Create necessary directories:
   ```bash
   mkdir -p server/static/music
   ```

### Starting the Server

1. Activate the virtual environment (if not already activated):
   ```bash
   # Windows
   venv\Scripts\activate

   # Linux/macOS
   source venv/bin/activate
   ```

2. Start the server:
   ```bash
   python server/main.py
   ```

3. Open a web browser and navigate to:
   ```
   http://localhost:8000
   ```

### Troubleshooting

If you get a "pip not recognized" error:
1. Make sure Python is installed and added to PATH
2. Try using `python -m pip` instead of just `pip`
3. On Linux/macOS, try `python3` and `pip3` instead

If you get a "module not found" error:
1. Make sure you're in the virtual environment (you should see `(venv)` in your terminal)
2. Try reinstalling the requirements:
   ```bash
   python -m pip install --force-reinstall -r server/requirements.txt
   ```

For other issues, make sure:
1. All commands are run from the project root directory
2. Python 3.7+ is installed (`python --version` to check)
3. Virtual environment is activated
4. All requirements are installed correctly

4. To host a game:
   - Click "Host a Game"
   - Share the room code or QR code with players
   - Players can join by scanning the QR code or entering the room code

## Customizing Music and Sound Effects

The game uses background music and sound effects to enhance the gaming experience. Here's how to customize them:

### Required Sound Files

Place the following MP3 files in the `server/static/music/` directory:

#### Background Music
- `lobby.mp3`: Played in the waiting room
- `drawing.mp3`: Played during the drawing game
- `trivia.mp3`: Played during the trivia game
- `game_over.mp3`: Played at the end of the game

#### Sound Effects
- `correct_answer.mp3`: Played when a player answers correctly
- `wrong_answer.mp3`: Played when a player answers incorrectly
- `round_start.mp3`: Played at the start of each round
- `player_join.mp3`: Played when a new player joins
- `player_leave.mp3`: Played when a player leaves
- `submit.mp3`: Played when submitting a drawing or answer
- `clear.mp3`: Played when clearing the canvas
- `tick.mp3`: Played during the last 5 seconds of a timer
- `time_up.mp3`: Played when time runs out
- `your_turn.mp3`: Played when it's the player's turn
- `error.mp3`: Played when an error occurs

### Customizing Sound Settings

You can customize the volume and behavior of each sound in `server/config.py`:

```python
MUSIC_CONFIG = {
    'lobby': {
        'file': 'static/music/your_lobby_music.mp3',
        'volume': 0.5,  # 0.0 to 1.0
        'loop': True    # Whether to loop the audio
    },
    # ... other sound settings
}
```

### Recommended Sound Specifications

For the best experience, use audio files that meet these specifications:

1. Background Music:
   - Format: MP3
   - Duration: 1-3 minutes (will loop)
   - Quality: 128-192 kbps
   - Volume: Normalized to -14 LUFS

2. Sound Effects:
   - Format: MP3
   - Duration: 0.5-2 seconds
   - Quality: 128-192 kbps
   - Volume: Normalized to -12 LUFS

### Finding Sound Files

You can find suitable sound files from these sources:
1. [OpenGameArt.org](https://opengameart.org/) - Free game assets
2. [Freesound](https://freesound.org/) - Creative Commons sound effects
3. [Incompetech](https://incompetech.com/) - Royalty-free music

Remember to check the licensing terms and give appropriate attribution when required.

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