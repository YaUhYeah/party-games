"""Socket events module."""
import base64
from typing import Dict

import socketio

from ..models.game_room import GameRoom
from ..database import User, Achievement

def register_socket_events(sio: socketio.AsyncServer, rooms: Dict[str, GameRoom]):
    """Register all socket events."""

    @sio.event
    async def connect(sid, environ):
        """Handle client connection."""
        print(f"Client connected: {sid}")

    @sio.event
    async def join_room(sid, data):
        """Handle player joining a room."""
        try:
            room_id = data['room_id']
            is_host = data.get('is_host', False)
            player_name = 'Host' if is_host else data['player_name']
            profile_picture = data.get('profile_picture')

            print(f"Join room request: {data}")

            # Create room if it doesn't exist
            if room_id not in rooms:
                print(f"Creating new room: {room_id}")
                rooms[room_id] = GameRoom(room_id)

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
    async def start_game(sid, data):
        """Handle game start request."""
        try:
            room_id = data['room_id']
            game_type = data['game_type']
            room = rooms[room_id]

            # Verify sender is host
            if sid != room.host_sid:
                await sio.emit('game_error', {
                    'message': 'Only the host can start the game'
                }, room=sid)
                return

            # Check minimum players
            active_players = sum(1 for p in room.players.values()
                               if p['connected'] and not p.get('is_host'))
            if active_players < 2:
                await sio.emit('game_error', {
                    'message': 'Need at least 2 players to start'
                }, room=sid)
                return

            # Initialize game
            room.current_game = game_type
            room.game_state = 'playing'
            room.round = 0
            room.scores = {sid: 0 for sid in room.players if not room.players[sid].get('is_host')}

            if game_type == 'trivia':
                # Set up first question
                room.current_question = room.get_next_question()
                await sio.emit('game_state', {
                    'state': 'playing',
                    'game_type': 'trivia',
                    'round': room.round,
                    'total_rounds': room.total_rounds,
                    'current_question': room.current_question
                }, room=room_id)

            elif game_type == 'chinese_whispers':
                # Set up drawing order and first word
                room.shuffle_player_order_with_catchup()
                room.current_word = room.get_next_word()
                
                # Notify all players
                for player_sid in room.players:
                    if not room.players[player_sid].get('is_host'):
                        is_current = room.player_order[0] == player_sid
                        await sio.emit('game_state', {
                            'state': 'playing',
                            'game_type': 'chinese_whispers',
                            'round': room.round,
                            'total_rounds': room.total_rounds,
                            'current_word': room.current_word if is_current else None,
                            'is_your_turn': is_current
                        }, room=player_sid)

            elif game_type == 'chase':
                # Set up chase game
                room.game_state = 'chase_setup'
                await sio.emit('game_state', {
                    'state': 'chase_setup',
                    'game_type': 'chase',
                    'round': room.round,
                    'total_rounds': room.total_rounds
                }, room=room_id)

        except Exception as e:
            print(f"Error starting game: {e}")
            await sio.emit('game_error', {
                'message': f"Failed to start game: {str(e)}"
            }, room=sid)

    @sio.event
    async def submit_answer(sid, data):
        """Handle answer submission for trivia game."""
        try:
            room_id = data['room_id']
            answer_index = data['answer_index']
            timestamp = data.get('timestamp', time.time() * 1000)
            room = rooms[room_id]

            if room.current_game != 'trivia' or room.game_state != 'playing':
                return

            # Calculate score
            is_correct = answer_index == room.current_question['correct_index']
            answer_time = (timestamp - room.round_start_time.timestamp() * 1000) / 1000
            score_data = room.calculate_score(sid, is_correct, answer_time)

            # Send result to player
            await sio.emit('answer_result', {
                'correct': is_correct,
                'score': score_data
            }, room=sid)

            # Check if all players answered
            all_answered = all(sid in room.player_answers 
                             for sid in room.players 
                             if not room.players[sid].get('is_host'))

            if all_answered:
                if room.round + 1 >= room.total_rounds:
                    # Game complete
                    await sio.emit('game_complete', {
                        'final_scores': room.get_leaderboard()
                    }, room=room_id)
                    room.game_state = 'complete'
                else:
                    # Next round
                    room.advance_round()
                    await sio.emit('game_state', {
                        'state': 'playing',
                        'game_type': 'trivia',
                        'round': room.round,
                        'total_rounds': room.total_rounds,
                        'current_question': room.current_question
                    }, room=room_id)

        except Exception as e:
            print(f"Error handling answer: {e}")
            await sio.emit('game_error', {
                'message': f"Failed to process answer: {str(e)}"
            }, room=sid)

    @sio.event
    async def submit_drawing(sid, data):
        """Handle drawing submission for chinese whispers game."""
        try:
            room_id = data['room_id']
            drawing = data['drawing']
            room = rooms[room_id]

            if room.current_game != 'chinese_whispers' or room.game_state != 'playing':
                return

            # Store drawing
            room.drawings.append({
                'player': room.players[sid]['name'],
                'drawing': drawing,
                'word': room.current_word
            })

            # Move to next player
            room.current_player_index = (room.current_player_index + 1) % len(room.player_order)
            next_player_id = room.player_order[room.current_player_index]

            # Check if round complete
            if room.current_player_index == 0:
                if room.round + 1 >= room.total_rounds:
                    # Game complete
                    await sio.emit('game_complete', {
                        'final_scores': room.get_leaderboard(),
                        'drawings': room.drawings
                    }, room=room_id)
                    room.game_state = 'complete'
                else:
                    # Next round
                    room.advance_round()
                    # Notify all players
                    for player_sid in room.players:
                        if not room.players[player_sid].get('is_host'):
                            is_current = room.player_order[0] == player_sid
                            await sio.emit('game_state', {
                                'state': 'playing',
                                'game_type': 'chinese_whispers',
                                'round': room.round,
                                'total_rounds': room.total_rounds,
                                'current_word': room.current_word if is_current else None,
                                'is_your_turn': is_current
                            }, room=player_sid)
            else:
                # Continue current round with next player
                await sio.emit('game_state', {
                    'state': 'playing',
                    'game_type': 'chinese_whispers',
                    'round': room.round,
                    'total_rounds': room.total_rounds,
                    'current_word': room.current_word,
                    'is_your_turn': True
                }, room=next_player_id)

        except Exception as e:
            print(f"Error handling drawing: {e}")
            await sio.emit('game_error', {
                'message': f"Failed to process drawing: {str(e)}"
            }, room=sid)

    @sio.event
    async def submit_chase_answer(sid, data):
        """Handle answer submission for chase game."""
        try:
            room_id = data['room_id']
            answer_index = data['answer_index']
            timestamp = data.get('timestamp', time.time() * 1000)
            room = rooms[room_id]

            if room.current_game != 'chase' or room.game_state != 'chase_question':
                return

            current_question = room.chase_questions[0]
            is_correct = answer_index == current_question['correct_index']
            is_chaser = sid == room.chaser

            if is_chaser:
                if is_correct:
                    room.chase_position -= 1  # Chaser moves closer
                    if room.chase_position <= 0:
                        # Chaser caught contestant
                        room.chase_scores[room.chaser] = room.chase_scores.get(room.chaser, 0) + GAME_CONFIG['points']['chase_catch']
                        await sio.emit('chase_complete', {
                            'caught': True,
                            'scores': room.chase_scores
                        }, room=room_id)
                        room.game_state = 'chase_setup'
                        room.chase_contestant = None
                        return
            else:  # Contestant
                if is_correct:
                    room.chase_position += 1  # Contestant moves away
                    room.chase_scores[sid] = room.chase_scores.get(sid, 0) + GAME_CONFIG['points']['chase_step']
                    if room.chase_position >= GAME_CONFIG['chase_board_size']:
                        # Contestant escaped
                        room.chase_scores[sid] = room.chase_scores.get(sid, 0) + GAME_CONFIG['points']['chase_win']
                        await sio.emit('chase_complete', {
                            'caught': False,
                            'scores': room.chase_scores
                        }, room=room_id)
                        room.game_state = 'chase_setup'
                        room.chase_contestant = None
                        return

            # Move to next question
            room.chase_questions.pop(0)
            if room.chase_questions:
                await sio.emit('game_state', {
                    'state': 'chase_question',
                    'game_type': 'chase',
                    'chase_position': room.chase_position,
                    'current_question': room.chase_questions[0]
                }, room=room_id)
            else:
                # No more questions, end chase
                await sio.emit('chase_complete', {
                    'caught': room.chase_position <= 0,
                    'scores': room.chase_scores
                }, room=room_id)
                room.game_state = 'chase_setup'
                room.chase_contestant = None

        except Exception as e:
            print(f"Error handling chase answer: {e}")
            await sio.emit('game_error', {
                'message': f"Failed to process chase answer: {str(e)}"
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