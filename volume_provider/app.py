import json
import logging
from traceback import print_exc
from bson import json_util
from flask import Flask, request, jsonify, make_response
from raven.contrib.flask import Sentry
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from mongoengine import connect
from volume_provider.settings import APP_USERNAME, APP_PASSWORD, MONGODB_PARAMS, MONGODB_DB, LOGGING_LEVEL, SENTRY_DSN
from volume_provider.providers import get_provider_to
from dbaas_base_provider.log import log_this
from volume_provider.models import Snapshot

app = Flask(__name__)
auth = HTTPBasicAuth()
cors = CORS(app)
LOG = logging.getLogger(__name__)

if SENTRY_DSN:
    sentry = Sentry(app, dsn=SENTRY_DSN)

connect(MONGODB_DB, **MONGODB_PARAMS)
logging.basicConfig(level=LOGGING_LEVEL)


@auth.verify_password
def verify_password(username, password):
    if APP_USERNAME and username != APP_USERNAME:
        return False
    if APP_PASSWORD and password != APP_PASSWORD:
        return False
    return True


def build_provider(provider_name, env):
    provider_cls = get_provider_to(provider_name)
    return provider_cls(env, dict(request.headers))


@app.route("/<string:provider_name>/<string:env>/credential/new", methods=["POST"])
@auth.login_required
@log_this
def create_credential(provider_name, env):
    data = request.get_json()
    try:
        provider = build_provider(provider_name, env)
        success, message = provider.credential_add(data)
    except Exception as e:
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    if not success:
        return response_invalid_request(message)
    return response_created(success=success, id=str(message))


@app.route("/<string:provider_name>/credentials", methods=["GET"])
@auth.login_required
@log_this
def get_all_credential(provider_name):
    try:
        provider = build_provider(provider_name, None)
        return make_response(
            json.dumps(
                list(map(lambda x: x, provider.credential.all())),
                default=json_util.default,
            )
        )
    except Exception as e:
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))


@app.route("/<string:provider_name>/<string:env>/credential", methods=["GET"])
@auth.login_required
@log_this
def get_credential(provider_name, env):
    try:
        provider = build_provider(provider_name, env)
        credential = provider.credential.get_by(environment=env)
    except Exception as e:
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    if credential.count() == 0:
        return response_not_found("{}/{}".format(provider_name, env))
    return make_response(json.dumps(credential[0], default=json_util.default))


@app.route("/<string:provider_name>/<string:env>/credential", methods=["PUT"])
@auth.login_required
@log_this
def update_credential(provider_name, env):
    return create_credential(provider_name, env)


@app.route("/<string:provider_name>/<string:env>/credential", methods=["DELETE"])
@auth.login_required
@log_this
def destroy_credential(provider_name, env):
    try:
        provider = build_provider(provider_name, env)
        deleted = provider.credential.delete()
    except Exception as e:
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    if deleted["n"] > 0:
        return response_ok()
    return response_not_found("{}-{}".format(provider_name, env))


@app.route("/<string:provider_name>/<string:env>/volume/new", methods=["POST"])
@auth.login_required
@log_this
def create_volume(provider_name, env):
    data = request.get_json()
    group = data.get("group", None)
    size_kb = data.get("size_kb", None)

    if not (group and size_kb):
        return response_invalid_request("Invalid data {}".format(data))

    try:
        provider = build_provider(provider_name, env)
        volume = provider.create_volume(**data)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_created(identifier=volume.identifier)


@app.route("/<string:provider_name>/<string:env>/volume/<string:identifier>", methods=["DELETE"])
@auth.login_required
@log_this
def delete_volume(provider_name, env, identifier):
    try:
        provider = build_provider(provider_name, env)
        provider.delete_volume(identifier)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route("/<string:provider_name>/<string:env>/move/<string:identifier>", methods=["POST"])
@auth.login_required
@log_this
def move_volume(provider_name, env, identifier):
    data = request.get_json()
    zone = data.get("zone")

    if not zone:
        return response_invalid_request("Invalid zone")
    try:
        provider = build_provider(provider_name, env)
        provider.move_volume(identifier, zone)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route("/<string:provider_name>/<string:env>/volume/<string:identifier_or_path>", methods=["GET"])
