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