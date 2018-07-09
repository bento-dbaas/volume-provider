import json
from traceback import print_exc
from bson import json_util, ObjectId
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from mongoengine import connect
from volume_provider.settings import APP_USERNAME, APP_PASSWORD, \
    MONGODB_PARAMS, MONGODB_DB
from volume_provider.providers import get_provider_to


app = Flask(__name__)
auth = HTTPBasicAuth()
cors = CORS(app)
connect(MONGODB_DB, **MONGODB_PARAMS)


@auth.verify_password
def verify_password(username, password):
    if APP_USERNAME and username != APP_USERNAME:
        return False
    if APP_PASSWORD and password != APP_PASSWORD:
        return False
    return True


@app.route("/<string:provider_name>/<string:env>/credential/new", methods=['POST'])
@auth.login_required
def create_credential(provider_name, env):
    data = request.get_json()
    if not data:
        return response_invalid_request("No data".format(data))

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        success, message = provider.credential_add(data)
    except Exception as e:
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    if not success:
        return response_invalid_request(message)
    return response_created(success=success, id=str(message))



@app.route(
    "/<string:provider_name>/credentials", methods=['GET']
)
@auth.login_required
def get_all_credential(provider_name):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(None)
        return make_response(
            json.dumps(
                list(map(lambda x: x, provider.build_credential().all())),
                default=json_util.default
            )
        )
    except Exception as e:
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))


@app.route(
    "/<string:provider_name>/<string:env>/credential", methods=['GET']
)
@auth.login_required
def get_credential(provider_name, env):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        credential = provider.build_credential().get_by(environment=env)
    except Exception as e:
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    if credential.count() == 0:
        return response_not_found('{}/{}'.format(provider_name, env))
    return make_response(json.dumps(credential[0], default=json_util.default))


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
    return response_created(uuid=volume.uuid)


@app.route("/<string:provider_name>/<string:env>/volume/<string:uuid>", methods=['DELETE'])
@auth.login_required
def delete_volume(provider_name, env, uuid):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        provider.delete_volume(uuid)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route("/<string:provider_name>/<string:env>/access/<string:uuid>", methods=['POST'])
@auth.login_required
def add_volume_access(provider_name, env, uuid):
    data = request.get_json()
    to_address = data.get("to_address", None)

    if not to_address:
        return response_invalid_request("Invalid data {}".format(data))

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        provider.add_access(uuid, to_address)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route("/<string:provider_name>/<string:env>/access/<string:uuid>/<string:address>", methods=['DELETE'])
@auth.login_required
def remove_volume_access(provider_name, env, uuid, address):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        provider.remove_access(uuid, address)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route("/<string:provider_name>/<string:env>/resize/<string:uuid>", methods=['POST'])
@auth.login_required
def resize_volume(provider_name, env, uuid):
    data = request.get_json()
    new_size_kb = data.get("new_size_kb", None)

    if not new_size_kb:
        return response_invalid_request("Invalid data {}".format(data))

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        provider.resize(uuid, new_size_kb)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route("/<string:provider_name>/<string:env>/snapshot/<string:uuid>", methods=['POST'])
@auth.login_required
def take_snapshot(provider_name, env, uuid):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        snapshot = provider.take_snapshot(uuid)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_created(uuid=snapshot.uuid)


@app.route("/<string:provider_name>/<string:env>/snapshot/<string:uuid>", methods=['DELETE'])
@auth.login_required
def remove_snapshot(provider_name, env, uuid):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        provider.remove_snapshot(uuid)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route("/<string:provider_name>/<string:env>/snapshot/<string:uuid>/restore", methods=['POST'])
@auth.login_required
def restore_snapshot(provider_name, env, uuid):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        volume = provider.restore_snapshot(uuid)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_created(uuid=volume.uuid)


@app.route("/<string:provider_name>/<string:env>/commands/<string:uuid>/mount", methods=['GET'])
@auth.login_required
def command_mount(provider_name, env, uuid):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        command = provider.commands.mount(uuid)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


def response_invalid_request(error, status_code=500):
    return _response(status_code, error=error)


def response_not_found(identifier):
    error = "Could not found with {}".format(identifier)
    return _response(404, error=error)


def response_created(status_code=201, **kwargs):
    return _response(status_code, **kwargs)


def response_ok(**kwargs):
    if kwargs:
        return _response(200, **kwargs)
    return _response(200, message="ok")


def _response(status, **kwargs):
    content = jsonify(**kwargs)
    return make_response(content, status)