@auth.login_required
@log_this
def get_volume(provider_name, env, identifier_or_path):
    try:
        provider = build_provider(provider_name, env)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    volume = provider.get_volume(identifier_or_path)
    if not volume:
        return response_not_found(identifier_or_path)
    return response_ok(**volume.get_json)


@app.route("/<string:provider_name>/<string:env>/access/<string:identifier>", methods=["POST"])
@auth.login_required
@log_this
def add_volume_access(provider_name, env, identifier):
    data = request.get_json()
    to_address = data.get("to_address", None)
    access_type = data.get("access_type", None)

    if not to_address:
        return response_invalid_request("Invalid data {}".format(data))

    try:
        provider = build_provider(provider_name, env)
        provider.add_access(identifier, to_address, access_type)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route("/<string:name>/<string:env>/access/<string:identifier>/<string:address>", methods=["DELETE"])
@auth.login_required
@log_this
def remove_volume_access(name, env, identifier, address):
    try:
        provider = build_provider(name, env)
        provider.remove_access(identifier, address)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route("/<string:provider_name>/<string:env>/resize/<string:identifier>", methods=["POST"])
@auth.login_required
@log_this
def resize_volume(provider_name, env, identifier):
    data = request.get_json()
    new_size_kb = data.get("new_size_kb", None)

    if not new_size_kb:
        return response_invalid_request("Invalid data {}".format(data))

    try:
        provider = build_provider(provider_name, env)
        provider.resize(identifier, new_size_kb)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route("/<string:provider_name>/<string:env>/snapshot/<string:identifier>", methods=["POST"])
@auth.login_required
@log_this
def take_snapshot(provider_name, env, identifier):
    data = request.get_json()
    engine = data.get("engine", None)
    team_name = data.get("team_name", None)
    db_name = data.get("db_name", None)
    persist = bool(int(request.args.get("persist", "0")))
    try:
        provider = build_provider(provider_name, env)
        snapshot = provider.take_snapshot(identifier, team_name, engine, db_name, persist)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_created(
        identifier=snapshot.identifier,
        description=snapshot.description,
        volume_path=snapshot.volume.path,
        size=snapshot.size_bytes,
    )


@app.route("/<string:provider_name>/<string:env>/gcp/snapshot/<string:identifier>", methods=["POST"])
@auth.login_required
@log_this
def new_take_snapshot(provider_name, env, identifier):
    data = request.get_json()
    engine = data.get("engine", None)
    team_name = data.get("team_name", None)
    db_name = data.get("db_name", None)
    persist = bool(int(request.args.get("persist", "0")))
    try:
        provider = build_provider(provider_name, env)
        snapshot = provider.new_take_snapshot(identifier, team_name, engine, db_name, persist)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_created(
        identifier=snapshot.identifier,
        description=snapshot.description,
        volume_path=snapshot.volume.path,
    )


@app.route("/<string:provider_name>/<string:env>/snapshot/<string:identifier>/state", methods=["GET"])
@auth.login_required
@log_this
def get_snapshot_status(provider_name, env, identifier):
    try:
        provider = build_provider(provider_name, env)
        state, snap = provider.get_snapshot_status(identifier)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))

    if state['code'] in [404, 408, 500]:
        return response_created(status_code=state['code'], identifier=identifier, error=state['message'])

    if state['code'] == 200:
        return response_created(
            status_code=state['code'], identifier=state['id'], database_name=state['db'], snapshot_status=state['status'],
            volume_path=snap.volume.path, size=state['size'], description=snap.description
        )
    else:
        return response_created(
            status_code=state['code'], identifier=state['id'], database_name=state['db'],
            snapshot_status=state['status'],
            volume_path=snap.volume.path, description=snap.description
        )


@app.route("/<string:provider_name>/<string:env>/snapshot/<string:identifier>", methods=["DELETE"])
@auth.login_required
@log_this
def remove_snapshot(provider_name, env, identifier):
    force = bool(int(request.args.get("force", "0")))
    try:
        snapshot = Snapshot.objects.filter(identifier=identifier)
        if len(snapshot) > 0:
            provider = build_provider(provider_name, env)
            removed = provider.remove_snapshot(identifier, force)
        else:
            removed = True
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(removed=removed)


