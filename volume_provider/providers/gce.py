import json
import logging
from datetime import datetime
from time import sleep
import httplib2
import google_auth_httplib2
import pytz

from os import getenv
from collections import namedtuple
from time import sleep

from dateutil import relativedelta
from googleapiclient.errors import HttpError

import googleapiclient.discovery
from google.oauth2 import service_account

from volume_provider.settings import HTTP_PROXY, TAG_BACKUP_DBAAS
from volume_provider.credentials.gce import CredentialGce, CredentialAddGce
from volume_provider.providers.base import ProviderBase, CommandsBase
from volume_provider.settings import TEAM_API_URL
from dbaas_base_provider.team import TeamClient
from volume_provider.models import Volume

LOG = logging.getLogger(__name__)


class ProviderGce(ProviderBase):

    seconds_to_wait = 3
    persisted_day = str(getenv("SNAPSHOTS_PERSIST_DAY", "10")).zfill(2)

    def get_commands(self):
        return CommandsGce(self)

    @classmethod
    def get_provider(cls):
        return 'gce'

    def build_client(self):
        service_account_data = self.credential.content['service_account']
        service_account_data['private_key'] = service_account_data[
            'private_key'
        ].replace('\\n', '\n')

        credentials = service_account.Credentials.from_service_account_info(
            service_account_data,
            scopes=self.credential.scopes
        )

        if HTTP_PROXY:
            _, host, port = HTTP_PROXY.split(':')
            try:
                port = int(port)
            except ValueError:
                raise EnvironmentError('HTTP_PROXY incorrect format')

            proxied_http = httplib2.Http(proxy_info=httplib2.ProxyInfo(
                httplib2.socks.PROXY_TYPE_HTTP,
                host.replace('//', ''),
                port
            ))

            authorized_http = google_auth_httplib2.AuthorizedHttp(
                                credentials,
                                http=proxied_http)

            service = googleapiclient.discovery.build(
                        'compute',
                        'v1',
                        http=authorized_http)
        else:
            service = googleapiclient.discovery.build(
                'compute',
                'v1',
                credentials=credentials,
            )

        return service

    def build_credential(self):
        return CredentialGce(
            self.provider, self.environment
        )

    def get_credential_add(self):
        return CredentialAddGce

    def __get_instance_disks(self, zone, vm_name):
        all_disks = self.client.instances().get(
                        project=self.credential.project,
                        zone=zone,
                        instance=vm_name
                    ).execute().get("disks")

        return [x['deviceName'] for x in all_disks]

    def _get_volumes(self, zone, instance, group):
        vol = self.get_volumes_from(group=group)
        return [self.get_device_name(x) for x in vol]

    def _get_new_disk_name(self, volume):
        all_disks = self._get_volumes(
            volume.zone,
            volume.vm_name,
            volume.group
        )
        all_disks_name_data = []
        for disk in all_disks:
            if 'data' in disk:
                all_disks_name_data.append(disk)

        disk_name = "data%s" % (int(all_disks_name_data[-1].split("data")[1]) + 1)\
                    if len(all_disks_name_data)\
                    else "data1"

        return "%s-%s" % (volume.group, disk_name)

    def _create_volume(self, volume, snapshot=None, *args, **kwargs):
        disk_name = self._get_new_disk_name(volume)
        team_name = kwargs.get('team_name')
        disk_offering_type = kwargs.get("disk_offering_type", None)
        if not team_name:
            raise Exception("The team name must be passed")

        team = TeamClient(api_url=TEAM_API_URL, team_name=team_name)
        labels = team.make_labels(
            engine_name=kwargs.get("engine", ''),
            infra_name=volume.group,
            database_name=kwargs.get("db_name", '')
        )

        config = {
            'name': disk_name,
            'sizeGb': volume.convert_kb_to_gb(volume.size_kb, to_int=True),
            'labels': labels,
        }

        if disk_offering_type:
            config['type'] = self.build_type_disk_url(disk_offering_type)

        if snapshot:
            config['sourceSnapshot'] = "global/snapshots/%s" % \
                (snapshot.description)

        disk_create = self.get_or_none_resource(
            self.client.disks,
            project=self.credential.project,
            zone=volume.zone,
            disk=disk_name
        )
        ready = True

        if disk_create is None:
            disk_create = self.client.disks().insert(
                project=self.credential.project,
                zone=volume.zone,
                body=config
            ).execute()

            ready = self.wait_operation(
                zone=volume.zone,
                operation=disk_create.get('name')
            )

        volume.identifier = disk_create.get('id')
        volume.resource_id = disk_name
        volume.path = "/dev/disk/by-id/google-%s" % \
            self.get_device_name(disk_name)
        volume.labels = labels
        volume.disk_offering_type = config['type'] if disk_offering_type else None

        return ready

    def _add_access(self, volume, to_address, *args, **kwargs):
        pass

    def __destroy_volume(self, volume):
        # Verify if disk is already removed
        disk_create = self.get_or_none_resource(
            self.client.disks,
            project=self.credential.project,
            zone=volume.zone,
            disk=volume.resource_id
        )

        if disk_create is None:
            return True

        delete_volume = self.client.disks().delete(
            project=self.credential.project,
            zone=volume.zone,
            disk=volume.resource_id
        ).execute()

        return self.wait_operation(
            zone=volume.zone,
            operation=delete_volume.get('name')
        )

    def _resize(self, volume, new_size_kb):
        if new_size_kb <= volume.size_kb:
            raise EnvironmentError(
                "New size must be greater than current size"
            )

        config = {
            "sizeGb": volume.convert_kb_to_gb(new_size_kb, to_int=True)
        }
        disk_resize = self.client.disks().resize(
            project=self.credential.project,
            zone=volume.zone,
            disk=volume.resource_id,
            body=config
        ).execute()

        return self.wait_operation(
            zone=volume.zone,
            operation=disk_resize.get('name')
        )

    def __verify_none(self, dict_var, key, var):
        if var and key:
            dict_var[key] = var

    def __get_snapshot_name(self, volume):
        return "ss-%(volume_name)s-%(timestamp)s" % {
            'volume_name': volume.resource_id.replace('-', ''),
            'timestamp': datetime.now().strftime('%Y%m%d%H%M%S%f')
        }

    def _verify_persistent_backup_date(self):
        tz = pytz.timezone('America/Sao_Paulo')
        now = datetime.now(tz)
        LOG.info('Persisted day: %s - Now: %s', self.persisted_day, now.strftime('%Y-%m-%d %H:%M:%S:%f'))
        return now.strftime('%d').zfill(2) == self.persisted_day

    def _validate_persistence_month(self):
        tz = pytz.timezone('America/Sao_Paulo')
        now = datetime.now(tz)
        if now.strftime('%d').zfill(2) < str(int(self.persisted_day) + 2).zfill(2):
            return datetime.today().strftime("%Y-%m")

        nextmonth = datetime.today() + relativedelta.relativedelta(months=1)
        return nextmonth.strftime("%Y-%m")

    def _take_snapshot(self, volume, snapshot, team, engine, db_name, persist):
        snapshot_name = self.__get_snapshot_name(volume)

        team = TeamClient(api_url=TEAM_API_URL, team_name=team)
        labels = team.make_labels(
            engine_name=engine,
            infra_name=volume.group,
            database_name=db_name
        )

        if persist or self._verify_persistent_backup_date():
            LOG.info('The snapshot will be persisted')
            persist_month = self._validate_persistence_month()
            labels['is_persisted'] = 1
            labels['persist_month'] = persist_month

        snapshot.labels = labels
        snapshot.description = snapshot_name

        snap = self.get_or_none_resource(
            self.client.snapshots,
            project=self.credential.project,
            snapshot=snapshot_name
        )

        if snap is None:
            config = {
                'labels': labels,
                'name': snapshot_name,
                "storageLocations": [self.credential.region]
            }

            operation = self.client.disks().createSnapshot(
                project=self.credential.project,
                zone=volume.zone,
                disk=volume.resource_id,
                body=config
            ).execute()

            self.wait_operation(
                zone=volume.zone,
                operation=operation.get('name')
            )

            snap = self.client.snapshots().get(
                project=self.credential.project,
                snapshot=snapshot_name
            ).execute()

        snapshot.identifier = snap.get('id')
        snapshot.size_bytes = snap.get('downloadBytes')

    def _remove_snapshot(self, snapshot, *args, **kwrgs):
        operation = self.get_or_none_resource(
            self.client.snapshots,
            project=self.credential.project,
            snapshot=snapshot.description
        )

        if operation is None:
            return True

        operation = self.client.snapshots().delete(
                project=self.credential.project,
                snapshot=snapshot.description
        ).execute()

        return self.wait_operation(operation=operation.get('name'))

    def _restore_snapshot(self, snapshot, volume, engine, team_name, db_name, disk_offering_type):
        return self._create_volume(
            volume=volume,
            snapshot=snapshot,
            engine=engine,
            team_name=team_name,
            db_name=db_name,
            disk_offering_type=disk_offering_type
        )

    def get_disk(self, name, zone, execute_request=True):
        req = self.client.disks().get(
            project=self.credential.project,
            zone=zone,
            disk=name
        )

        return req if not execute_request else req.execute()

    def get_instance_status(self, volume):
        instance = self.client.instances().get(
            project=self.credential.project,
            zone=volume.zone,
            instance=volume.vm_name
        ).execute()

        return instance.get('status')

    def get_device_name(self, disk_name):
        return disk_name.rsplit("-", 1)[1]

    def _attach_disk(self, volume):
        disk = self.get_disk(volume.resource_id, volume.zone)

        config = {
            "source": disk.get('selfLink'),
            "deviceName": self.get_device_name(volume.resource_id),
            "autoDelete": True
        }

        # checks if disk is already attached
        for user in disk.get('users', []):
            if user.endswith("/%s" % volume.vm_name):
                return True

        attach_disk = self.client\
            .instances().attachDisk(
                project=self.credential.project,
                zone=volume.zone,
                instance=volume.vm_name,
                body=config
            ).execute()

        return self.wait_operation(
            zone=volume.zone,
            operation=attach_disk.get('name')
        )

    def _detach_disk(self, volume):

        vm_attached_disks = self.__get_instance_disks(
            zone=volume.zone,
            vm_name=volume.vm_name)

        device_name = self.get_device_name(volume.resource_id)

        if device_name not in vm_attached_disks:
            return

        detach_disk = self.client.instances().detachDisk(
                project=self.credential.project,
                zone=volume.zone,
                instance=volume.vm_name,
                deviceName=self.get_device_name(volume.resource_id)
        ).execute()

        return self.wait_operation(
            zone=volume.zone,
            operation=detach_disk.get('name')
        )

    def _move_volume(self, volume, zone):
        if volume.zone == zone:
            return True

        # Verify if disk is already moved
        disk = self.get_or_none_resource(
            self.client.disks,
            project=self.credential.project,
            disk=volume.resource_id,
            zone=zone
        )

        if disk is not None:
            return True

        config = {
            "targetDisk": "zones/%(zone)s/disks/%(disk_name)s" % {
                "zone": volume.zone,
                "disk_name": volume.resource_id
            },
            "destinationZone": "zones/%s" % zone
        }

        move_volume = self.client.projects().moveDisk(
            project=self.credential.project,
            body=config
        ).execute()

        return self.wait_operation(
            operation=move_volume.get('name')
        )

    def __wait_instance_status(self, volume, status):
        while self.get_instance_status(volume) != status:
            sleep(self.seconds_to_wait)

        return True

    def _delete_volume(self, volume):
        return self.__destroy_volume(volume)

    def _remove_all_snapshots(self, group):
        snaps = self.client.snapshots().list(
            project=self.credential.project,
            filter="labels.group=%s" % group
        ).execute().get('items', [])

        for ss in snaps:
            self.client.snapshots().delete(
                project=self.credential.project,
                snapshot=ss.get('name')
            ).execute()

    def _new_disk_with_migration(self):
        return True

    def _get_snapshot_status(self, snapshot):
        return "available"

    def build_type_disk_url(self, disk_type):
        url = "/projects/{project}/regions/{region}/diskTypes/{disk_type}"
        return url.format(project=self.credential.project,
                          region=self.credential.region,
                          disk_type=disk_type if disk_type is not None else 'pd-standard')

    def update_labels(self, resource_id, zone, team):
        try:
            # function to get labelFingerprint and Labels info from a disk of GCP
            disk_gcp = self.client.disks().get(project=self.credential.project,
                                               zone=zone,
                                               disk=resource_id).execute()
            labelFingerprint = disk_gcp['labelFingerprint']
            labels = disk_gcp['labels']

            # add info of new team
            labels['servico_de_negocio'] = team.get('servico-de-negocio')
            labels['cliente'] = team.get('cliente')
            labels['team_slug_name'] = team.get('slug')
            labels['team_id'] = team.get('id')

            # create the body of function with Label Fingerprint and Labels
            body = dict()
            body['labels'] = labels
            body['labelFingerprint'] = labelFingerprint

            update_disk_labels = self.client.disks().setLabels(project=self.credential.project,
                                                               zone=zone,
                                                               resource=resource_id,
                                                               body=body).execute()
            return self.wait_operation(operation=update_disk_labels.get('name'),
                                       zone=zone)
        except Exception as error:
            print(error)
            return False

    def _update_team_labels(self, vm_name, team_name):
        disks = dict()
        team = TeamClient(api_url=TEAM_API_URL, team_name=team_name)
        other_volumes = Volume.objects.filter(vm_name=vm_name)
        for v in other_volumes:
            status = self.update_labels(v.resource_id, v.zone, team.team)
            disks[v.resource_id] = status

        return disks


