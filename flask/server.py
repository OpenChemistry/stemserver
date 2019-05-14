from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room

import glob
import os

from stemserver.socketio import endpoints as socketio_endpoints

app = Flask(__name__)
socketio = SocketIO(app)


@socketio.on('subscribe', namespace='/stem')
def subscribe(topic):
    join_room(topic)

# Setup the socketio events
socketio_endpoints.init(socketio)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', log_output=True)
