import logging
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

from volume_provider.settings import LOGGING_LEVEL, TEAM_API_URL, DBAAS_TEAM_API_URL, USER_DBAAS_API, PASSWORD_DBAAS_API
from volume_provider.models import Volume, Snapshot
from dbaas_base_provider.baseProvider import BaseProvider
from dbaas_base_provider.team import TeamClient

logging.basicConfig(level=LOGGING_LEVEL)

class BasicProvider(BaseProvider):
    provider_type = "volume_provider"

    @staticmethod
    def load_volume(identifier, search_field="identifier"):
        volume = Volume.objects(**{search_field: identifier}).get()
        return volume


class ProviderBase(BasicProvider):

    def __init__(self, environment, auth_info=None):
        super(ProviderBase, self).__init__(
            environment,
            auth_info=None
        )

    @property
    def commands(self):
        if not self._commands:
            self._commands = self.get_commands()
        return self._commands

    def get_commands(self):
        raise NotImplementedError

    def create_volume(self, group, size_kb, to_address, snapshot_id=None, zone=None, vm_name=None,
                      team_name=None, engine=None, db_name=None, disk_offering_type=None):
        snapshot = None
        if snapshot_id:
            snapshot = Snapshot.objects(identifier=snapshot_id).get()
        volume = Volume()
        volume.size_kb = size_kb
        volume.set_group(group)
        volume.zone = zone
        volume.vm_name = vm_name
        volume.owner_address = to_address
        self._create_volume(
            volume, snapshot=snapshot,
            team_name=team_name,
            engine=engine,
            db_name=db_name,
            disk_offering_type=disk_offering_type
        )
        self._add_access(volume, volume.owner_address)
        volume.save()

        return volume

    def _create_volume(self, volume, snapshot=None, *args, **kwargs):
        raise NotImplementedError

    def delete_volume(self, identifier):
        volume = self.load_volume(identifier)
        self._delete_volume(volume)
        volume.delete()

    def _delete_volume(self, volume):
        raise NotImplementedError

    def move_volume(self, identifier, zone):
        volume = self.load_volume(identifier)
        self._move_volume(volume, zone)

        volume.zone = zone
        volume.save()
        return volume

    def _move_volume(self, volume, zone):
        pass

    def detach_disk(self, identifier):
        volume = self.load_volume(identifier)
        self._detach_disk(volume)

    def _detach_disk(self, volume):
        pass

    def attach_disk(self, identifier, host_vm, host_zone):
        volume = self.load_volume(identifier)
        volume.zone = host_zone or volume.zone
        volume.vm_name = host_vm or volume.vm_name
        self._attach_disk(volume)
        volume.save()

    def _attach_disk(self, volume):
        pass

    def get_volume(self, identifier_or_path):
        try:
            return self.load_volume(identifier_or_path)
        except Volume.DoesNotExist:
            pass
        try:
            return self.load_volume(
                identifier_or_path,
                search_field="path__icontains"
            )
        except Volume.DoesNotExist:
            return None

    def get_team_labels_formatted(self, team_name, infra_name='', database_name='', engine_name=''):
        team_labels = {}
        url = DBAAS_TEAM_API_URL + team_name
        response = requests.get(url, verify=False, auth=HTTPBasicAuth(USER_DBAAS_API, PASSWORD_DBAAS_API))
        if response.status_code == 200:
            team = response.json()
            team_labels = {
                "servico_de_negocio": team["business_service"],
                "cliente": team["client"],
                "team_slug_name": team["slug"],
                "team_id": team["identifier"],
                "created_at": datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
                "engine": engine_name,
                "infra_name": infra_name,
                "database_name": database_name,
                'origin': 'dbaas'
            }
        else:
            team = TeamClient(api_url=TEAM_API_URL, team_name=team_name)
            team_labels = team.make_labels(
                engine_name=engine_name,
                infra_name=infra_name,
                database_name=database_name
            )
        return team_labels

    def add_access(self, identifier, to_address, access_type=None):
        volume = self.load_volume(identifier)
        self._add_access(volume, to_address, access_type)

    def _add_access(self, volume, to_address, *args, **kwargs):
        raise NotImplementedError

    def remove_access(self, identifier, to_address):
        volume = self.load_volume(identifier)
        self._remove_access(volume, to_address)

    def _remove_access(self, volume, to_address):
        raise NotImplementedError

    def resize(self, identifier, new_size_kb):
        volume = self.load_volume(identifier)
        self._resize(volume, new_size_kb)
        volume.size_kb = new_size_kb
        volume.save()

    def _resize(self, volume, new_size_kb):
        raise NotImplementedError

    def get_snapshot_status(self, identifier):
        try:
            snap = Snapshot.objects.get(identifier=identifier)
            return self._get_snapshot_status(snap), snap
        except Exception as e:
            logging.error('Error when try to get snapshot object. Error: {}'.format(e))
            return {'code': 404, 'message': 'Snapshot object not found'}, None

    def _get_snapshot_status(self, identifier):
        raise NotImplementedError

    def take_snapshot(self, identifier, team, engine, db_name, persist=False):
        volume = self.load_volume(identifier)
        snapshot = Snapshot(volume=volume, created_at=datetime.now())
        self._take_snapshot(volume, snapshot, team, engine, db_name, persist)
        snapshot.save()
        return snapshot

    def new_take_snapshot(self, identifier, team, engine, db_name, persist=False):
        volume = self.load_volume(identifier)
        snapshot = Snapshot(volume=volume, created_at=datetime.now())
        self._new_take_snapshot(volume, snapshot, team, engine, db_name, persist)
        snapshot.save()
        return snapshot

    def _take_snapshot(self, volume, snapshot, team, engine, db_name, persist):
        raise NotImplementedError

    def _new_take_snapshot(self, volume, snapshot, team, engine, db_name, persist):
        raise NotImplementedError

    def remove_snapshot(self, identifier, force=False):
        snapshot = Snapshot.objects(identifier=identifier).get()
        removed = self._remove_snapshot(snapshot, force)
        if removed:
            snapshot.delete()
        return removed

    def _remove_snapshot(self, snapshot, force):
        raise NotImplementedError

    def restore_snapshot(self,
            identifier, zone=None, vm_name=None,
            engine=None, team_name=None, db_name=None, disk_offering_type=None
        ):
        snapshot = Snapshot.objects(identifier=identifier).get()
        volume = Volume()
        volume.size_kb = snapshot.volume.size_kb
        volume.set_group(snapshot.volume.group)
        volume.owner_address = snapshot.volume.owner_address
        volume.vm_name = vm_name or snapshot.volume.vm_name
        volume.zone = zone or snapshot.volume.zone
        volume.disk_offering_type = disk_offering_type
        self._restore_snapshot(snapshot, volume, engine, team_name, db_name, disk_offering_type)
        volume.save()
        return volume

    def _restore_snapshot(self, snapshot, volume, engine, team_name, db_name, disk_offering_type):
        raise NotImplementedError

    def get_volumes_from(self, **kwargs):
        return Volume.objects.filter(**kwargs).values_list('resource_id')

    def get_snapshots_from(self, offset=0, **kwargs):
        snaps = Snapshot.objects.filter(**kwargs)
        if not snaps:
            return []
        snaps = list(snaps)
        if offset:
            return snaps[:-offset]

        return snaps

    def new_disk_with_migration(self):
        return self._new_disk_with_migration()

    def _new_disk_with_migration(self):
        return False

    def update_team_labels(self, volume, team_name, zone):
        return self._update_team_labels(volume, team_name, zone)

    def _update_team_labels(self, volume, team_name, zone):
        pass


