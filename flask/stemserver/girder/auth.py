from flask import Flask, Blueprint, abort, request, current_app
from flask.json import jsonify
from flask_login import LoginManager, UserMixin, login_required, login_user
import requests

class GirderUser(UserMixin):
    def __init__(self, girder_token, user):
        self.girder_user = user
        self.id = girder_token

def _fetch_girder_user_from_token(girder_token):
    headers = {
        'Girder-Token': girder_token
    }
    r = requests.get('%s/user/me' % current_app.config['GIRDER_API_URL'], headers=headers)
    user = r.json()
    if user is None:
        return None

    return GirderUser(girder_token, user)

def _fetch_girder_user_from_api_key(girder_api_key):
    params = {
        'key': girder_api_key
    }
    r = requests.post('%s/api_key/token' % current_app.config['GIRDER_API_URL'], params=params)

    # Girder returns 400 for invalid key
    if r.status_code == 400:
        return None

    r.raise_for_status()
    r = r.json()

    return _fetch_girder_user_from_token(r['authToken']['token'])

auth_blueprint = Blueprint('auth_blueprint', __name__)

@auth_blueprint.route('/login', methods=['POST'])
def login():
    r = request.get_json()
    r = r if r is not None else {}

    if 'girderToken' in r:
        user = _fetch_girder_user_from_token(r['girderToken'])
    elif 'girderApiKey' in r:
        user = _fetch_girder_user_from_api_key(r['girderApiKey'])
    else:
        response = jsonify({
            'message': "'girderToken' or 'girderApiKey' is required."
        })

        return response, 400

    if user is None:
        return abort(401)

    r = login_user(user)

    return ''
