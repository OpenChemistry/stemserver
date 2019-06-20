import sys
import logging

from flask_socketio import SocketIO
from flask import Flask
from flask_login import LoginManager, login_required, login_user
import coloredlogs

from stemserver.girder.auth import fetch_girder_user_from_token, auth_blueprint
from stemserver.socketio import endpoints as socketio_endpoints

app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY='dev',
    GIRDER_API_URL='http://localhost:8080/api/v1'
)
app.config.from_envvar('STEMSERVER_CONFIG', silent=True)

if app.config['SECRET_KEY'] == 'dev':
    app.logger.warning('Using development SECRET_KEY, DO NOT use in production!!!')

login_manager = LoginManager()
login_manager.init_app(app)
socketio = SocketIO(app)

app.register_blueprint(auth_blueprint)

# Girder authentication
@login_manager.user_loader
def load_user(girder_token):
    return fetch_girder_user_from_token(girder_token)

# Setup the socketio events
socketio_endpoints.init(socketio)

if __name__ == '__main__':
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = coloredlogs.ColoredFormatter('%(asctime)s,%(msecs)03d - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger('stemserver')
    logger.addHandler(handler)

    socketio.run(app, host='0.0.0.0', log_output=True)