class CommandsBase(BasicProvider):

    def __init__(self, data_directory="/data"):
        self.data_directory = data_directory

    def die_if_error_script(self):
        return """
die_if_error()
{
    local err=$?
    if [ "$err" != "0" ]; then
        echo "$*"
        exit $err
    fi
}
"""

    def copy_files(self, *args, **kw):
        return self._copy_files(*args, **kw)

    def mount(self, identifier, fstab=True, host_vm=None, host_zone=None):
        volume = self.load_volume(identifier)
        return self._mount(volume,
                           fstab=fstab,
                           host_vm=host_vm,
                           host_zone=host_zone)

    def scp(self, identifier, source_dir, target_ip, target_dir):
        snap = Snapshot.objects(identifier=identifier).get()
        return self._scp(snap, source_dir, target_ip, target_dir)

    def _scp(self, snap, target_ip, target_directory):
        raise NotImplementedError

    def rsync(self, identifier, source_dir, target_ip, target_dir):
        snap = None
        if identifier:
            snap = Snapshot.objects(identifier=identifier).get()
        return self._rsync(snap, source_dir, target_ip, target_dir)

    def _rsync(self, *args, **kwargs):
        raise NotImplementedError

    def add_hosts_allow(self, host_ip):
        return self._add_hosts_allow(host_ip)

    def remove_hosts_allow(self, host_ip):
        return self._remove_hosts_allow(host_ip)

    def _add_hosts_allow(self, host_ip):
        script = self.die_if_error_script()
        script += self.add_hosts_allow_script(host_ip=host_ip)
        return script

    def _remove_hosts_allow(self, host_ip):
        script = self.die_if_error_script()
        script += self.remove_hosts_allow_script(host_ip=host_ip)
        return script

    def add_hosts_allow_script(self, **kw):
        return """
echo "sshd: {host_ip}     - Host Migrate" >> /etc/hosts.allow
die_if_error "Erro on add {host_ip} on /etc/hosts.allow"
""".format(**kw)

    def remove_hosts_allow_script(self, **kw):
        return """
sed -i -e "/sshd: {host_ip}     - Host Migrate/d" /etc/hosts.allow
die_if_error "Erro on remove {host_ip} from /etc/hosts.allow"
""".format(**kw)

    def create_pub_key(self, host_ip):
        return self._create_pub_key(host_ip)

    def remove_pub_key(self, host_ip):
        return self._remove_pub_key(host_ip)

    def _create_pub_key(self, host_ip):
        script = self.die_if_error_script()
        script += self.create_pub_key_script(host_ip=host_ip)
        return script

    def _remove_pub_key(self, host_ip):
        script = self.die_if_error_script()
        script += self.remove_pub_key_script(host_ip=host_ip)
        return script

    def create_pub_key_script(self, **kw):
        return """
[ -f /root/.ssh/dbaas.key.pub ] || ssh-keygen -t rsa -N "" -f /root/.ssh/dbaas.key > /dev/null
cat /root/.ssh/dbaas.key.pub
die_if_error "Error to create public key dbaas"
""".format(**kw)

    def remove_pub_key_script(self, **kw):
        return """
rm -f /root/.ssh/dbaas.key*
die_if_error "Error to remove public key dbaas"
""".format(**kw)

    def _mount(self, volume, *args, **kwargs):
        raise NotImplementedError

    def umount(self, identifier, data_directory):
        volume = self.load_volume(identifier)
        return self._umount(volume, data_directory=data_directory)

    def _umount(self, volume, data_directory=None):
        raise NotImplementedError

    def clean_up(self, identifier):
        volume = self.load_volume(identifier)
        return self._clean_up(volume)

    def _clean_up(self, volume):
        raise NotImplementedError

    def _copy_files(self, *args, **kwargs):
        raise NotImplementedError

    def resize2fs(self, identifier):
        volume = self.load_volume(identifier)
        return self._resize2fs(volume)

    def _resize2fs(self, volume):
        return ""

