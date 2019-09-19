import json
from traceback import print_exc
from bson import json_util
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


@app.route(
    "/<string:provider_name>/<string:env>/credential/new", methods=['POST']
)
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
                list(map(lambda x: x, provider.credential.all())),
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
        credential = provider.credential.get_by(environment=env)
    except Exception as e:
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    if credential.count() == 0:
        return response_not_found('{}/{}'.format(provider_name, env))
    return make_response(json.dumps(credential[0], default=json_util.default))


@app.route("/<string:provider_name>/<string:env>/credential", methods=['PUT'])
@auth.login_required
def update_credential(provider_name, env):
    return create_credential(provider_name, env)


@app.route(
    "/<string:provider_name>/<string:env>/credential", methods=['DELETE']
)
@auth.login_required
def destroy_credential(provider_name, env):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        deleted = provider.credential.delete()
    except Exception as e:
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    if deleted['n'] > 0:
        return response_ok()
    return response_not_found("{}-{}".format(provider_name, env))


@app.route("/<string:provider_name>/<string:env>/volume/new", methods=['POST'])
@auth.login_required
def create_volume(provider_name, env):
    data = request.get_json()
    group = data.get("group", None)
    size_kb = data.get("size_kb", None)
    to_address = data.get("to_address", None)
    snapshot_id = data.get("snapshot_id", None)

    if not(group and size_kb and to_address):
        return response_invalid_request("Invalid data {}".format(data))

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        volume = provider.create_volume(group, size_kb, to_address, snapshot_id=snapshot_id)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_created(identifier=volume.identifier)


@app.route(
    "/<string:provider_name>/<string:env>/volume/<string:identifier>",
    methods=['DELETE']
)
@auth.login_required
def delete_volume(provider_name, env, identifier):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        provider.delete_volume(identifier)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route(
    "/<string:provider_name>/<string:env>/volume/<string:identifier_or_path>",
    methods=['GET']
)
@auth.login_required
def get_volume(provider_name, env, identifier_or_path):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    volume = provider.get_volume(identifier_or_path)
    if not volume:
        return response_not_found(identifier_or_path)
    return response_ok(**volume.get_json)


@app.route(
    "/<string:provider_name>/<string:env>/access/<string:identifier>",
    methods=['POST']
)
@auth.login_required
def add_volume_access(provider_name, env, identifier):
    data = request.get_json()
    to_address = data.get("to_address", None)
    access_type = data.get("access_type", None)

    if not to_address:
        return response_invalid_request("Invalid data {}".format(data))

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        provider.add_access(identifier, to_address, access_type)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route(
    "/<string:name>/<string:env>/access/<string:identifier>/<string:address>",
    methods=['DELETE']
)
@auth.login_required
def remove_volume_access(name, env, identifier, address):
    try:
        provider_cls = get_provider_to(name)
        provider = provider_cls(env)
        provider.remove_access(identifier, address)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route(
    "/<string:provider_name>/<string:env>/resize/<string:identifier>",
    methods=['POST']
)
@auth.login_required
def resize_volume(provider_name, env, identifier):
    data = request.get_json()
    new_size_kb = data.get("new_size_kb", None)

    if not new_size_kb:
        return response_invalid_request("Invalid data {}".format(data))

    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        provider.resize(identifier, new_size_kb)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route(
    "/<string:provider_name>/<string:env>/snapshot/<string:identifier>",
    methods=['POST']
)
@auth.login_required
def take_snapshot(provider_name, env, identifier):
    data = request.get_json()
    engine = data.get("engine", None)
    team_name = data.get("team_name", None)
    db_name = data.get("db_name", None)
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        snapshot = provider.take_snapshot(identifier, team_name, engine, db_name)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_created(
        identifier=snapshot.identifier,
        description=snapshot.description
    )


@app.route(
    "/<string:provider_name>/<string:env>/snapshot/<string:identifier>/state",
    methods=['GET']
)
@auth.login_required
def get_snapshot_status(provider_name, env, identifier):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        state = provider.get_snapshot_status(identifier)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(
        state=state
    )


@app.route(
    "/<string:provider_name>/<string:env>/snapshot/<string:identifier>",
    methods=['DELETE']
)
@auth.login_required
def remove_snapshot(provider_name, env, identifier):
    force = bool(int(request.args.get('force', '0')))
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        removed = provider.remove_snapshot(identifier, force)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(removed=removed)