@app.route("/<string:provider_name>/<string:env>/snapshot/<string:identifier>/restore", methods=["POST"])
@auth.login_required
@log_this
def restore_snapshot(provider_name, env, identifier):
    data = request.get_json() or {}
    destination_zone = data.get("zone")
    destination_vm_name = data.get("vm_name")
    engine = data.get("engine", None)
    team_name = data.get("team_name", None)
    db_name = data.get("db_name", None)
    disk_offering_type = data.get("disk_offering_type", None)

    try:
        provider = build_provider(provider_name, env)
        volume = provider.restore_snapshot(
            identifier, destination_zone, destination_vm_name,
            engine, team_name, db_name, disk_offering_type
        )
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_created(identifier=volume.identifier)


@app.route("/<string:provider_name>/<string:env>/commands/<string:identifier>/mount", methods=["POST"])
@auth.login_required
@log_this
def command_mount(provider_name, env, identifier):
    data = request.get_json()
    with_fstab = data.get("with_fstab", True)
    data_directory = data.get("data_directory", "/data")
    host_vm = data.get("host_vm", None)
    host_zone = data.get("host_zone", None)

    try:
        provider = build_provider(provider_name, env)
        provider.commands.data_directory = data_directory
        command = provider.commands.mount(
            identifier, fstab=with_fstab, host_vm=host_vm, host_zone=host_zone
        )
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


@app.route("/<string:provider_name>/<string:env>/attach/<string:identifier>/", methods=["POST"])
@auth.login_required
@log_this
def attach_volume(provider_name, env, identifier):
    data = request.get_json()
    host_vm = data.get("host_vm", None)
    host_zone = data.get("host_zone", None)

    try:
        provider = build_provider(provider_name, env)
        provider.attach_disk(identifier, host_vm=host_vm, host_zone=host_zone)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route("/<string:provider_name>/<string:env>/detach/<string:identifier>/", methods=["POST"])
@auth.login_required
@log_this
def detach_volume(provider_name, env, identifier):
    data = request.get_json()

    try:
        provider = build_provider(provider_name, env)
        provider.detach_disk(identifier)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok()


@app.route("/<string:provider_name>/<string:env>/snapshots/<string:identifier>/commands/scp", methods=["GET"])
@auth.login_required
@log_this
def command_scp_from_snap(provider_name, env, identifier):
    data = request.get_json()
    target_ip = data.get("target_ip")
    target_dir = data.get("target_dir")
    source_dir = data.get("source_dir")

    if not (target_ip and target_dir and source_dir):
        return response_invalid_request("Invalid data {}".format(data))
    try:
        provider = build_provider(provider_name, env)
        command = provider.commands.scp(identifier, source_dir, target_ip, target_dir)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


@app.route("/<string:provider_name>/<string:env>/snapshots/<string:identifier>/commands/rsync", methods=["GET"])
@auth.login_required
@log_this
def command_rsync_from_snap(provider_name, env, identifier=None):
    data = request.get_json()
    target_ip = data.get("target_ip")
    target_dir = data.get("target_dir")
    source_dir = data.get("source_dir")

    if not (target_ip and target_dir and source_dir):
        return response_invalid_request("Invalid data {}".format(data))
    try:
        provider = build_provider(provider_name, env)
        command = provider.commands.rsync(
            identifier if identifier != "-" else None,
            source_dir,
            target_ip,
            target_dir
        )
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


@app.route("/<string:provider_name>/<string:env>/commands/create_pub_key", methods=["GET"])
@auth.login_required
@log_this
def command_create_pub_key(provider_name, env):
    keys_must_on_payload = ["host_ip"]
    return _command(provider_name, env, "create_pub_key", keys_must_on_payload)


@app.route("/<string:provider_name>/<string:env>/commands/remove_pub_key", methods=["GET"])
@auth.login_required
@log_this
def command_remove_pub_key(provider_name, env):
    keys_must_on_payload = ["host_ip"]
    return _command(provider_name, env, "remove_pub_key", keys_must_on_payload)