class CommandsGce(CommandsBase):

    _provider = None

    def __init__(self, provider):
        self._provider = provider

    def _mount(self, volume, fstab=True,
               host_vm=None, host_zone=None, *args, **kwargs):


        command = """try_loop=0;\
                     while [[ ! -L %(disk_path)s && $try_loop -lt 30 ]];\
                     do echo \"waiting symlink\"\
                     && sleep 3 && try_loop=$((try_loop + 1)); done"""

        # verify if volume is ex4 and create a fs
        command += """ && formatted=$(blkid -o value -s TYPE %(disk_path)s \
            | grep ext4 | wc -l);"""
        command += """if [ $formatted -eq 0 ]; \
            then  mkfs -t ext4 -F %(disk_path)s;fi"""

        if fstab:
            command += " && %s" % self.fstab_script(
                                    volume.path,
                                    self.data_directory)

        # mount disk
        command += " && systemctl daemon-reload "
        command += " && mkdir -p %(data_directory)s"
        command += " && mount %(disk_path)s %(data_directory)s"
        command = command % {
            "disk_path": volume.path,
            "data_directory": self.data_directory
        }

        return command

    def _umount(self, volume, data_directory=None, *args, **kw):
        return "umount %s" % data_directory

    def fstab_script(self, filer_path, mount_path):
        command = "/usr/bin/cp -f     /etc/fstab /etc/fstab.bkp"
        command += """ && sed \'/\{mount_path}/d\' \
             /etc/fstab.bkp > /etc/fstab"""
        command += ' && echo "{filer_path}  {mount_path}  \
              ext4 defaults    0   0" >> /etc/fstab'
        return command.format(mount_path=mount_path, filer_path=filer_path)

    def _resize2fs(self, volume):
        return "resize2fs {}".format(volume.path)

    def _clean_up(self, volume):
        return None

    def _rsync(self, snap, source_dir, target_ip, target_dir):
        script = self.die_if_error_script()
        snap_description = None
        if snap:
            snap_description = snap.description
        script += self.rsync_script(
            snap_dir=snap_description,
            source_dir=source_dir,
            target_ip=target_ip,
            target_dir=target_dir
        )
        return script

    def rsync_script(self, **kw):
        return """
            rsync -e "ssh -i /root/.ssh/dbaas.key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"  -aog {source_dir}/* root@{target_ip}:{target_dir} &
            die_if_error "Error rsync from {source_dir} to {target_ip}:{target_dir}"
            """.format(**kw)