@app.route(
    "/<string:provider_name>/<string:env>/snapshot/<string:identifier>/restore",
    methods=['POST']
)
@auth.login_required
def restore_snapshot(provider_name, env, identifier):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        volume = provider.restore_snapshot(identifier)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_created(identifier=volume.identifier)


@app.route(
    "/<string:provider_name>/<string:env>/commands/<string:identifier>/mount",
    methods=['POST']
)
@auth.login_required
def command_mount(provider_name, env, identifier):
    data = request.get_json()
    with_fstab = data.get("with_fstab", True)
    data_directory = data.get("data_directory", "/data")
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        provider.commands.data_directory = data_directory
        command = provider.commands.mount(identifier, fstab=with_fstab)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


@app.route(
    "/<string:provider_name>/<string:env>/snapshots/<string:identifier>/commands/scp",
    methods=['GET']
)
@auth.login_required
def command_scp_from_snap(provider_name, env, identifier):
    data = request.get_json()
    target_ip = data.get("target_ip")
    target_dir = data.get("target_dir")
    source_dir = data.get("source_dir")

    if not(target_ip and target_dir and source_dir):
        return response_invalid_request("Invalid data {}".format(data))
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        command = provider.commands.scp(
            identifier,
            source_dir,
            target_ip,
            target_dir
        )
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


@app.route(
    "/<string:provider_name>/<string:env>/commands/create_pub_key",
    methods=['GET']
)
@auth.login_required
def command_create_pub_key(provider_name, env):
    keys_must_on_payload = ['host_ip']
    return _command(provider_name, env, 'create_pub_key', keys_must_on_payload)


@app.route(
    "/<string:provider_name>/<string:env>/commands/remove_pub_key",
    methods=['GET']
)
@auth.login_required
def command_remove_pub_key(provider_name, env):
    keys_must_on_payload = ['host_ip']
    return _command(provider_name, env, 'remove_pub_key', keys_must_on_payload)


@app.route(
    "/<string:provider_name>/<string:env>/commands/add_hosts_allow",
    methods=['GET']
)
@auth.login_required
def command_add_hosts_allow(provider_name, env):
    return _command_hosts_allow(provider_name, env, 'add_hosts_allow')


@app.route(
    "/<string:provider_name>/<string:env>/commands/remove_hosts_allow",
    methods=['GET']
)
@auth.login_required
def command_remove_hosts_allow(provider_name, env):
    return _command_hosts_allow(provider_name, env, 'remove_hosts_allow')


@app.route(
    "/<string:provider_name>/<string:env>/commands/copy_files",
    methods=['POST']
)
@auth.login_required
def command_copy_files(provider_name, env):
    data = request.get_json()
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        command = provider.commands.copy_files(**data)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


@app.route(
    "/<string:provider_name>/<string:env>/commands/<string:identifier>/umount",
    methods=['POST']
)
@auth.login_required
def command_umount(provider_name, env, identifier):
    data = request.get_json()
    data_directory = data.get("data_directory", "/data")
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        command = provider.commands.umount(
            identifier,
            data_directory=data_directory
        )
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


@app.route(
    "/<string:provider_name>/<string:env>/commands/<string:identifier>/cleanup",
    methods=['GET']
)
@auth.login_required
def cleanup(provider_name, env, identifier):
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        command = provider.commands.clean_up(identifier)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


def _validate_payload(keys):
    data = request.get_json()
    data_keys = data.keys()
    return all(k in data_keys for k in keys), data


def _command(provider_name, env, func_name, keys_must_on_payload):
    is_valid, data = _validate_payload(keys_must_on_payload)
    if not(is_valid):
        return response_invalid_request("Invalid data {}".format(data))
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        func = getattr(provider.commands, func_name)
        command = func(**data)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


def _command_hosts_allow(provider_name, env, func_name):
    data = request.get_json()
    host_ip = data.get("host_ip")

    if not(host_ip):
        return response_invalid_request("Invalid data {}".format(data))
    try:
        provider_cls = get_provider_to(provider_name)
        provider = provider_cls(env)
        func = getattr(provider.commands, func_name)
        command = func(host_ip)
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