@app.route("/<string:provider_name>/<string:env>/commands/add_hosts_allow", methods=["GET"])
@auth.login_required
@log_this
def command_add_hosts_allow(provider_name, env):
    return _command_hosts_allow(provider_name, env, "add_hosts_allow")


@app.route("/<string:provider_name>/<string:env>/commands/remove_hosts_allow", methods=["GET"])
@auth.login_required
@log_this
def command_remove_hosts_allow(provider_name, env):
    return _command_hosts_allow(provider_name, env, "remove_hosts_allow")


@app.route("/<string:provider_name>/<string:env>/commands/copy_files", methods=["POST"])
@auth.login_required
@log_this
def command_copy_files(provider_name, env):
    data = request.get_json()
    try:
        provider = build_provider(provider_name, env)
        command = provider.commands.copy_files(**data)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


@app.route("/<string:provider_name>/<string:env>/commands/<string:identifier>/umount", methods=["POST"])
@auth.login_required
@log_this
def command_umount(provider_name, env, identifier):
    data = request.get_json()
    data_directory = data.get("data_directory", "/data")
    try:
        provider = build_provider(provider_name, env)
        command = provider.commands.umount(identifier, data_directory=data_directory)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


@app.route("/<string:provider_name>/<string:env>/commands/<string:identifier>/cleanup", methods=["GET"])
@auth.login_required
@log_this
def cleanup(provider_name, env, identifier):
    try:
        provider = build_provider(provider_name, env)
        command = provider.commands.clean_up(identifier)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


# this route only checks if environment must create other
# disk to migrate
@app.route("/<string:provider_name>/<string:env>/new-disk-migration", methods=['GET'])
@auth.login_required
@log_this
def new_disk_with_migration(provider_name, env):
    try:
        provider = build_provider(provider_name, env)
        should_create = provider.new_disk_with_migration()
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(create_new_disk=should_create)


@app.route("/<string:provider_name>/<string:env>/commands/<string:identifier>/resize2fs", methods=["POST"])
@auth.login_required
@log_this
def resize2fs(provider_name, env, identifier):
    try:
        provider = build_provider(provider_name, env)
        command = provider.commands.resize2fs(identifier)
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
    if not (is_valid):
        return response_invalid_request("Invalid data {}".format(data))
    try:
        provider = build_provider(provider_name, env)
        func = getattr(provider.commands, func_name)
        command = func(**data)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


def _command_hosts_allow(provider_name, env, func_name):
    data = request.get_json()
    host_ip = data.get("host_ip")

    if not (host_ip):
        return response_invalid_request("Invalid data {}".format(data))
    try:
        provider = build_provider(provider_name, env)
        func = getattr(provider.commands, func_name)
        command = func(host_ip)
    except Exception as e:  # TODO What can get wrong here?
        print_exc()  # TODO Improve log
        return response_invalid_request(str(e))
    return response_ok(command=command)


@app.route("/<string:provider_name>/<string:env>/volume/update_labels", methods=["POST"])
@auth.login_required
@log_this
def update_team_labels(provider_name, env):
    data = request.get_json()
    vm_name = data.get('vm_name', None)
    team_name = data.get('team_name', None)
    zone = data.get('zone', None)
    if not (vm_name and team_name and zone):
        return response_invalid_request("Invalid data {}".format(data))
    try:
        provider = build_provider(provider_name, env)
        provider.update_team_labels(vm_name, team_name, zone)
    except Exception as e:
        print_exc()
        return response_invalid_request(str(e))
    return response_ok()


@app.route('/')
def default_route():
    response = "volume-provider, from dbaas/dbdev <br>"
    try:
        f = open("./build_info.txt")
        response += f.readline()
    except:
        response += "build_info.txt not found"
    return response


def response_invalid_request(error, status_code=500):
    return _response(status_code, error=error)


def response_not_found(identifier, message=None):
    error = "Could not found with {}".format(identifier)
    return _response(404, error=error, message=message)


def response_created(status_code=201, **kwargs):
    return _response(status_code, **kwargs)


def response_ok(**kwargs):
    if kwargs:
        return _response(200, **kwargs)
    return _response(200, message="ok")


def _response(status, **kwargs):
    content = jsonify(**kwargs)
    return make_response(content, status)
