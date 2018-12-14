from flask import Flask, render_template
from flask_socketio import SocketIO, emit

import glob
import os

app = Flask(__name__)
socketio = SocketIO(app)

@socketio.on('connect', namespace='/stem')
def connect():
    print('Client connected')

    for path in glob.glob('./data/stem0.*.bin'):
        with open(path, 'rb') as f:
            emit('stem', {
                'data': f.read()
            });

@socketio.on('disconnect', namespace='/stem')
def disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app)
