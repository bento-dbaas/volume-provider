from mongoengine import connect
from traceback import print_exc
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from volume_provider.settings import APP_USERNAME, APP_PASSWORD
from volume_provider.providers import get_provider_to


app = Flask(__name__)
auth = HTTPBasicAuth()
cors = CORS(app)

from volume_provider.settings import MONGODB_DB, MONGODB_HOST, MONGODB_PORT, \
    MONGODB_USER, MONGODB_PWD, MONGODB_ENDPOINT
if MONGODB_ENDPOINT:
    connect(MONGODB_ENDPOINT, )
else:
    params = {
        'host': MONGODB_HOST, 'port': MONGODB_PORT, 'db': MONGODB_DB,
        'username': MONGODB_USER, 'password': MONGODB_PWD
    }
    connect(**params)


@auth.verify_password
def verify_password(username, password):
    if APP_USERNAME and username != APP_USERNAME:
        return False
    if APP_PASSWORD and password != APP_PASSWORD:
        return False
    return True


@app.route("/<string:provider_name>/<string:env>/volume/new", methods=['POST'])
@auth.login_required
def create_volume(provider_name, env):
    data = request.get_json()
    group = data.get("group", None)
    size_kb = data.get("size_kb", None)
    to_address = data.get("to_address", None)

    if not(group and size_kb and to_address):
        return response_invalid_request("Invalid data {}".format(data))

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        volume = provider.create_volume(group, size_kb, to_address)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_created(address=volume.uuid)


def response_invalid_request(error, status_code=500):
    return _response(status_code, error=error)


def response_not_found(identifier):
    error = "Could not found with {}".format(identifier)
    return _response(404, error=error)


def response_created(status_code=201, **kwargs):
    return _response(status_code, **kwargs)


def response_ok(message=None):
    return _response(200, message=message or "ok")


def _response(status, **kwargs):
    content = jsonify(**kwargs)
    return make_response(content, status)
