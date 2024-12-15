@sio.event
async def join_room(sid, data):
    """Handle player joining a room"""
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
        
        # Handle host joining
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
        
        # Handle player rejoining
        existing_sid = None
        for s, p in room.players.items():
            if not p.get('is_host') and p['name'] == player_name and not p['connected']:
                existing_sid = s
                break
        
        if existing_sid:
            if existing_sid in room.players:
                del room.players[existing_sid]
                await sio.leave_room(existing_sid, room_id)
        
        # Create or get user from database
        try:
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
            
            # Add user to room
            room.players[sid] = {
                'name': player_name,
                'user_id': user.id if user.id else None,
                'profile': profile_picture,
                'connected': True,
                'is_host': is_host
            }
            
            # Join the socket.io room
            await sio.enter_room(sid, room_id)
            
            # Notify client of successful join
            await sio.emit('join_success', {
                'player_name': player_name,
                'room_id': room_id,
                'is_host': False
            }, room=sid)
            
            # Update all clients with new player list
            player_list = [
                {'name': p['name'], 'score': room.scores.get(s, 0)}
                for s, p in room.players.items()
                if p['connected'] and not p.get('is_host')
            ]
            
            await sio.emit('player_joined', {
                'players': player_list,
                'new_player': player_name
            }, room=room_id)
            
            print(f"Player {player_name} successfully joined room {room_id}")
            
        except Exception as e:
            print(f"Database error: {e}")
            await sio.emit('join_error', {
                'message': 'Internal server error'
            }, room=sid)
            return
            
    except Exception as e:
        print(f"Error joining room: {e}")
        await sio.emit('join_error', {
            'message': f"Failed to join room: {str(e)}"
        }, room=sid)