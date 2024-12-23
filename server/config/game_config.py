"""Game configuration module."""
from typing import Dict, Any, List

# Game configuration
GAME_CONFIG = {
    'chase_categories': [
        'general_knowledge',
        'science',
        'history',
        'geography',
        'entertainment',
        'sports',
        'literature',
        'technology'
    ],
    'min_players': 2,  # Reduced minimum players
    'max_players': 12,
    'time_limits': {
        'drawing': {
            '2-3': 90,   # More time for fewer players
            '4-6': 75,
            '7+': 60
        },
        'guess': {
            '2-3': 45,
            '4-6': 35,
            '7+': 30
        },
        'trivia': {
            '2-3': 25,
            '4-6': 20,
            '7+': 15
        },
        'chase': {
            '2': 20,     # Head-to-head mode
            '3+': 15
        }
    },
    'game_modes': {
        'chinese_whispers': {
            'min_players': 2,
            'two_player_mode': {
                'rounds': 5,        # More rounds for 2 players
                'hints_allowed': 2  # Extra hints for balance
            }
        },
        'trivia': {
            'min_players': 2,
            'two_player_mode': {
                'head_to_head': True,  # Direct competition
                'steal_points': True   # Steal points on wrong answers
            }
        },
        'chase': {
            'min_players': 2,
            'two_player_mode': {
                'roles_swap': True,    # Players swap chaser/contestant roles
                'quick_fire': True     # Faster rounds for 2 players
            }
        }
    },
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
        'scale_factor': 0.1,  # Increase difficulty by 10% each round
        'performance_threshold': {
            'easy_to_medium': 0.7,  # 70% success rate to advance
            'medium_to_hard': 0.8,  # 80% success rate to advance
            'fallback': 0.3  # Fall back to easier difficulty below 30%
        },
        'time_bonus': {
            'easy': 1.2,  # 20% more time
            'medium': 1.0,  # Standard time
            'hard': 0.8  # 20% less time
        }
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

# Enhanced game topics with varied difficulty levels and categories
GAME_TOPICS = {
    'animals': {
        'easy': [
            'cat', 'dog', 'fish', 'bird', 'pig', 'cow', 'horse', 'sheep', 'duck', 'chicken',
            'rabbit', 'mouse', 'frog', 'bear', 'lion'
        ],
        'medium': [
            'elephant', 'giraffe', 'penguin', 'kangaroo', 'octopus', 'dolphin', 'tiger',
            'panda', 'koala', 'zebra', 'monkey', 'gorilla', 'hippo', 'rhino', 'camel'
        ],
        'hard': [
            'platypus', 'chameleon', 'narwhal', 'armadillo', 'pangolin', 'axolotl',
            'echidna', 'quokka', 'tardigrade', 'capybara', 'lemur', 'sloth', 'tapir',
            'numbat', 'okapi'
        ]
    },
    'mythical_creatures': {
        'easy': [
            'dragon', 'unicorn', 'mermaid', 'fairy', 'phoenix', 'giant', 'troll',
            'elf', 'wizard', 'witch'
        ],
        'medium': [
            'griffin', 'centaur', 'pegasus', 'minotaur', 'sphinx', 'cyclops',
            'hydra', 'siren', 'goblin', 'vampire'
        ],
        'hard': [
            'chimera', 'basilisk', 'kraken', 'leviathan', 'banshee', 'wendigo',
            'kitsune', 'djinn', 'manticore', 'cockatrice'
        ]
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