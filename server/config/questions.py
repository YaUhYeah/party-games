"""Question bank for trivia and chase games."""

# Trivia questions
TRIVIA_QUESTIONS = [
    # Science & Space
    {
        'question': 'What is the largest planet in our solar system?',
        'options': ['Jupiter', 'Saturn', 'Neptune', 'Mars'],
        'correct': 'Jupiter',
        'category': 'Science'
    },
    {
        'question': 'Which planet is known as the Red Planet?',
        'options': ['Mars', 'Venus', 'Jupiter', 'Mercury'],
        'correct': 'Mars',
        'category': 'Science'
    },
    {
        'question': 'What is the chemical symbol for gold?',
        'options': ['Au', 'Ag', 'Fe', 'Cu'],
        'correct': 'Au',
        'category': 'Science'
    },
    # Geography
    {
        'question': 'Which country has the longest coastline in the world?',
        'options': ['Canada', 'Russia', 'Indonesia', 'Australia'],
        'correct': 'Canada',
        'category': 'Geography'
    },
    {
        'question': 'What is the capital of Australia?',
        'options': ['Canberra', 'Sydney', 'Melbourne', 'Perth'],
        'correct': 'Canberra',
        'category': 'Geography'
    },
    {
        'question': 'Which is the largest ocean on Earth?',
        'options': ['Pacific', 'Atlantic', 'Indian', 'Arctic'],
        'correct': 'Pacific',
        'category': 'Geography'
    },
    # Entertainment
    {
        'question': 'Who played Iron Man in the Marvel Cinematic Universe?',
        'options': ['Robert Downey Jr.', 'Chris Evans', 'Chris Hemsworth', 'Mark Ruffalo'],
        'correct': 'Robert Downey Jr.',
        'category': 'Entertainment'
    },
    {
        'question': 'Which band performed "Bohemian Rhapsody"?',
        'options': ['Queen', 'The Beatles', 'Led Zeppelin', 'Pink Floyd'],
        'correct': 'Queen',
        'category': 'Entertainment'
    },
    {
        'question': 'What is the highest-grossing film of all time?',
        'options': ['Avatar', 'Avengers: Endgame', 'Titanic', 'Star Wars: Episode VII'],
        'correct': 'Avatar',
        'category': 'Entertainment'
    },
    # History
    {
        'question': 'In which year did World War II end?',
        'options': ['1945', '1944', '1946', '1943'],
        'correct': '1945',
        'category': 'History'
    },
    {
        'question': 'Who was the first President of the United States?',
        'options': ['George Washington', 'Thomas Jefferson', 'John Adams', 'Benjamin Franklin'],
        'correct': 'George Washington',
        'category': 'History'
    },
    {
        'question': 'Which ancient civilization built the pyramids of Giza?',
        'options': ['Egyptians', 'Greeks', 'Romans', 'Mayans'],
        'correct': 'Egyptians',
        'category': 'History'
    },
    # Sports
    {
        'question': 'Which country won the first FIFA World Cup in 1930?',
        'options': ['Uruguay', 'Brazil', 'Argentina', 'Italy'],
        'correct': 'Uruguay',
        'category': 'Sports'
    },
    {
        'question': 'In which sport would you perform a slam dunk?',
        'options': ['Basketball', 'Volleyball', 'Tennis', 'Soccer'],
        'correct': 'Basketball',
        'category': 'Sports'
    },
    {
        'question': 'How many players are on a standard soccer team during a match?',
        'options': ['11', '10', '12', '9'],
        'correct': '11',
        'category': 'Sports'
    },
    # Technology
    {
        'question': 'Who co-founded Apple Computer with Steve Jobs?',
        'options': ['Steve Wozniak', 'Bill Gates', 'Mark Zuckerberg', 'Jeff Bezos'],
        'correct': 'Steve Wozniak',
        'category': 'Technology'
    },
    {
        'question': 'What does "HTTP" stand for?',
        'options': ['Hypertext Transfer Protocol', 'High Tech Transfer Protocol', 'Hypertext Technical Program', 'High Tech Transport Program'],
        'correct': 'Hypertext Transfer Protocol',
        'category': 'Technology'
    },
    {
        'question': 'Which programming language is known as the "language of the web"?',
        'options': ['JavaScript', 'Python', 'Java', 'C++'],
        'correct': 'JavaScript',
        'category': 'Technology'
    }
]

# Chase game questions with difficulty levels
CHASE_QUESTIONS = {
    'Science': [
        {
            'question': 'What is the chemical symbol for gold?',
            'options': ['Au', 'Ag', 'Fe', 'Cu'],
            'correct': 'Au',
            'difficulty': 1
        },
        {
            'question': 'Which planet is known as the Red Planet?',
            'options': ['Mars', 'Venus', 'Jupiter', 'Mercury'],
            'correct': 'Mars',
            'difficulty': 1
        },
        {
            'question': 'What is the hardest natural substance on Earth?',
            'options': ['Diamond', 'Titanium', 'Platinum', 'Gold'],
            'correct': 'Diamond',
            'difficulty': 2
        }
    ],
    'History': [
        {
            'question': 'In which year did World War II end?',
            'options': ['1945', '1944', '1946', '1943'],
            'correct': '1945',
            'difficulty': 1
        },
        {
            'question': 'Who was the first President of the United States?',
            'options': ['George Washington', 'Thomas Jefferson', 'John Adams', 'Benjamin Franklin'],
            'correct': 'George Washington',
            'difficulty': 1
        },
        {
            'question': 'Which ancient wonder was located in Alexandria?',
            'options': ['Lighthouse', 'Colossus', 'Hanging Gardens', 'Temple of Artemis'],
            'correct': 'Lighthouse',
            'difficulty': 2
        }
    ],
    'Geography': [
        {
            'question': 'What is the capital of Australia?',
            'options': ['Canberra', 'Sydney', 'Melbourne', 'Perth'],
            'correct': 'Canberra',
            'difficulty': 1
        },
        {
            'question': 'Which is the longest river in the world?',
            'options': ['Nile', 'Amazon', 'Mississippi', 'Yangtze'],
            'correct': 'Nile',
            'difficulty': 1
        },
        {
            'question': 'In which mountain range would you find K2?',
            'options': ['Himalayas', 'Andes', 'Alps', 'Rockies'],
            'correct': 'Himalayas',
            'difficulty': 2
        }
    ]
}