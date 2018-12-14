from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

@socketio.on('connect', namespace='/stem')
def connect():
    print('Client connected')
    with open('raw.bin', 'rb') as f:
        emit('stem', {'data': f.read()})

@socketio.on('disconnect', namespace='/stem')
def disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app)
