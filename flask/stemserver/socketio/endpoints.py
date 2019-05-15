import functools

from flask import session
from flask_login import current_user
from flask_socketio import SocketIO, emit, join_room, disconnect

def auth_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped

def current_room():
    return current_user.girder_user['login']

def init(socketio):
    @socketio.on('connect', namespace='/stem')
    def connect():
        if current_user.is_authenticated:
            print('Client connected')
            join_room(current_room())
        else:
            return False

    @socketio.on('stem.bright', namespace='/stem')
    @auth_required
    def bright(data):
        emit('stem.bright', data, room=current_room())

    @socketio.on('stem.dark', namespace='/stem')
    @auth_required
    def dark(data):
        emit('stem.dark', data, room=current_room())

    @socketio.on('subscribe', namespace='/stem')
    @auth_required
    def subscribe(topic):
        join_room(topic)

    @socketio.on('stem.size', namespace='/stem')
    @auth_required
    def size(data):
        emit('stem.size', data, broadcast=True, include_self=False)

    @socketio.on('disconnect', namespace='/stem')
    @auth_required
    def disconnect():
        print('Client disconnected')
