# server/config/game_config.py

GAME_CONFIG = {
    # Basic game constraints
    'min_players': 3,
    'max_players': 12,
    'drawing_time': 60,      # seconds for Chinese Whispers drawing
    'guess_time': 30,        # seconds to guess in Chinese Whispers
    'trivia_time': 20,       # default time per trivia question
    'rounds_per_game': 3,
    'idle_timeout': 120,     # how many seconds before AFK?

    # Points & scoring
    'points': {
        'correct_guess': 100,
        'partial_guess': 50,
        'correct_trivia': 100,
        'fast_answer_bonus': 50,    # bonus for answering quickly
        'participation_bonus': 10,  # minimal points for participating
        'streak_multiplier': 0.25,  # each consecutive correct multiplies
        'comeback_bonus': 25,       # bonus for trailing players
        'perfect_round': 100        # bonus for no mistakes in a round
    },

    # Maximum consecutive skips allowed (Chinese Whispers)
    'max_consecutive_skips': 2,

    # Additional game-based config
    'difficulty_scaling': {
        'enabled': True
    },

    # Specific chase parameters
    'chase_board_size': 7,
    'chase_win': 500,   # points if contestant escapes
    'chase_catch': 300, # points if chaser catches

    # For dynamic time-limits depending on # of players
    'time_limits': {
        'chase': {
            '2': 30,   # 2 players
            '3+': 25   # 3 or more
        },
        'trivia': {
            '2-3': 30, # 2-3 players
            '4-6': 25, # 4-6 players
            '7+': 20   # 7 or more players
        },
        'drawing': {
            '2-3': 60,
            '4-6': 50,
            '7+': 40
        }
    },

    # Minimal definitions so code referencing "game_modes" works
    'game_modes': {
        'chinese_whispers': {
            'min_players': 2,
            'max_players': 12
        },
        'trivia': {
            'min_players': 2,
            'max_players': 12
        },
        'chase': {
            'min_players': 2,
            'max_players': 12
        }
    }
}

###############################################################################
# GAME_TOPICS: a dict of categories => { "easy": [...], "medium": [...], "hard": [...] }
# Your GameRoom code does: "for topic_words in GAME_TOPICS.values(): words = topic_words[self.difficulty_level]"
###############################################################################
GAME_TOPICS = {
    "animals": {
        "easy": ["cat", "dog", "mouse", "fish"],
        "medium": ["giraffe", "penguin", "kangaroo", "koala"],
        "hard": ["hippopotamus", "chameleon", "caterpillar", "crocodile"]
    },
    "food": {
        "easy": ["pizza", "rice", "milk", "bread"],
        "medium": ["noodles", "lasagna", "sushi", "sandwich"],
        "hard": ["bouillabaisse", "ratatouille", "tiramisu", "tzatziki"]
    },
    "places": {
        "easy": ["park", "city", "beach", "cave"],
        "medium": ["desert", "rainforest", "tundra", "savanna"],
        "hard": ["archipelago", "antarctica", "mount everest", "timbuktu"]
    }
}


###############################################################################
# MUSIC_CONFIG: minimal placeholder for "chase", "trivia", "chinese_whispers", etc.
# so `self.change_music("chase")` won't crash.
###############################################################################
MUSIC_CONFIG = {
    "chase": {
        "file": "static/music/chase.mp3",
        "volume": 0.4,
        "loop": True
    },
    "trivia": {
        "file": "static/music/trivia.mp3",
        "volume": 0.4,
        "loop": True
    },
    "chinese_whispers": {
        "file": "static/music/drawing.mp3",
        "volume": 0.4,
        "loop": True
    },
    "round_transition": {
        "file": "static/music/round_start.mp3",
        "volume": 0.5,
        "loop": False
    },
    "game_over": {
        "file": "static/music/game_over.mp3",
        "volume": 0.6,
        "loop": False
    }
}
