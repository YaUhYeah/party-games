import base64
import random
from datetime import datetime
from typing import Dict, Optional

import socketio

from ..models.game_room import GameRoom, GameError
from ..database import User
from ..config.game_config import GAME_CONFIG, MUSIC_CONFIG
from ..config.questions import CHASE_QUESTIONS

def register_socket_events(sio: socketio.AsyncServer, rooms: Dict[str, GameRoom]):
    """Register all socket events."""

    @sio.event
    async def connect(sid, environ):
        print(f"Client connected: {sid}")
        query = environ.get('QUERY_STRING', '')
        # If the room is missing, we can either let them join or disconnect
        room_id = None
        if 'room_id=' in query:
            room_id = query.split('room_id=')[1].split('&')[0]
            print(f"Client {sid} attempting to connect to room {room_id}")
            # If that room doesn't exist, we can disconnect them or create it
            if room_id not in rooms:
                print(f"Warning: Room {room_id} not found")
                await sio.emit(
                    'room_status',
                    {'exists': False, 'message': 'Room not found or expired'},
                    room=sid
                )
                await sio.disconnect(sid)
                return False
        # Otherwise, accept connection if we want

    @sio.event
    async def join_room(sid, data):
        """
        Handle player joining a room:
        - If is_host=True, create the room if needed, or replace old host
        - If not host, check name conflicts, store user in room
        - Send join confirmations, player lists, etc.
        """
        try:
            room_id = data['room_id']
            is_host = data.get('is_host', False)
            player_name = 'Host' if is_host else data['player_name']
            profile_picture = data.get('profile_picture')

            print(f"join_room request from {sid}: {data}")

            # If hosting a brand new room
            if room_id not in rooms and is_host:
                rooms[room_id] = GameRoom(room_id)
                print(f"Created new room: {room_id}")

            # If room does not exist, error out
            if room_id not in rooms:
                print(f"Error: Room {room_id} not found")
                await sio.emit('join_error', {
                    'message': 'Room not found or expired. Please scan again.'
                }, room=sid)
                await sio.disconnect(sid)
                return

            room = rooms[room_id]

            # If host is re-joining or newly joining
            if is_host:
                # If there is an old host SID, remove it
                if room.host_sid and room.host_sid in room.players:
                    del room.players[room.host_sid]
                    await sio.leave_room(room.host_sid, room_id)
                room.host_sid = sid
                room.players[sid] = {
                    'name': 'Host',
                    'is_host': True,
                    'connected': True,
                }
                await sio.enter_room(sid, room_id)
                await sio.emit('join_success', {
                    'player_name': 'Host',
                    'room_id': room_id,
                    'is_host': True
                }, room=sid)
                return

            # Non-host: Check username conflicts
            for s, p in room.players.items():
                if not p.get('is_host') and p['name'] == player_name and p['connected']:
                    await sio.emit('join_error', {
                        'message': 'Username already taken'
                    }, room=sid)
                    await sio.disconnect(sid)
                    return

            # Possibly a rejoin
            existing_sid = None
            for s, p in room.players.items():
                if not p.get('is_host') and p['name'] == player_name and not p['connected']:
                    existing_sid = s
                    break
            # Clean up old SID if we found it
            if existing_sid and existing_sid in room.players:
                try:
                    await sio.leave_room(existing_sid, room_id)
                    del room.players[existing_sid]
                except Exception as e:
                    print(f"Error removing old connection: {e}")

            # Check or create DB user
            user = room.db.query(User).filter(User.username == player_name).first()
            if not user:
                user = User(username=player_name)
                room.db.add(user)
                room.db.commit()

            # If a base64-encoded profile picture was sent, attach it
            if profile_picture:
                try:
                    # Typically "data:image/png;base64,...."
                    image_data = base64.b64decode(profile_picture.split(',')[1])
                    user.profile_picture = image_data
                    room.db.commit()
                except Exception as e:
                    print(f"Error processing profile picture: {e}")
            room.db.refresh(user)

            # Now store the player in room
            room.players[sid] = {
                'name': player_name,
                'user_id': user.id,
                'profile': profile_picture or '',
                'score': 0,
                'connected': True,
                'is_host': False
            }
            await sio.enter_room(sid, room_id)

            # If the room is mid-game, send partial state
            # (not fully implemented here—just an example)
            if room.game_state != 'waiting':
                # e.g. send 'game_state' event to the rejoining sid
                pass

            # Build a fresh player_list for the entire room
            player_list = []
            for player_sid, player_data in room.players.items():
                if player_data['connected'] and not player_data.get('is_host'):
                    player_list.append({
                        'name': player_data['name'],
                        'score': player_data.get('score', 0)
                    })

            # Confirm join to this sid only
            await sio.emit('join_confirmed', {
                'player_name': player_name,
                'room_id': room_id,
                'is_host': False,
                'current_players': player_list
            }, room=sid)

            # Notify everyone else in the room
            await sio.emit('player_joined', {
                'players': player_list,
                'new_player': player_name
            }, room=room_id)

            print(f"Player {player_name} successfully joined room {room_id}")

        except Exception as e:
            print(f"Error joining room: {e}")
            await sio.emit('join_error', {'message': str(e)}, room=sid)
            await sio.disconnect(sid)

    # Example of the "start_game" event logic
    @sio.event
    async def start_game(sid, data):
        """
        Host triggers this to begin a chosen game_type (chase/trivia/chinese_whispers).
        We'll handle the logic for setting up the first round, etc.
        """
        try:
            room_id = data['room_id']
            game_type = data['game_type']
            if room_id not in rooms:
                await sio.emit('game_error', {'message': 'Room not found'}, room=sid)
                return

            room = rooms[room_id]

            # Must be host
            if sid != room.host_sid:
                await sio.emit('game_error', {'message': 'Only host can start'}, room=sid)
                return

            # Count active players (excluding host)
            active_players = [pid for pid, p in room.players.items() if p['connected'] and not p.get('is_host')]
            if len(active_players) < GAME_CONFIG['game_modes'][game_type]['min_players']:
                await sio.emit('game_error', {
                    'message': f"Need at least {GAME_CONFIG['game_modes'][game_type]['min_players']} players to start {game_type}"
                }, room=sid)
                return

            # Initialize common stuff
            room.current_game = game_type
            room.game_state = 'playing'
            room.round = 1
            room.total_rounds = GAME_CONFIG['rounds_per_game']
            room.scores = {pid: 0 for pid in active_players}  # track scores
            room.player_answers = {}
            room.drawings = []
            room.player_order = active_players[:]  # naive approach
            random.shuffle(room.player_order)

            if game_type == 'chinese_whispers':
                room.current_word = room.get_next_word()
                room.current_player_index = 0
                # "is_drawer" for the first player
                for player_sid in room.players:
                    if room.players[player_sid]['connected'] and not room.players[player_sid].get('is_host'):
                        is_drawer = (player_sid == room.player_order[0])
                        await sio.emit('game_started', {
                            'game_type': 'chinese_whispers',
                            'round': 1,
                            'total_rounds': room.total_rounds,
                            'is_drawer': is_drawer,
                            'word': room.current_word if is_drawer else None,
                            'time_limit': _get_drawing_time_limit(len(active_players)),
                            'game_state': 'playing'
                        }, room=player_sid)

            elif game_type == 'trivia':
                room.current_question = room.get_next_question()
                room.player_answers = {}  # Reset answers for new question
                room.round_start_time = datetime.now()  # Start timer
                
                # Broadcast to all players
                await sio.emit('game_started', {
                    'game_type': 'trivia',
                    'round': 1,
                    'total_rounds': room.total_rounds,
                    'question': room.current_question,
                    'time_limit': _get_trivia_time_limit(len(active_players)),
                    'game_state': 'playing',
                    'scores': room.scores,
                    'start_time': room.round_start_time.timestamp()
                }, room=room_id)

            elif game_type == 'chase':
                # Pick a random chaser
                chaser_sid = random.choice(active_players)
                room.chaser = chaser_sid
                # Pick a random category
                room.chase_category = random.choice(list(CHASE_QUESTIONS.keys()))
                room.chase_questions = random.sample(CHASE_QUESTIONS[room.chase_category], 3)
                # Reset chase state
                room.chase_contestant = None
                room.chase_position = 0
                room.chase_state = {
                    'board_size': GAME_CONFIG['chase_board_size'],
                    'chaser_position': 0,
                    'contestant_position': 0,
                    'safe_positions': [],
                    'current_prize': 0,
                    'offer_high': 0,
                    'offer_low': 0,
                    'time_pressure': False,
                    'power_ups': {
                        'double_steps': 1,
                        'shield': 1,
                        'time_freeze': 1
                    },
                }
                # Broadcast to all
                for player_sid in room.players:
                    if room.players[player_sid]['connected'] and not room.players[player_sid].get('is_host'):
                        is_chaser = (player_sid == chaser_sid)
                        await sio.emit('game_started', {
                            'game_type': 'chase',
                            'is_chaser': is_chaser,
                            'chase_category': room.chase_category,
                            'board_size': room.chase_state['board_size'],
                            'time_limit': _get_chase_time_limit(len(active_players)),
                            'game_state': 'playing',
                            'chaser_name': room.players[chaser_sid]['name'],
                            'scores': room.scores
                        }, room=player_sid)

            # Optionally play music
            await sio.emit('play_music', {
                'track': game_type,
                'volume': MUSIC_CONFIG[game_type]['volume'],
                'loop': True
            }, room=room_id)

        except Exception as e:
            import traceback
            print(f"Error starting game: {e}")
            print(traceback.format_exc())
            await sio.emit('game_error', {'message': str(e)}, room=sid)
            # Possibly reset
            if room_id in rooms:
                rooms[room_id].game_state = 'waiting'
                rooms[room_id].current_game = None

    @sio.event
    async def submit_drawing(sid, data):
        """When the drawer in Chinese Whispers finishes and passes the drawing along."""
        try:
            room_id = data['room_id']
            drawing_data = data['drawing']
            if room_id not in rooms:
                return
            room = rooms[room_id]

            if room.game_state != 'playing' or room.current_game != 'chinese_whispers':
                return

            # Must be the current drawer
            if sid != room.player_order[room.current_player_index]:
                await sio.emit('game_error', {'message': 'Not your turn to draw'}, room=sid)
                return

            # Store the drawing
            room.drawings.append({
                'player': room.players[sid]['name'],
                'data': drawing_data,
                'timestamp': datetime.now()
            })

            # Move to next player
            room.current_player_index = (room.current_player_index + 1) % len(room.player_order)
            next_player_id = room.player_order[room.current_player_index]

            # Send the drawing to that next player
            await sio.emit('receive_drawing', {
                'drawing': drawing_data,
                'previous_player': room.players[sid]['name']
            }, room=next_player_id)

            # Notify entire room of whose turn it is
            await sio.emit('next_player', {
                'player': room.players[next_player_id]['name']
            }, room=room_id)

        except Exception as e:
            print(f"Error in submit_drawing: {e}")
            await sio.emit('game_error', {'message': str(e)}, room=sid)

    @sio.event
    async def submit_guess(sid, data):
        """In Chinese Whispers, a guess about the final word (or the next clue)."""
        try:
            room_id = data['room_id']
            guess = data['guess'].strip().lower()
            if room_id not in rooms:
                return
            room = rooms[room_id]
            if room.current_game != 'chinese_whispers':
                return

            # Must be that player's turn
            if sid != room.player_order[room.current_player_index]:
                await sio.emit('game_error', {'message': 'Not your turn to guess'}, room=sid)
                return

            # Store guess
            room.player_answers[sid] = guess

            # Evaluate correctness
            is_correct = (guess == room.current_word.lower())
            scoring = room.calculate_score(sid, is_correct)
            room.scores[sid] = room.scores.get(sid, 0) + scoring['total_score']

            # If last in order, that means the round is done
            if room.current_player_index == len(room.player_order) - 1:
                # Round ends
                await sio.emit('round_complete', {
                    'original_word': room.current_word,
                    'final_guess': guess,
                    'scores': room.scores,
                    'drawings': room.drawings
                }, room=room_id)

                # Check if game is fully done
                if room.round >= room.total_rounds:
                    # Game over
                    await sio.emit('game_complete', {
                        'final_scores': room.scores,
                        'winner': _highest_scorer_name(room)
                    }, room=room_id)
                    room.game_state = 'waiting'
                    room.current_game = None
                else:
                    # Next round
                    room.round += 1
                    room.reset_round()
                    # new word, reset index
                    room.current_word = room.get_next_word()
                    room.current_player_index = 0

                    # Let players know the next round started
                    for pid in room.players:
                        if not room.players[pid].get('is_host'):
                            is_drawer = (pid == room.player_order[0])
                            await sio.emit('round_start', {
                                'round': room.round,
                                'is_drawer': is_drawer,
                                'word': room.current_word if is_drawer else None
                            }, room=pid)
            else:
                # Move to next
                room.current_player_index = (room.current_player_index + 1) % len(room.player_order)
                next_player_id = room.player_order[room.current_player_index]
                await sio.emit('your_turn', {
                    'previous_guess': guess
                }, room=next_player_id)
                await sio.emit('next_player', {
                    'player': room.players[next_player_id]['name']
                }, room=room_id)

        except Exception as e:
            print(f"Error in submit_guess: {e}")
            await sio.emit('game_error', {'message': str(e)}, room=sid)

    @sio.event
    async def submit_answer(sid, data):
        """In Trivia, user sends an answer. We check correctness, update scores, handle next round."""
        try:
            room_id = data['room_id']
            answer = data['answer']
            answer_time = data.get('answer_time')  # Time taken to answer

            if room_id not in rooms:
                return
            room = rooms[room_id]
            if room.current_game != 'trivia' or room.game_state != 'playing':
                return

            # Check if answer is within time limit
            elapsed_time = (datetime.now() - room.round_start_time).total_seconds()
            time_limit = _get_trivia_time_limit(len([p for p in room.players.values() if p['connected'] and not p.get('is_host')]))
            if elapsed_time > time_limit:
                await sio.emit('answer_feedback', {
                    'error': 'Time expired',
                    'correct_answer': room.current_question['correct']
                }, room=sid)
                return

            # Check if they've already answered
            if sid in room.player_answers:
                return  # ignore

            # Store answer with timing info
            room.player_answers[sid] = {
                'answer': answer,
                'time': answer_time or elapsed_time
            }

            # Calculate score with time bonus
            is_correct = (answer == room.current_question['correct'])
            scoring = room.calculate_score(sid, is_correct, answer_time)
            room.scores[sid] = room.scores.get(sid, 0) + scoring['total_score']

            # Immediate feedback to the player
            await sio.emit('answer_feedback', {
                'correct': is_correct,
                'score': scoring['total_score'],
                'streak': room.player_streaks.get(sid, 0),
                'time_bonus': scoring.get('time_bonus', 0),
                'correct_answer': room.current_question['correct'] if not is_correct else None
            }, room=sid)

            # Update all players on answer progress
            active_players = [pid for pid, p in room.players.items() if p['connected'] and not p.get('is_host')]
            await sio.emit('answer_progress', {
                'answered': len(room.player_answers),
                'total': len(active_players)
            }, room=room_id)

            # If everyone has answered or time is up
            if len(room.player_answers) >= len(active_players) or elapsed_time >= time_limit:
                # Calculate stats for this question
                answer_stats = {
                    'correct_count': sum(1 for ans in room.player_answers.values() 
                                      if ans['answer'] == room.current_question['correct']),
                    'fastest_time': min(ans['time'] for ans in room.player_answers.values()),
                    'average_time': sum(ans['time'] for ans in room.player_answers.values()) / len(room.player_answers)
                }

                # End of round
                await sio.emit('round_complete', {
                    'question': room.current_question,
                    'answers': {
                        room.players[p]['name']: ans['answer'] for p, ans in room.player_answers.items()
                    },
                    'scores': room.scores,
                    'stats': answer_stats
                }, room=room_id)

                # Check if final round
                if room.round >= room.total_rounds:
                    # Calculate final achievements and stats
                    final_stats = {
                        'perfect_scores': sum(1 for score in room.scores.values() if score >= room.total_rounds * GAME_CONFIG['points']['correct_trivia']),
                        'total_correct': sum(1 for ans in room.player_answers.values() if ans['answer'] == room.current_question['correct']),
                        'fastest_player': min(((sid, ans['time']) for sid, ans in room.player_answers.items()), key=lambda x: x[1])[0]
                    }
                    
                    await sio.emit('game_complete', {
                        'final_scores': room.scores,
                        'winner': _highest_scorer_name(room),
                        'achievements': room.achievements,
                        'stats': final_stats
                    }, room=room_id)
                    room.game_state = 'waiting'
                    room.current_game = None
                else:
                    # Next round
                    room.round += 1
                    room.reset_round()
                    room.current_question = room.get_next_question()
                    room.round_start_time = datetime.now()  # Reset timer
                    
                    # Send next question with synchronized start time
                    await sio.emit('next_question', {
                        'question': room.current_question,
                        'round': room.round,
                        'time_limit': time_limit,
                        'start_time': room.round_start_time.timestamp(),
                        'total_rounds': room.total_rounds
                    }, room=room_id)

                    await sio.emit('round_start', {
                        'round': room.round,
                        'question': room.current_question,
                        'time_limit': _get_trivia_time_limit(len(active_players))
                    }, room=room_id)

        except Exception as e:
            print(f"Error in submit_answer: {e}")
            await sio.emit('game_error', {'message': str(e)}, room=sid)

    @sio.event
    async def disconnect(sid):
        print(f"Client disconnected: {sid}")
        # Mark them disconnected and handle special cases (chaser, drawer, etc.)
        for room in rooms.values():
            if sid in room.players:
                room.players[sid]['connected'] = False
                disc_name = room.players[sid]['name']

                # If chaser or chase contestant leaves mid-chase
                if room.current_game == 'chase':
                    if sid == room.chaser:
                        room.chaser = None
                        room.game_state = 'waiting'
                        await sio.emit('chase_cancelled', {
                            'reason': f'Chaser {disc_name} disconnected'
                        }, room=room.room_id)
                    elif sid == room.chase_contestant:
                        room.chase_contestant = None
                        room.game_state = 'chase_setup'
                        await sio.emit('chase_cancelled', {
                            'reason': f'Contestant {disc_name} disconnected'
                        }, room=room.room_id)

                # Update players
                active_players = [
                    p for p in room.players.values()
                    if p['connected'] and not p.get('is_host')
                ]
                if len(active_players) < 2 and room.game_state == 'playing':
                    room.game_state = 'waiting'
                    room.current_game = None
                    await sio.emit('game_cancelled', {
                        'reason': 'Not enough players'
                    }, room=room.room_id)

                # If they were drawing in Chinese Whispers
                if (room.current_game == 'chinese_whispers' and
                    sid == room.player_order[room.current_player_index]):
                    room.current_player_index = (room.current_player_index + 1) % len(room.player_order)
                    next_player = room.player_order[room.current_player_index]
                    while not room.players[next_player]['connected']:
                        room.current_player_index = (room.current_player_index + 1) % len(room.player_order)
                        next_player = room.player_order[room.current_player_index]
                    await sio.emit('next_player', {
                        'player': room.players[next_player]['name'],
                        'skipped_disconnected': True
                    }, room=room.room_id)

                # Broadcast updated players
                updated_list = [
                    {'name': p['name'], 'score': p.get('score', 0)}
                    for s, p in room.players.items() if p['connected'] and not p.get('is_host')
                ]
                await sio.emit('player_left', {
                    'players': updated_list,
                    'disconnected_player': disc_name
                }, room=room.room_id)

# Helper methods for time-limits
def _get_drawing_time_limit(player_count: int) -> int:
    if player_count <= 3:
        return GAME_CONFIG['time_limits']['drawing']['2-3']
    elif player_count <= 6:
        return GAME_CONFIG['time_limits']['drawing']['4-6']
    else:
        return GAME_CONFIG['time_limits']['drawing']['7+']

def _get_trivia_time_limit(player_count: int) -> int:
    if player_count <= 3:
        return GAME_CONFIG['time_limits']['trivia']['2-3']
    elif player_count <= 6:
        return GAME_CONFIG['time_limits']['trivia']['4-6']
    else:
        return GAME_CONFIG['time_limits']['trivia']['7+']

def _get_chase_time_limit(player_count: int) -> int:
    if player_count == 2:
        return GAME_CONFIG['time_limits']['chase']['2']
    else:
        return GAME_CONFIG['time_limits']['chase']['3+']

def _highest_scorer_name(room: GameRoom) -> str:
    # Return the name of the highest-scoring player (excluding host)
    if not room.scores:
        return "Nobody"
    top_player_id = max(room.scores, key=room.scores.get)
    return room.players[top_player_id]['name']
