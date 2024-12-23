"""Socket events module."""
import base64
import random
from datetime import datetime
from typing import Dict, Optional

import socketio

from ..models.game_room import GameRoom, GameError
from ..database import User, Achievement
from ..config.game_config import GAME_CONFIG, MUSIC_CONFIG
from ..config.questions import CHASE_QUESTIONS

def register_socket_events(sio: socketio.AsyncServer, rooms: Dict[str, GameRoom]):
    """Register all socket events."""

    @sio.event
    async def connect(sid, environ):
        """Handle client connection."""
        print(f"Client connected: {sid}")
        print(f"Connection details: {environ.get('QUERY_STRING', '')}")
        
        # Get room_id from query string if available
        room_id = None
        query = environ.get('QUERY_STRING', '')
        if 'room_id=' in query:
            room_id = query.split('room_id=')[1].split('&')[0]
            print(f"Client attempting to connect to room: {room_id}")
            
            # Validate room exists
            if room_id not in rooms:
                print(f"Warning: Room {room_id} not found")
                # We'll let the client connect but inform them about the room status
                await sio.emit('room_status', {
                    'exists': False,
                    'message': 'Room not found or expired'
                }, room=sid)

    @sio.event
    async def join_room(sid, data):
        """Handle player joining a room."""
        try:
            room_id = data['room_id']
            is_host = data.get('is_host', False)
            player_name = 'Host' if is_host else data['player_name']
            profile_picture = data.get('profile_picture')

            print(f"Join room request: {data}")

            # Validate room exists
            if room_id not in rooms:
                print(f"Error: Room {room_id} not found")
                await sio.emit('join_error', {
                    'message': 'Room not found or has expired. Please scan the QR code again.'
                }, room=sid)
                return

            room = rooms[room_id]

            if is_host:
                if room.host_sid:
                    # Remove old host
                    if room.host_sid in room.players:
                        del room.players[room.host_sid]
                        await sio.leave_room(room.host_sid, room_id)
                room.host_sid = sid
                room.players[sid] = {
                    'name': 'Host',
                    'is_host': True,
                    'connected': True
                }
                await sio.enter_room(sid, room_id)
                await sio.emit('join_success', {
                    'player_name': 'Host',
                    'room_id': room_id,
                    'is_host': True
                }, room=sid)
                return

            # Check if username is taken by an active player
            for s, p in room.players.items():
                if not p.get('is_host') and p['name'] == player_name and p['connected']:
                    await sio.emit('join_error', {
                        'message': 'Username already taken'
                    }, room=sid)
                    return

            # Check if it's a rejoin case
            existing_sid = None
            for s, p in room.players.items():
                if not p.get('is_host') and p['name'] == player_name and not p['connected']:
                    existing_sid = s
                    break

            if existing_sid:
                # Remove old connection
                if existing_sid in room.players:
                    del room.players[existing_sid]
                    await sio.leave_room(existing_sid, room_id)

            # Check if username exists or create new user
            user = room.db.query(User).filter(User.username == player_name).first()
            if not user:
                user = User(username=player_name)
                room.db.add(user)
                room.db.commit()

            if profile_picture:
                try:
                    image_data = base64.b64decode(profile_picture.split(',')[1])
                    user.profile_picture = image_data
                    room.db.commit()
                except Exception as e:
                    print(f"Error processing profile picture: {e}")

            room.db.refresh(user)

            # Store user info in room
            room.players[sid] = {
                'name': player_name,
                'user_id': user.id,
                'profile': profile_picture or '',
                'score': 0,
                'connected': True,
                'is_host': False
            }

            await sio.enter_room(sid, room_id)

            # Send current game state to rejoining player
            if room.game_state != 'waiting':
                state_data = {
                    'state': room.game_state,
                    'game_type': room.current_game,
                    'round': room.round,
                    'total_rounds': room.total_rounds,
                }

                if room.current_game == 'chinese_whispers':
                    state_data.update({
                        'current_word': room.current_word,
                        'is_your_turn': room.player_order[room.current_player_index] == sid
                    })
                elif room.current_game == 'trivia':
                    state_data['current_question'] = room.current_question
                elif room.current_game == 'chase':
                    state_data.update({
                        'chase_category': room.chase_category,
                        'chase_position': room.chase_position,
                        'is_chaser': room.chaser == sid,
                        'is_contestant': room.chase_contestant == sid,
                        'current_question': room.chase_questions[0] if room.chase_questions else None
                    })

                await sio.emit('game_state', state_data, room=sid)

            # Update all clients with new player list
            player_list = []
            for player_sid, player_data in room.players.items():
                if player_data['connected'] and not player_data.get('is_host'):
                    player_list.append({
                        'name': player_data['name'],
                        'score': player_data.get('score', 0)
                    })

            # Send join confirmation to the player
            await sio.emit('join_confirmed', {
                'player_name': player_name,
                'room_id': room_id,
                'is_host': False,
                'current_players': player_list
            }, room=sid)

            # Notify other players
            await sio.emit('player_joined', {
                'players': player_list,
                'new_player': player_name
            }, room=room_id)

            print(f"Player {player_name} successfully joined room {room_id}")

        except Exception as e:
            print(f"Error joining room: {e}")
            await sio.emit('join_error', {
                'message': f"Failed to join room: {str(e)}"
            }, room=sid)

    @sio.event
    async def disconnect(sid):
        """Handle client disconnection."""
        print(f"Client disconnected: {sid}")
        for room in rooms.values():
            if sid in room.players:
                player_data = room.players[sid]
                # Mark player as disconnected instead of removing
                player_data['connected'] = False

                # Handle special cases based on game state
                if room.current_game == 'chase':
                    if sid == room.chaser:
                        # Chaser disconnected, reset chase game
                        room.chaser = None
                        room.chase_category = None
                        room.chase_contestant = None
                        room.game_state = 'waiting'
                        await sio.emit('chase_cancelled', {
                            'reason': 'Chaser disconnected'
                        }, room=room.room_id)
                    elif sid == room.chase_contestant:
                        # Contestant disconnected, reset current chase
                        room.chase_contestant = None
                        room.game_state = 'chase_setup'
                        await sio.emit('chase_cancelled', {
                            'reason': 'Contestant disconnected'
                        }, room=room.room_id)

                # Update player list for all clients
                player_list = []
                for p_sid, p_data in room.players.items():
                    if p_data['connected'] and not p_data.get('is_host'):
                        player_list.append({
                            'name': p_data['name'],
                            'score': p_data.get('score', 0)
                        })

                await sio.emit('player_left', {
                    'players': player_list,
                    'disconnected_player': player_data['name']
                }, room=room.room_id)

                # If not enough players, end the game
                active_players = sum(1 for p in room.players.values()
                                    if p['connected'] and not p.get('is_host'))
                if active_players < 2:  # Minimum 2 players for any game
                    room.game_state = 'waiting'
                    room.current_game = None
                    await sio.emit('game_cancelled', {
                        'reason': 'Not enough players'
                    }, room=room.room_id)

                # If it was this player's turn in drawing game, move to next player
                if (room.game_state == 'playing' and
                        room.current_game == 'chinese_whispers' and
                        room.player_order[room.current_player_index] == sid):
                    room.current_player_index = (room.current_player_index + 1) % len(room.player_order)
                    next_player_id = room.player_order[room.current_player_index]

                    # Skip disconnected players
                    while not room.players[next_player_id]['connected']:
                        room.current_player_index = (room.current_player_index + 1) % len(room.player_order)
                        next_player_id = room.player_order[room.current_player_index]

                    await sio.emit('next_player', {
                        'player': room.players[next_player_id]['name'],
                        'skipped_disconnected': True
                    }, room=room.room_id)

    @sio.event
    async def start_game(sid, data):
        """Handle game start request from host."""
        try:
            room_id = data['room_id']
            game_type = data['game_type']

            if room_id not in rooms:
                await sio.emit('game_error', {
                    'message': 'Room not found'
                }, room=sid)
                return

            room = rooms[room_id]

            # Verify sender is host
            if sid != room.host_sid:
                await sio.emit('game_error', {
                    'message': 'Only the host can start the game'
                }, room=sid)
                return

            # Check minimum player count
            active_players = sum(1 for p in room.players.values()
                               if p['connected'] and not p.get('is_host'))
            min_players = GAME_CONFIG['game_modes'][game_type]['min_players']
            
            if active_players < min_players:
                await sio.emit('game_error', {
                    'message': f'Need at least {min_players} players to start {game_type}'
                }, room=sid)
                return

            # Initialize game state
            room.current_game = game_type
            room.game_state = 'playing'
            room.round = 1
            room.scores = {sid: 0 for sid, player in room.players.items() if not player.get('is_host')}
            room.round_start_time = datetime.now()

            # Set up game-specific state
            if game_type == 'chinese_whispers':
                try:
                    # Create player order (excluding host)
                    room.player_order = [sid for sid, player in room.players.items() 
                                       if player['connected'] and not player.get('is_host')]
                    random.shuffle(room.player_order)
                    room.current_player_index = 0
                    room.current_word = room.get_next_word()
                    room.drawings = []  # Clear previous drawings
                    
                    # Send initial state to all players
                    for player_sid in room.players:
                        if not room.players[player_sid].get('is_host'):
                            is_drawer = player_sid == room.player_order[0]
                            await sio.emit('game_started', {
                                'game_type': 'chinese_whispers',
                                'round': 1,
                                'total_rounds': room.total_rounds,
                                'is_drawer': is_drawer,
                                'word': room.current_word if is_drawer else None,
                                'time_limit': GAME_CONFIG['time_limits']['drawing'][
                                    '2-3' if active_players <= 3 else '4-6' if active_players <= 6 else '7+'
                                ]
                            }, room=player_sid)
                    
                    print(f"Chinese Whispers game started with word: {room.current_word}")
                    print(f"Player order: {[room.players[pid]['name'] for pid in room.player_order]}")
                except Exception as e:
                    print(f"Error initializing Chinese Whispers: {e}")
                    raise

            elif game_type == 'trivia':
                room.current_question = room.get_next_question()
                room.player_answers = {}
                
                # Send initial state to all players
                await sio.emit('game_started', {
                    'game_type': 'trivia',
                    'round': 1,
                    'total_rounds': room.total_rounds,
                    'question': room.current_question,
                    'time_limit': GAME_CONFIG['time_limits']['trivia'][
                        '2-3' if active_players <= 3 else '4-6' if active_players <= 6 else '7+'
                    ]
                }, room=room_id)

            elif game_type == 'chase':
                # Select random chaser
                non_host_players = [sid for sid, player in room.players.items() 
                                  if player['connected'] and not player.get('is_host')]
                room.chaser = random.choice(non_host_players)
                # Select random category from available chase questions
                room.chase_category = random.choice(list(CHASE_QUESTIONS.keys()))
                room.chase_position = 0
                # Get initial questions for the category
                room.chase_questions = CHASE_QUESTIONS[room.chase_category].copy()
                random.shuffle(room.chase_questions)
                
                # Send initial state to all players
                for player_sid in room.players:
                    if not room.players[player_sid].get('is_host'):
                        await sio.emit('game_started', {
                            'game_type': 'chase',
                            'is_chaser': player_sid == room.chaser,
                            'chase_category': room.chase_category,
                            'board_size': room.chase_state['board_size'],
                            'time_limit': GAME_CONFIG['time_limits']['chase'][
                                '2' if active_players == 2 else '3+'
                            ]
                        }, room=player_sid)

            # Start background music
            await sio.emit('play_music', {
                'track': game_type,
                'volume': MUSIC_CONFIG[game_type]['volume'],
                'loop': True
            }, room=room_id)

            print(f"Game {game_type} started in room {room_id}")
            print(f"Active players: {active_players}")
            print(f"Game state: {room.game_state}")
            print(f"Current game: {room.current_game}")
            if game_type == 'chinese_whispers':
                print(f"Current word: {room.current_word}")
                print(f"Player order: {[room.players[pid]['name'] for pid in room.player_order]}")
            elif game_type == 'trivia':
                print(f"Current question: {room.current_question}")
            elif game_type == 'chase':
                print(f"Chase category: {room.chase_category}")
                print(f"Chaser: {room.players[room.chaser]['name']}")
                print(f"Questions loaded: {len(room.chase_questions)}")

        except Exception as e:
            import traceback
            print(f"Error starting game: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            await sio.emit('game_error', {
                'message': f'Failed to start game: {str(e)}'
            }, room=sid)
            # Reset game state on error
            if room_id in rooms:
                room = rooms[room_id]
                room.game_state = 'waiting'
                room.current_game = None

    @sio.event
    async def submit_drawing(sid, data):
        """Handle drawing submission in Chinese Whispers game."""
        try:
            room_id = data['room_id']
            drawing_data = data['drawing']

            if room_id not in rooms:
                return

            room = rooms[room_id]
            if room.game_state != 'playing' or room.current_game != 'chinese_whispers':
                return

            if sid != room.player_order[room.current_player_index]:
                await sio.emit('game_error', {
                    'message': 'Not your turn to draw'
                }, room=sid)
                return

            # Store drawing
            room.drawings.append({
                'player': room.players[sid]['name'],
                'data': drawing_data,
                'timestamp': datetime.now()
            })

            # Move to next player
            room.current_player_index = (room.current_player_index + 1) % len(room.player_order)
            next_player_id = room.player_order[room.current_player_index]

            # Send drawing to next player
            await sio.emit('receive_drawing', {
                'drawing': drawing_data,
                'previous_player': room.players[sid]['name']
            }, room=next_player_id)

            # Notify all players of turn change
            await sio.emit('next_player', {
                'player': room.players[next_player_id]['name']
            }, room=room_id)

        except Exception as e:
            print(f"Error submitting drawing: {e}")
            await sio.emit('game_error', {
                'message': f'Failed to submit drawing: {str(e)}'
            }, room=sid)

    @sio.event
    async def submit_guess(sid, data):
        """Handle word guess in Chinese Whispers game."""
        try:
            room_id = data['room_id']
            guess = data['guess'].strip().lower()

            if room_id not in rooms:
                return

            room = rooms[room_id]
            if room.game_state != 'playing' or room.current_game != 'chinese_whispers':
                return

            if sid != room.player_order[room.current_player_index]:
                await sio.emit('game_error', {
                    'message': 'Not your turn to guess'
                }, room=sid)
                return

            # Store guess
            room.player_answers[sid] = guess

            # Calculate score
            score_result = room.calculate_score(sid, guess == room.current_word.lower())
            room.scores[sid] = room.scores.get(sid, 0) + score_result['total_score']

            # Check if round is complete
            if room.current_player_index == len(room.player_order) - 1:
                # Round complete
                await sio.emit('round_complete', {
                    'original_word': room.current_word,
                    'final_guess': guess,
                    'scores': room.scores,
                    'drawings': room.drawings
                }, room=room_id)

                # Check if game is complete
                if room.round >= room.total_rounds:
                    # Game complete
                    await sio.emit('game_complete', {
                        'final_scores': room.scores,
                        'winner': max(room.scores.items(), key=lambda x: x[1])[0]
                    }, room=room_id)
                    room.game_state = 'waiting'
                else:
                    # Start next round
                    room.round += 1
                    room.reset_round()
                    room.current_word = room.get_next_word()
                    room.current_player_index = 0
                    
                    # Notify players of next round
                    for player_sid in room.players:
                        if not room.players[player_sid].get('is_host'):
                            is_drawer = player_sid == room.player_order[0]
                            await sio.emit('round_start', {
                                'round': room.round,
                                'is_drawer': is_drawer,
                                'word': room.current_word if is_drawer else None
                            }, room=player_sid)
            else:
                # Move to next player
                room.current_player_index = (room.current_player_index + 1) % len(room.player_order)
                next_player_id = room.player_order[room.current_player_index]

                # Send current state to next player
                await sio.emit('your_turn', {
                    'previous_guess': guess
                }, room=next_player_id)

                # Notify all players of turn change
                await sio.emit('next_player', {
                    'player': room.players[next_player_id]['name']
                }, room=room_id)

        except Exception as e:
            print(f"Error submitting guess: {e}")
            await sio.emit('game_error', {
                'message': f'Failed to submit guess: {str(e)}'
            }, room=sid)

    @sio.event
    async def submit_answer(sid, data):
        """Handle answer submission in Trivia game."""
        try:
            room_id = data['room_id']
            answer = data['answer']
            answer_time = data.get('answer_time')  # Time taken to answer in seconds

            if room_id not in rooms:
                return

            room = rooms[room_id]
            if room.game_state != 'playing' or room.current_game != 'trivia':
                return

            # Check if player already answered
            if sid in room.player_answers:
                return

            # Store answer
            room.player_answers[sid] = answer

            # Calculate score
            is_correct = answer == room.current_question['correct_answer']
            score_result = room.calculate_score(sid, is_correct, answer_time)
            room.scores[sid] = room.scores.get(sid, 0) + score_result['total_score']

            # Send immediate feedback to the player
            await sio.emit('answer_result', {
                'correct': is_correct,
                'score': score_result['total_score'],
                'streak': room.player_streaks.get(sid, 0)
            }, room=sid)

            # Check if all players have answered
            active_players = sum(1 for p in room.players.values()
                               if p['connected'] and not p.get('is_host'))
            if len(room.player_answers) >= active_players:
                # Round complete
                await sio.emit('round_complete', {
                    'question': room.current_question,
                    'answers': {room.players[p_sid]['name']: ans 
                              for p_sid, ans in room.player_answers.items()},
                    'scores': room.scores
                }, room=room_id)

                # Check if game is complete
                if room.round >= room.total_rounds:
                    # Game complete
                    await sio.emit('game_complete', {
                        'final_scores': room.scores,
                        'winner': max(room.scores.items(), key=lambda x: x[1])[0]
                    }, room=room_id)
                    room.game_state = 'waiting'
                else:
                    # Start next round
                    room.round += 1
                    room.reset_round()
                    room.current_question = room.get_next_question()
                    
                    # Notify players of next round
                    await sio.emit('round_start', {
                        'round': room.round,
                        'question': room.current_question,
                        'time_limit': GAME_CONFIG['time_limits']['trivia'][
                            '2-3' if active_players <= 3 else '4-6' if active_players <= 6 else '7+'
                        ]
                    }, room=room_id)

        except Exception as e:
            print(f"Error submitting answer: {e}")
            await sio.emit('game_error', {
                'message': f'Failed to submit answer: {str(e)}'
            }, room=sid)