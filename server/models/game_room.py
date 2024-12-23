"""Game room model with enhanced features for better user experience."""
import random
import time
import io
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from server.config.game_config import GAME_CONFIG, GAME_TOPICS, MUSIC_CONFIG
from server.config.questions import TRIVIA_QUESTIONS, CHASE_QUESTIONS
from server.database import get_db, User, Achievement

class GameError(Exception):
    """Custom game error class for better error handling."""
    pass

class GameRoom:
    def __init__(self, room_id: str):
        # Basic room attributes with enhanced security and profiles
        self.room_id = room_id
        self.players: Dict[str, Dict[str, Any]] = {}  # {sid: {'name': str, 'user_id': int, 'profile_picture': str, 'is_host': bool, 'last_action': datetime, 'stats': Dict}}
        self.host_sid: Optional[str] = None
        self.game_state = 'waiting'
        self.current_game: Optional[str] = None
        self.state_history: List[Dict[str, Any]] = []  # For state recovery
        self.last_state_update = datetime.now()
        
        # Player profiles and stats
        self.player_stats: Dict[str, Dict[str, Any]] = {}  # Persistent player statistics
        self.profile_cache: Dict[str, str] = {}  # Cache for profile pictures
        self.achievements: Dict[str, List[str]] = {}  # Player achievements
        
        # Enhanced game progress tracking
        self.round = 0
        self.total_rounds = GAME_CONFIG['rounds_per_game']
        self.difficulty_level = 'easy'  # Dynamic difficulty adjustment
        self.current_word: Optional[str] = None
        self.current_question = None
        self.topic: Optional[str] = None
        self.round_start_time: Optional[datetime] = None
        self.state_lock = False  # Prevent race conditions
        
        # Player management
        self.player_order: List[str] = []
        self.current_player_index = 0
        self.player_answers: Dict[str, Any] = {}
        self.player_streaks: Dict[str, int] = {}  # Track correct answer streaks
        self.player_skips: Dict[str, int] = {}  # Track consecutive skips
        
        # Scoring system
        self.scores: Dict[str, int] = {}
        self.round_scores: Dict[str, int] = {}
        self.perfect_rounds: Dict[str, int] = {}  # Track perfect rounds per player
        
        # Time management
        self.round_start_time: Optional[datetime] = None
        self.timer_task = None
        self.last_activity_time = datetime.now()
        self.afk_warnings: Dict[str, bool] = {}  # Track AFK warnings per player
        
        # Enhanced content management
        self.used_words = set()
        self.used_questions = set()
        self.drawings: List[Dict[str, Any]] = []
        self.drawing_state = {
            'current_chain': [],  # Track drawing progression
            'hints_used': set(),  # Track used hints
            'time_extensions': 2,  # Number of time extensions available
            'tools': {
                'brush_sizes': [2, 5, 10, 20],
                'colors': ['#000000', '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF'],
                'special_tools': {
                    'eraser': True,
                    'fill': True,
                    'undo': True,
                    'shapes': ['circle', 'rectangle', 'line']
                }
            },
            'canvas_history': [],  # For undo/redo
            'reactions': {  # Player reactions to drawings
                'likes': {},
                'laughs': {},
                'wows': {}
            }
        }
        
        # Performance optimization
        self.cache = {
            'leaderboard': None,
            'leaderboard_timestamp': None,
            'available_words': None,
            'word_cache_round': None
        }
        
        # Database connection
        self.db = next(get_db())
        
        # Enhanced chase game attributes
        self.chaser: Optional[str] = None
        self.chase_category: Optional[str] = None
        self.chase_position = 0
        self.chase_questions: List[Dict[str, Any]] = []
        self.chase_contestant: Optional[str] = None
        self.chase_scores: Dict[str, int] = {}
        self.chase_state = {
            'board_size': GAME_CONFIG['chase_board_size'],
            'chaser_position': 0,
            'contestant_position': 0,
            'safe_positions': [],  # Positions where contestants are safe
            'current_prize': 0,
            'offer_high': 0,  # Higher offer with less steps to safety
            'offer_low': 0,   # Lower offer with more steps to safety
            'time_pressure': False,  # Activates when chaser is close
            'power_ups': {  # Special abilities for contestants
                'double_steps': 1,  # Move two steps on correct answer
                'shield': 1,     # Block one chaser advance
                'time_freeze': 1 # Extra time for one question
            }
        }
        
        # Music state
        self.current_music: Optional[str] = 'lobby'
        self.music_fade_task = None

    def reset_round(self) -> None:
        """Reset the round state with enhanced cleanup."""
        self.drawings = []
        self.current_word = None
        self.player_answers = {}
        self.round_scores = {}
        self.round_start_time = datetime.now()
        self.last_activity_time = datetime.now()
        
        # Clear AFK warnings at round start
        self.afk_warnings = {sid: False for sid in self.players}
        
        # Update difficulty based on round progress
        total_rounds = self.total_rounds
        if self.round < total_rounds * 0.3:
            self.difficulty_level = 'easy'
        elif self.round < total_rounds * 0.7:
            self.difficulty_level = 'medium'
        else:
            self.difficulty_level = 'hard'
            
        # Clear performance caches
        self.cache['leaderboard'] = None
        self.cache['available_words'] = None
        self.cache['word_cache_round'] = None

    def get_next_word(self) -> str:
        """Get the next word with progressive difficulty."""
        # Check cache first
        if (self.cache['available_words'] is not None and 
            self.cache['word_cache_round'] == self.round):
            available_words = self.cache['available_words']
        else:
            available_words = []
            # Get words based on current difficulty
            for topic_words in GAME_TOPICS.values():
                words = topic_words[self.difficulty_level]
                available_words.extend([w for w in words if w not in self.used_words])
                
            # If no words available in current difficulty, include easier ones
            if not available_words and self.difficulty_level != 'easy':
                if self.difficulty_level == 'hard':
                    # Try medium words
                    for topic_words in GAME_TOPICS.values():
                        words = topic_words['medium']
                        available_words.extend([w for w in words if w not in self.used_words])
                
                # If still no words, try easy words
                if not available_words:
                    for topic_words in GAME_TOPICS.values():
                        words = topic_words['easy']
                        available_words.extend([w for w in words if w not in self.used_words])
            
            # If still no words, reset used words
            if not available_words:
                self.used_words.clear()
                for topic_words in GAME_TOPICS.values():
                    words = topic_words[self.difficulty_level]
                    available_words.extend(words)
            
            # Update cache
            self.cache['available_words'] = available_words
            self.cache['word_cache_round'] = self.round
        
        word = random.choice(available_words)
        self.used_words.add(word)
        
        # Update cache
        self.cache['available_words'] = [w for w in available_words if w != word]
        return word

    def get_next_question(self) -> Dict[str, Any]:
        """Get the next question for trivia game."""
        # Track questions by their text to avoid unhashable dict issue
        used_questions = {q['question'] for q in TRIVIA_QUESTIONS if q['question'] in self.used_questions}
        available_questions = [q for q in TRIVIA_QUESTIONS if q['question'] not in used_questions]
        
        if not available_questions:
            self.used_questions.clear()
            available_questions = TRIVIA_QUESTIONS
            
        question = random.choice(available_questions)
        self.used_questions.add(question['question'])  # Store just the question text
        return question

    def add_player(self, sid: str, name: str, profile_picture: str = None, is_host: bool = False) -> None:
        """Add a player with profile picture and initialize their stats."""
        # Initialize player stats
        initial_stats = {
            'games_played': 0,
            'wins': 0,
            'perfect_rounds': 0,
            'total_score': 0,
            'best_streak': 0,
            'favorite_game': None,
            'achievements': [],
            'last_played': datetime.now()
        }

        # Process profile picture
        if profile_picture:
            # Cache the profile picture
            self.profile_cache[sid] = profile_picture
        else:
            # Generate default profile picture if none provided
            self.profile_cache[sid] = self._generate_default_profile(name[0].upper())

        # Add player to room
        self.players[sid] = {
            'name': name,
            'profile_picture': self.profile_cache[sid],
            'is_host': is_host,
            'last_action': datetime.now(),
            'stats': initial_stats.copy()
        }

        # Load persistent stats if available
        if sid in self.player_stats:
            self.players[sid]['stats'].update(self.player_stats[sid])

    def update_player_stats(self, sid: str, game_result: Dict[str, Any]) -> None:
        """Update player statistics after a game."""
        if sid not in self.players:
            return

        stats = self.players[sid]['stats']
        stats['games_played'] += 1
        stats['total_score'] += game_result.get('score', 0)
        
        if game_result.get('is_winner'):
            stats['wins'] += 1
        
        if game_result.get('perfect_round'):
            stats['perfect_rounds'] += 1
        
        current_streak = game_result.get('streak', 0)
        if current_streak > stats['best_streak']:
            stats['best_streak'] = current_streak
        
        # Update favorite game
        game_type = self.current_game
        if game_type:
            if 'game_counts' not in stats:
                stats['game_counts'] = {}
            stats['game_counts'][game_type] = stats['game_counts'].get(game_type, 0) + 1
            
            # Update favorite game based on most played
            stats['favorite_game'] = max(stats['game_counts'].items(), key=lambda x: x[1])[0]
        
        stats['last_played'] = datetime.now()
        
        # Save to persistent storage
        self.player_stats[sid] = stats.copy()

    def get_player_profile(self, sid: str) -> Dict[str, Any]:
        """Get player profile with stats and achievements."""
        if sid not in self.players:
            return None

        player = self.players[sid]
        return {
            'name': player['name'],
            'profile_picture': player['profile_picture'],
            'stats': player['stats'],
            'achievements': self.achievements.get(sid, []),
            'rank': self._calculate_player_rank(sid)
        }

    def _calculate_player_rank(self, sid: str) -> str:
        """Calculate player rank based on performance."""
        if sid not in self.players:
            return 'Novice'

        stats = self.players[sid]['stats']
        score = (
            stats['wins'] * 100 +
            stats['perfect_rounds'] * 50 +
            stats['best_streak'] * 10 +
            stats['total_score'] // 1000
        )

        if score >= 1000:
            return 'Legend'
        elif score >= 500:
            return 'Master'
        elif score >= 250:
            return 'Expert'
        elif score >= 100:
            return 'Veteran'
        else:
            return 'Novice'

    def _generate_default_profile(self, letter: str) -> str:
        """Generate a default profile picture with the first letter."""
        import io
        from PIL import Image, ImageDraw, ImageFont
        import base64

        # Create a new image with a random background color
        img = Image.new('RGB', (128, 128), self._get_random_color())
        draw = ImageDraw.Draw(img)

        # Load a font (using default font as fallback)
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 64)
        except:
            font = ImageFont.load_default()

        # Calculate text position
        text_width = draw.textlength(letter, font=font)
        text_height = 64  # Approximate height
        x = (128 - text_width) // 2
        y = (128 - text_height) // 2

        # Draw the letter
        draw.text((x, y), letter, fill='white', font=font)

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

    def _get_random_color(self) -> tuple:
        """Generate a random pastel color."""
        import random
        return (
            random.randint(100, 200),
            random.randint(100, 200),
            random.randint(100, 200)
        )

    def calculate_score(self, player_id: str, is_correct: bool, answer_time: Optional[float] = None) -> Dict[str, Any]:
        """Calculate score with enhanced mechanics, bonuses, and achievements."""
        result = {
            'base_score': 0,
            'streak_bonus': 0,
            'time_bonus': 0,
            'comeback_bonus': 0,
            'difficulty_bonus': 0,
            'participation_bonus': GAME_CONFIG['points']['participation_bonus'],
            'total_score': 0,
            'achievements': []
        }
        
        # Apply difficulty multiplier
        difficulty_multipliers = {
            'easy': 1.0,
            'medium': 1.5,
            'hard': 2.0
        }
        
        # Update activity timestamp
        self.last_activity_time = datetime.now()
        self.afk_warnings[player_id] = False
        
        if is_correct:
            # Base score based on game type
            if self.current_game == 'chinese_whispers':
                result['base_score'] = GAME_CONFIG['points']['correct_guess']
            else:  # trivia
                result['base_score'] = GAME_CONFIG['points']['correct_trivia']
            
            # Streak bonus
            self.player_streaks[player_id] = self.player_streaks.get(player_id, 0) + 1
            streak = self.player_streaks[player_id]
            if streak > 1:
                streak_multiplier = min(streak * GAME_CONFIG['points']['streak_multiplier'], 0.5)
                result['streak_bonus'] = int(result['base_score'] * streak_multiplier)
            
            # Time bonus for quick answers
            if answer_time is not None:
                max_time = GAME_CONFIG['trivia_time'] if self.current_game == 'trivia' else GAME_CONFIG['guess_time']
                time_factor = max(0, (max_time - answer_time) / max_time)
                result['time_bonus'] = int(GAME_CONFIG['points']['fast_answer_bonus'] * time_factor)
            
            # Reset skip counter on correct answer
            self.player_skips[player_id] = 0
            
        else:
            # Reset streak on wrong answer
            self.player_streaks[player_id] = 0
            
            if self.current_game == 'chinese_whispers':
                # Enhanced partial matching
                guess = self.player_answers[player_id].lower()
                target = self.current_word.lower()
                common_words = set(guess.split()) & set(target.split())
                if common_words:
                    result['base_score'] = GAME_CONFIG['points']['partial_guess'] * len(common_words)
            
            # Increment skip counter
            self.player_skips[player_id] = self.player_skips.get(player_id, 0) + 1
            
            # Check for excessive skipping
            if self.player_skips[player_id] >= GAME_CONFIG['max_consecutive_skips']:
                result['participation_bonus'] = 0
        
        # Comeback bonus for trailing players
        leaderboard = self.get_leaderboard()
        if len(leaderboard) > 1:
            max_score = leaderboard[0]['score']
            player_score = self.scores.get(player_id, 0)
            if player_score < max_score * 0.5:  # Significantly behind
                result['comeback_bonus'] = GAME_CONFIG['points']['comeback_bonus']
        
        # Calculate total score
        result['total_score'] = (
            result['base_score'] +
            result['streak_bonus'] +
            result['time_bonus'] +
            result['comeback_bonus'] +
            result['participation_bonus']
        )
        
        # Update player scores
        self.scores[player_id] = self.scores.get(player_id, 0) + result['total_score']
        self.round_scores[player_id] = result['total_score']
        
        return result

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """Get cached leaderboard with enhanced player stats."""
        current_time = datetime.now()
        if (self.cache['leaderboard'] is None or
            self.cache['leaderboard_timestamp'] is None or
            (current_time - self.cache['leaderboard_timestamp']).seconds > 2):
            
            leaderboard = []
            for pid, score in self.scores.items():
                if not self.players[pid].get('is_host', False):
                    player_data = {
                        'name': self.players[pid]['name'],
                        'score': score,
                        'streak': self.player_streaks.get(pid, 0),
                        'perfect_rounds': self.perfect_rounds.get(pid, 0),
                        'rank_change': 0  # Will be calculated below
                    }
                    leaderboard.append(player_data)
            
            # Sort by score
            leaderboard.sort(key=lambda x: x['score'], reverse=True)
            
            # Calculate rank changes if we have previous leaderboard
            if self.cache['leaderboard']:
                old_ranks = {player['name']: idx for idx, player in enumerate(self.cache['leaderboard'])}
                for idx, player in enumerate(leaderboard):
                    if player['name'] in old_ranks:
                        player['rank_change'] = old_ranks[player['name']] - idx
            
            self.cache['leaderboard'] = leaderboard
            self.cache['leaderboard_timestamp'] = current_time
        
        return self.cache['leaderboard']

    def update_difficulty(self) -> None:
        """Update game difficulty based on player performance."""
        avg_score = sum(self.round_scores.values()) / len(self.round_scores) if self.round_scores else 0
        max_possible = GAME_CONFIG['points']['correct_guess'] + GAME_CONFIG['points']['fast_answer_bonus']
        
        if avg_score > max_possible * 0.8:  # Players doing very well
            self.difficulty_level = 'hard'
        elif avg_score > max_possible * 0.5:  # Players doing okay
            self.difficulty_level = 'medium'
        else:  # Players struggling
            self.difficulty_level = 'easy'

    def shuffle_player_order_with_catchup(self) -> None:
        """Shuffle player order with catch-up mechanic for trailing players."""
        # Sort players by score
        sorted_players = sorted(
            [(pid, self.scores.get(pid, 0)) for pid in self.players if not self.players[pid].get('is_host', False)],
            key=lambda x: x[1]
        )
        
        # Give trailing players better positions
        if len(sorted_players) > 2:
            # Put the lowest scoring player in a good position
            lowest_scorer = sorted_players[0][0]
            others = [p[0] for p in sorted_players[1:]]
            random.shuffle(others)
            # Position the lowest scorer in the first half of the round
            insert_pos = random.randint(0, len(others) // 2)
            others.insert(insert_pos, lowest_scorer)
            self.player_order = others
        else:
            # For 2 or fewer players, just shuffle
            self.player_order = [p[0] for p in sorted_players]
            random.shuffle(self.player_order)

    def advance_round(self) -> None:
        """Advance to the next round with enhanced progression."""
        self.round += 1
        
        # Check for perfect round achievements
        for pid, score in self.round_scores.items():
            if score > 0 and not any(
                ans.get('is_wrong', True) 
                for ans in self.player_answers.values() 
                if ans.get('player_id') == pid
            ):
                self.perfect_rounds[pid] = self.perfect_rounds.get(pid, 0) + 1
                # Award perfect round bonus
                self.scores[pid] = self.scores.get(pid, 0) + GAME_CONFIG['points']['perfect_round']
        
        # Reset round state
        self.reset_round()
        
        # Update game difficulty
        if GAME_CONFIG['difficulty_scaling']['enabled']:
            self.update_difficulty()
        
        # Set up next round content
        if self.current_game == 'chinese_whispers':
            # Shuffle player order with catch-up mechanic
            self.shuffle_player_order_with_catchup()
            self.current_player_index = 0
            self.current_word = self.get_next_word()
        else:  # trivia
            self.current_question = self.get_next_question()
        
        # Trigger round transition music
        self.change_music('round_transition', fade=True)

    def is_game_complete(self) -> bool:
        """Check if the game is complete and handle end-game events."""
        if self.round >= self.total_rounds:
            # Award achievements
            self.award_end_game_achievements()
            # Change to game over music
            self.change_music('game_over', fade=True)
            return True
        return False

    def award_end_game_achievements(self) -> None:
        """Award achievements at the end of the game."""
        leaderboard = self.get_leaderboard()
        if leaderboard:
            # Award winner achievement
            winner = leaderboard[0]
            winner_id = next(
                pid for pid, data in self.players.items()
                if data['name'] == winner['name']
            )
            user = self.db.query(User).filter_by(id=self.players[winner_id]['user_id']).first()
            if user:
                achievement = Achievement(
                    user_id=user.id,
                    name='game_winner',
                    description=f'Won a game with {winner["score"]} points!'
                )
                self.db.add(achievement)
                
                # Perfect game achievement
                if self.perfect_rounds.get(winner_id, 0) == self.total_rounds:
                    achievement = Achievement(
                        user_id=user.id,
                        name='perfect_game',
                        description='Completed a game with all perfect rounds!'
                    )
                    self.db.add(achievement)
                
                self.db.commit()

    def change_music(self, music_type: str, fade: bool = False) -> None:
        """Change background music with optional fade effect."""
        if music_type in MUSIC_CONFIG:
            self.current_music = music_type

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

    def validate_game_state(self) -> None:
        """Validate and maintain game state consistency."""
        if self.game_state not in ['waiting', 'playing', 'chase_setup', 'chase_question']:
            self.game_state = 'waiting'
            
        if self.current_game and self.game_state == 'waiting':
            self.current_game = None
            
        if self.round > self.total_rounds:
            self.game_state = 'complete'
            
        # Validate player states
        for pid in list(self.players.keys()):
            if pid not in self.scores:
                self.scores[pid] = 0
            if pid not in self.player_streaks:
                self.player_streaks[pid] = 0
            if pid not in self.player_skips:
                self.player_skips[pid] = 0
            if pid not in self.perfect_rounds:
                self.perfect_rounds[pid] = 0

    def check_afk_players(self) -> List[str]:
        """Check for AFK players and return list of inactive players."""
        current_time = datetime.now()
        afk_players = []
        
        for pid in self.players:
            if (current_time - self.last_activity_time).seconds > GAME_CONFIG['idle_timeout']:
                if not self.afk_warnings.get(pid, False):
                    self.afk_warnings[pid] = True
                    afk_players.append(pid)
                    
        return afk_players

    def validate_game_action(self, player_sid: str, action_type: str) -> None:
        """Validate game actions and maintain game integrity."""
        if player_sid not in self.players:
            raise GameError("Player not found in room")
        
        if self.game_state == 'waiting':
            raise GameError("Game hasn't started yet")
            
        if action_type == 'draw' and self.current_game != 'chinese_whispers':
            raise GameError("Invalid action for current game mode")
            
        if self.game_status['is_paused']:
            raise GameError("Game is currently paused")
            
        # Update activity timestamp
        self.last_activity_time = datetime.now()
        self.afk_warnings[player_sid] = False

    def is_round_complete(self) -> bool:
        """Check if the current round is complete with enhanced validation."""
        # Validate game state first
        self.validate_game_state()
        
        if self.current_game == 'chinese_whispers':
            all_drawn = len(self.drawings) >= len(self.players)
            all_active = all(
                (datetime.now() - self.last_activity_time).seconds < GAME_CONFIG['idle_timeout']
                for pid in self.players
            )
            return all_drawn or not all_active
        else:  # trivia
            all_answered = len(self.player_answers) >= len(self.players)
            time_limit_reached = (
                self.round_start_time and 
                (datetime.now() - self.round_start_time).seconds >= GAME_CONFIG['trivia_time']
            )
            return all_answered or time_limit_reached

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