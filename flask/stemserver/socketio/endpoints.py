import functools

from flask import session, request
from flask_login import current_user
from flask_socketio import SocketIO, emit, join_room, disconnect

workers = {}

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
            user_id = current_user.girder_user['_id']
            user_workers = workers.setdefault(user_id, set())
            emit('stem.workers', list(user_workers))
        else:
            return False

    @socketio.on('stem.generate', namespace='/stem')
    @auth_required
    def generate(params):
        emit('stem.generate', params, room=current_room(), include_self=False)

    @socketio.on('stem.worker_connected', namespace='/stem')
    @auth_required
    def worker_connected():
        user_id = current_user.girder_user['_id']
        client_id = request.sid
        user_workers = workers.setdefault(user_id, set())
        user_workers.add(client_id)
        emit('stem.workers', list(user_workers), room=current_room())

    @socketio.on('stem.bright', namespace='/stem')
    @auth_required
    def bright(data):
        emit('stem.bright', data, room=current_room(), include_self=False)

    @socketio.on('stem.dark', namespace='/stem')
    @auth_required
    def dark(data):
        emit('stem.dark', data, room=current_room(), include_self=False)

    @socketio.on('stem.size', namespace='/stem')
    @auth_required
    def size(data):
        emit('stem.size', data, room=current_room(), include_self=False)

    @socketio.on('disconnect', namespace='/stem')
    @auth_required
    def disconnect():
        print('Client disconnected')
        user_id = current_user.girder_user['_id']
        client_id = request.sid
        user_workers = workers.setdefault(user_id, set())
        if client_id in user_workers:
            user_workers.remove(client_id)
            emit('stem.workers', list(user_workers), room=current_room())
