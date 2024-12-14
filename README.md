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