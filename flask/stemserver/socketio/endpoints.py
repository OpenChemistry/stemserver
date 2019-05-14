from flask_socketio import SocketIO, emit, join_room


def init(socketio):
    @socketio.on('connect', namespace='/stem')
    def connect():
        print('Client connected')

    @socketio.on('stem.bright', namespace='/stem')
    def bright(data):
        emit('stem.bright', data, room='bright')

    @socketio.on('stem.dark', namespace='/stem')
    def dark(data):
        emit('stem.dark', data, room='dark')

    @socketio.on('subscribe', namespace='/stem')
    def subscribe(topic):
        join_room(topic)

    @socketio.on('stem.size', namespace='/stem')
    def size(data):
        emit('stem.size', data, broadcast=True, include_self=False)

    @socketio.on('disconnect', namespace='/stem')
    def disconnect():
        print('Client disconnected')
