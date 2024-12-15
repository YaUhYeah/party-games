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
    'idle_timeout': 300,  # 5 minutes
    'afk_warning_time': 240,  # 4 minutes
    'min_word_length': 4,
    'max_consecutive_skips': 2,
    'comeback_mechanics': {
        'points_multiplier': 1.2,  # 20% bonus for players in last place
        'extra_time': 5  # Extra seconds for players trailing
    },
    'difficulty_scaling': {
        'enabled': True,
        'scale_factor': 0.1  # Increase difficulty by 10% each round
    },
    'points': {
        'correct_guess': 100,
        'partial_guess': 50,
        'correct_trivia': 100,
        'fast_answer_bonus': 50,  # bonus for answering within 5 seconds
        'chase_win': 500,  # contestant escapes chaser
        'chase_catch': 300,  # chaser catches contestant
        'chase_step': 100,  # contestant moves one step closer to safety
        'participation_bonus': 10,  # Small bonus for participating
        'streak_multiplier': 0.1,  # 10% bonus per correct answer streak
        'comeback_bonus': 20,  # Bonus for players in last place
        'perfect_round': 200,  # Bonus for perfect round
    }
}

# Music configuration with dynamic transitions
MUSIC_CONFIG = {
    'lobby': {
        'file': 'static/music/lobby.mp3',
        'volume': 0.5,
        'loop': True,
        'fade_out': 1.5
    },
    'drawing': {
        'file': 'static/music/drawing.mp3',
        'volume': 0.4,
        'loop': True,
        'fade_in': 1,
        'fade_out': 1
    },
    'trivia': {
        'file': 'static/music/trivia.mp3',
        'volume': 0.4,
        'loop': True,
        'fade_in': 1,
        'fade_out': 1
    },
    'correct_answer': {
        'file': 'static/music/correct.mp3',
        'volume': 0.6,
        'loop': False,
        'fade_out': 0.5
    },
    'wrong_answer': {
        'file': 'static/music/wrong.mp3',
        'volume': 0.6,
        'loop': False,
        'fade_out': 0.5
    },
    'round_transition': {
        'file': 'static/music/round_start.mp3',
        'volume': 0.5,
        'loop': False,
        'fade_in': 2,
        'fade_out': 1.5
    },
    'tension': {
        'file': 'static/music/tick.mp3',
        'volume': 0.7,
        'loop': True,
        'fade_in': 1,
        'fade_out': 0.5
    },
    'game_over': {
        'file': 'static/music/game_over.mp3',
        'volume': 0.6,
        'loop': False,
        'fade_in': 1
    }
}

# Enhanced game topics with varied difficulty levels
GAME_TOPICS = {
    'animals': {
        'easy': ['cat', 'dog', 'fish', 'bird', 'pig'],
        'medium': ['elephant', 'giraffe', 'penguin', 'kangaroo', 'octopus'],
        'hard': ['platypus', 'chameleon', 'narwhal', 'armadillo', 'pangolin']
    },
    'food': {
        'easy': ['apple', 'bread', 'cake', 'milk', 'egg'],
        'medium': ['pizza', 'sushi', 'hamburger', 'ice cream', 'tacos'],
        'hard': ['ratatouille', 'tiramisu', 'croissant', 'guacamole', 'bruschetta']
    },
    'places': {
        'easy': ['house', 'park', 'school', 'store', 'farm'],
        'medium': ['beach', 'mountain', 'city', 'forest', 'desert'],
        'hard': ['observatory', 'lighthouse', 'monastery', 'aquarium', 'colosseum']
    },
    'objects': {
        'easy': ['book', 'chair', 'table', 'door', 'bed'],
        'medium': ['telephone', 'bicycle', 'umbrella', 'glasses', 'camera'],
        'hard': ['microscope', 'telescope', 'typewriter', 'chandelier', 'gramophone']
    },
    'emotions': {
        'easy': ['happy', 'sad', 'mad', 'tired', 'shy'],
        'medium': ['excited', 'worried', 'confused', 'surprised', 'scared'],
        'hard': ['anxious', 'nostalgic', 'confident', 'suspicious', 'determined']
    },
    'actions': {
        'easy': ['run', 'jump', 'walk', 'sit', 'eat'],
        'medium': ['dancing', 'swimming', 'cooking', 'reading', 'painting'],
        'hard': ['meditating', 'conducting', 'juggling', 'skateboarding', 'somersaulting']
    },
    'weather': {
        'easy': ['sun', 'rain', 'snow', 'wind', 'cloud'],
        'medium': ['rainbow', 'storm', 'fog', 'hail', 'frost'],
        'hard': ['hurricane', 'tornado', 'blizzard', 'avalanche', 'thunderstorm']
    },
    'sports': {
        'easy': ['ball', 'bat', 'run', 'jump', 'swim'],
        'medium': ['soccer', 'basketball', 'tennis', 'baseball', 'volleyball'],
        'hard': ['badminton', 'waterpolo', 'lacrosse', 'cricket', 'rugby']
    }
}