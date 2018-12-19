from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room

import glob
import os

app = Flask(__name__)
socketio = SocketIO(app)

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


@socketio.on('disconnect', namespace='/stem')
def disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', log_output=True)
