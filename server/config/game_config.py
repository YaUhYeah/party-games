"""Game configuration module."""

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