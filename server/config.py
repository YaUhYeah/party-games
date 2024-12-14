# Game configuration
GAME_CONFIG = {
    'min_players': 3,
    'max_players': 12,
    'drawing_time': 60,  # seconds
    'guess_time': 30,    # seconds
    'trivia_time': 20,   # seconds
    'rounds_per_game': 3,
    'points': {
        'correct_guess': 100,
        'partial_guess': 50,
        'correct_trivia': 100,
        'fast_answer_bonus': 50,  # bonus for answering within 5 seconds
    }
}

# Music and sound effects configuration
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
    },
    'round_start': {
        'file': 'static/music/round_start.mp3',
        'volume': 0.5,
        'loop': False
    },
    'game_over': {
        'file': 'static/music/game_over.mp3',
        'volume': 0.6,
        'loop': False
    },
    'timer_tick': {
        'file': 'static/music/tick.mp3',
        'volume': 0.3,
        'loop': False
    }
}

# Game topics and words
GAME_TOPICS = {
    'animals': [
        'elephant', 'giraffe', 'penguin', 'kangaroo', 'octopus', 'rhinoceros',
        'hippopotamus', 'crocodile', 'butterfly', 'dolphin', 'panda', 'koala',
        'platypus', 'flamingo', 'chameleon', 'peacock', 'sloth', 'armadillo'
    ],
    'food': [
        'pizza', 'sushi', 'hamburger', 'ice cream', 'tacos', 'spaghetti',
        'pancakes', 'chocolate cake', 'french fries', 'sandwich', 'popcorn',
        'hot dog', 'burrito', 'cupcake', 'donut', 'fortune cookie'
    ],
    'places': [
        'beach', 'mountain', 'city', 'forest', 'desert', 'volcano',
        'waterfall', 'castle', 'lighthouse', 'pyramid', 'space station',
        'underwater city', 'treehouse', 'ancient ruins', 'amusement park'
    ],
    'objects': [
        'telephone', 'bicycle', 'umbrella', 'glasses', 'camera', 'robot',
        'rocket ship', 'time machine', 'magic wand', 'treasure chest',
        'crystal ball', 'flying carpet', 'jetpack', 'submarine'
    ],
    'activities': [
        'skateboarding', 'surfing', 'dancing', 'painting', 'gardening',
        'cooking', 'juggling', 'rock climbing', 'scuba diving', 'skiing',
        'playing chess', 'building sandcastles', 'flying a kite'
    ],
    'fantasy': [
        'dragon', 'unicorn', 'wizard', 'mermaid', 'phoenix', 'fairy',
        'centaur', 'griffin', 'goblin', 'troll', 'leprechaun', 'yeti',
        'kraken', 'pegasus', 'chimera', 'basilisk'
    ]
}

# Trivia questions database
TRIVIA_QUESTIONS = [
    {
        'question': 'What is the largest planet in our solar system?',
        'options': ['Jupiter', 'Saturn', 'Neptune', 'Mars'],
        'correct': 'Jupiter',
        'category': 'Science',
        'difficulty': 'easy'
    },
    {
        'question': 'Which country has the longest coastline in the world?',
        'options': ['Canada', 'Russia', 'Indonesia', 'Australia'],
        'correct': 'Canada',
        'category': 'Geography',
        'difficulty': 'medium'
    },
    {
        'question': 'Who painted the Mona Lisa?',
        'options': ['Leonardo da Vinci', 'Vincent van Gogh', 'Pablo Picasso', 'Michelangelo'],
        'correct': 'Leonardo da Vinci',
        'category': 'Art',
        'difficulty': 'easy'
    },
    {
        'question': 'What is the chemical symbol for gold?',
        'options': ['Au', 'Ag', 'Fe', 'Cu'],
        'correct': 'Au',
        'category': 'Science',
        'difficulty': 'easy'
    },
    {
        'question': 'Which programming language was created by Guido van Rossum?',
        'options': ['Python', 'Java', 'C++', 'Ruby'],
        'correct': 'Python',
        'category': 'Technology',
        'difficulty': 'medium'
    },
    {
        'question': 'What is the capital of Japan?',
        'options': ['Tokyo', 'Seoul', 'Beijing', 'Bangkok'],
        'correct': 'Tokyo',
        'category': 'Geography',
        'difficulty': 'easy'
    },
    {
        'question': 'Who wrote "Romeo and Juliet"?',
        'options': ['William Shakespeare', 'Charles Dickens', 'Jane Austen', 'Mark Twain'],
        'correct': 'William Shakespeare',
        'category': 'Literature',
        'difficulty': 'easy'
    },
    {
        'question': 'What is the speed of light in kilometers per second (approximate)?',
        'options': ['300,000', '200,000', '400,000', '500,000'],
        'correct': '300,000',
        'category': 'Science',
        'difficulty': 'hard'
    },
    {
        'question': 'Which ancient wonder of the world was located in Egypt?',
        'options': ['Great Pyramid of Giza', 'Hanging Gardens', 'Colossus of Rhodes', 'Temple of Artemis'],
        'correct': 'Great Pyramid of Giza',
        'category': 'History',
        'difficulty': 'medium'
    },
    {
        'question': 'What is the largest organ in the human body?',
        'options': ['Skin', 'Liver', 'Heart', 'Brain'],
        'correct': 'Skin',
        'category': 'Biology',
        'difficulty': 'medium'
    },
    {
        'question': 'Which element has the atomic number 1?',
        'options': ['Hydrogen', 'Helium', 'Carbon', 'Oxygen'],
        'correct': 'Hydrogen',
        'category': 'Science',
        'difficulty': 'medium'
    },
    {
        'question': 'Who is known as the father of modern physics?',
        'options': ['Albert Einstein', 'Isaac Newton', 'Niels Bohr', 'Galileo Galilei'],
        'correct': 'Albert Einstein',
        'category': 'Science',
        'difficulty': 'medium'
    },
    {
        'question': 'What is the longest river in the world?',
        'options': ['Nile', 'Amazon', 'Yangtze', 'Mississippi'],
        'correct': 'Nile',
        'category': 'Geography',
        'difficulty': 'medium'
    },
    {
        'question': 'Which planet is known as the Red Planet?',
        'options': ['Mars', 'Venus', 'Jupiter', 'Mercury'],
        'correct': 'Mars',
        'category': 'Science',
        'difficulty': 'easy'
    },
    {
        'question': 'What is the smallest prime number?',
        'options': ['2', '1', '3', '0'],
        'correct': '2',
        'category': 'Mathematics',
        'difficulty': 'easy'
    }
]

# Game animations configuration
ANIMATIONS = {
    'correct_answer': {
        'duration': 1000,
        'type': 'bounce',
        'color': '#4CAF50'
    },
    'wrong_answer': {
        'duration': 800,
        'type': 'shake',
        'color': '#F44336'
    },
    'time_warning': {
        'duration': 500,
        'type': 'pulse',
        'color': '#FFC107'
    },
    'round_transition': {
        'duration': 1200,
        'type': 'fade',
        'color': '#2196F3'
    }
}