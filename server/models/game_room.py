"""Game room model."""
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

from server.config.game_config import GAME_CONFIG, GAME_TOPICS
from server.config.questions import TRIVIA_QUESTIONS, CHASE_QUESTIONS
from server.database import get_db, User, Achievement

class GameRoom:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: Dict[str, Dict[str, Any]] = {}  # {sid: {'name': str, 'user_id': int, 'profile': str, 'is_host': bool}}
        self.host_sid: Optional[str] = None
        self.game_state = 'waiting'
        self.current_game: Optional[str] = None
        self.drawings: List[Dict[str, Any]] = []
        self.current_word: Optional[str] = None
        self.round = 0
        self.total_rounds = GAME_CONFIG['rounds_per_game']
        self.scores: Dict[str, int] = {}
        self.topic: Optional[str] = None
        self.player_order: List[str] = []
        self.current_player_index = 0
        self.round_start_time: Optional[datetime] = None
        self.timer_task = None
        self.used_words = set()
        self.used_questions = set()
        self.current_question = None
        self.player_answers: Dict[str, Any] = {}
        self.round_scores: Dict[str, int] = {}
        self.db = next(get_db())

        # Chase game specific attributes
        self.chaser: Optional[str] = None
        self.chase_category: Optional[str] = None
        self.chase_position = 0
        self.chase_questions: List[Dict[str, Any]] = []
        self.chase_contestant: Optional[str] = None
        self.chase_scores: Dict[str, int] = {}

    def reset_round(self) -> None:
        """Reset the round state."""
        self.drawings = []
        self.current_word = None
        self.player_answers = {}
        self.round_scores = {}
        self.round_start_time = datetime.now()

    def get_next_word(self) -> str:
        """Get the next word for the drawing game."""
        available_words = []
        for words in GAME_TOPICS.values():
            available_words.extend([w for w in words if w not in self.used_words])
        if not available_words:
            self.used_words.clear()
            available_words = [w for topic in GAME_TOPICS.values() for w in topic]
        word = random.choice(available_words)
        self.used_words.add(word)
        return word

    def get_next_question(self) -> Dict[str, Any]:
        """Get the next question for trivia game."""
        available_questions = [q for q in TRIVIA_QUESTIONS if q not in self.used_questions]
        if not available_questions:
            self.used_questions.clear()
            available_questions = TRIVIA_QUESTIONS
        question = random.choice(available_questions)
        self.used_questions.add(question)
        return question

    def calculate_score(self, player_id: str, is_correct: bool, answer_time: Optional[float] = None) -> int:
        """Calculate score for a player's answer."""
        base_score = 0
        if is_correct:
            if self.current_game == 'chinese_whispers':
                base_score = GAME_CONFIG['points']['correct_guess']
            else:  # trivia
                base_score = GAME_CONFIG['points']['correct_trivia']
                if answer_time and answer_time < 5:  # Fast answer bonus
                    base_score += GAME_CONFIG['points']['fast_answer_bonus']
        elif self.current_game == 'chinese_whispers':
            # Check for partial matches
            guess = self.player_answers[player_id].lower()
            target = self.current_word.lower()
            if len(set(guess.split()) & set(target.split())) > 0:
                base_score = GAME_CONFIG['points']['partial_guess']

        self.scores[player_id] = self.scores.get(player_id, 0) + base_score
        self.round_scores[player_id] = base_score
        return base_score

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """Get the current leaderboard."""
        return sorted(
            [{'name': self.players[pid]['name'], 'score': score}
             for pid, score in self.scores.items() if not self.players[pid].get('is_host', False)],
            key=lambda x: x['score'],
            reverse=True
        )

    def start_chase_game(self, chaser_sid: str, category: str) -> None:
        """Initialize a new chase game."""
        if category not in CHASE_QUESTIONS:
            raise ValueError(f"Invalid category: {category}")

        self.current_game = 'chase'
        self.game_state = 'chase_setup'
        self.chaser = chaser_sid
        self.chase_category = category
        self.chase_position = 0
        self.chase_contestant = None
        self.chase_questions = []

        # Select questions for this chase game
        available_questions = CHASE_QUESTIONS[category]
        easy_questions = [q for q in available_questions if q['difficulty'] == 1]
        hard_questions = [q for q in available_questions if q['difficulty'] == 2]

        # Mix questions to create a balanced set
        self.chase_questions = (
            random.sample(easy_questions, min(3, len(easy_questions))) +
            random.sample(hard_questions, min(2, len(hard_questions)))
        )
        random.shuffle(self.chase_questions)

    def select_chase_contestant(self, contestant_sid: str) -> Dict[str, Any]:
        """Select the next contestant for the chase."""
        if contestant_sid not in self.players or contestant_sid == self.chaser:
            raise ValueError("Invalid contestant")

        self.chase_contestant = contestant_sid
        self.chase_position = 0
        self.game_state = 'chase_question'
        return self.chase_questions[0]

    def process_chase_answer(self, player_sid: str, answer: str) -> Dict[str, Any]:
        """Process an answer in the chase game."""
        current_question = self.chase_questions[0]
        is_correct = answer == current_question['correct']
        is_contestant = player_sid == self.chase_contestant

        result = {
            'is_correct': is_correct,
            'correct_answer': current_question['correct'],
            'player_type': 'contestant' if is_contestant else 'chaser',
            'position_change': 0
        }

        if is_contestant and is_correct:
            self.chase_position += 1
            result['position_change'] = 1
        elif not is_contestant and is_correct:  # Chaser
            self.chase_position -= 1
            result['position_change'] = -1

        # Check if chase is over
        if self.chase_position >= GAME_CONFIG['chase_board_size']:
            result['game_over'] = True
            result['winner'] = 'contestant'
            self.scores[self.chase_contestant] = self.scores.get(self.chase_contestant, 0) + GAME_CONFIG['chase_win']
        elif self.chase_position <= -1:
            result['game_over'] = True
            result['winner'] = 'chaser'
            self.scores[self.chaser] = self.scores.get(self.chaser, 0) + GAME_CONFIG['chase_catch']
        else:
            # Move to next question
            self.chase_questions.pop(0)
            if self.chase_questions:
                result['next_question'] = self.chase_questions[0]
            else:
                result['game_over'] = True
                result['winner'] = 'contestant' if self.chase_position > 0 else 'chaser'
                if result['winner'] == 'contestant':
                    self.scores[self.chase_contestant] = self.scores.get(self.chase_contestant, 0) + GAME_CONFIG['chase_win']
                else:
                    self.scores[self.chaser] = self.scores.get(self.chaser, 0) + GAME_CONFIG['chase_catch']

        return result

    def is_round_complete(self) -> bool:
        """Check if the current round is complete."""
        if self.current_game == 'chinese_whispers':
            return len(self.drawings) >= len(self.players)
        else:  # trivia
            return len(self.player_answers) >= len(self.players)

    def advance_round(self) -> None:
        """Advance to the next round."""
        self.round += 1
        self.reset_round()
        if self.current_game == 'chinese_whispers':
            random.shuffle(self.player_order)
            self.current_player_index = 0
            self.current_word = self.get_next_word()
        else:  # trivia
            self.current_question = self.get_next_question()

    def is_game_complete(self) -> bool:
        """Check if the game is complete."""
        return self.round >= self.total_rounds