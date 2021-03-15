import json
import logging
from datetime import datetime
from time import sleep

from os import getenv
from collections import namedtuple
from time import sleep

from googleapiclient.errors import HttpError

import googleapiclient.discovery
from google.oauth2 import service_account

from volume_provider.settings import AWS_PROXY, TAG_BACKUP_DBAAS
from volume_provider.credentials.gce import CredentialGce, CredentialAddGce
from volume_provider.providers.base import ProviderBase, CommandsBase
from volume_provider.clients.team import TeamClient


LOG = logging.getLogger(__name__)


class ProviderGce(ProviderBase):

    seconds_to_wait = 3

    def get_commands(self):
        return CommandsGce(self)

    @classmethod
    def get_provider(cls):
        return 'gce'

    def build_client(self):
        service_account_data = self.credential.service_account
        service_account_data['private_key'] = service_account_data[
            'private_key'
        ].replace('\\n', '\n')
        credentials = service_account.Credentials.from_service_account_info(
            service_account_data
        )
        credentials
        return googleapiclient.discovery.build(
            'compute', 'v1', credentials=credentials
        )

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
        disk_name = "data%s" % (int(all_disks[-1].split("data")[1]) + 1)\
                    if len(all_disks)\
                    else "data1"

        return "%s-%s" % (volume.group, disk_name)

    def _create_volume(self, volume, snapshot=None, *args, **kwargs):
        disk_name = self._get_new_disk_name(volume)

        config = {
            'name': disk_name,
            'sizeGb': volume.convert_kb_to_gb(volume.size_kb, to_int=True),
            'labels': {
                'group': volume.group
            }
        }

        if snapshot:
            config['sourceSnapshot'] = "global/snapshots/%s" % \
                (snapshot.description)

        disk_create = self.client.disks().insert(
            project=self.credential.project,
            zone=volume.zone,
            body=config
        ).execute()

        volume.identifier = disk_create.get('id')
        volume.resource_id = disk_name
        volume.path = "/dev/disk/by-id/google-%s" % \
            self.get_device_name(disk_name)

        return self.__wait_disk_create(volume)

    def _add_access(self, volume, to_address, *args, **kwargs):
        pass

    def __destroy_volume(self, volume, snapshot_offset=0):

        self._detach_disk(volume)

        '''
        snapshots = self.get_snapshots_from(
            offset=snapshot_offset,**{'volume': volume}
        )
        for snap in snapshots:
            self._remove_snapshot(snap)
            snap.delete()
        '''

        self.client.disks().delete(
            project=self.credential.project,
            zone=volume.zone,
            disk=volume.resource_id
        ).execute()

        return True

    def _resize(self, volume, new_size_kb):
        if new_size_kb <= volume.size_kb:
            raise EnvironmentError(
                "New size must be greater than current size"
            )

        config = {
            "sizeGb": volume.convert_kb_to_gb(new_size_kb, to_int=True)
        }
        self.client.disks().resize(
            project=self.credential.project,
            zone=volume.zone,
            disk=volume.resource_id,
            body=config
        ).execute()

        return True

    def __verify_none(self, dict_var, key, var):
        if var and key:
            dict_var[key] = var

    def __get_snapshot_name(self, volume):
        return "ss-%(volume_name)s-%(timestamp)s" % {
            'volume_name': volume.resource_id.replace('-', ''),
            'timestamp': datetime.now().strftime('%Y%m%d%H%M%S%f')
        }

    def _take_snapshot(self, volume, snapshot, team, engine, db_name):
        snapshot_name = self.__get_snapshot_name(volume)

        ex_metadata = {}
        if team and engine:
            ex_metadata = TeamClient.make_tags(team, engine)
        self.__verify_none(ex_metadata, 'engine', engine)
        self.__verify_none(ex_metadata, 'db_name', db_name)
        self.__verify_none(ex_metadata, 'team', team)
        self.__verify_none(
            ex_metadata,
            TAG_BACKUP_DBAAS.lower() if TAG_BACKUP_DBAAS else None,
            1
        )
        ex_metadata['group'] = volume.group

        snapshot.labels = ex_metadata
        snapshot.description = snapshot_name

        config = {
            'labels': ex_metadata,
            'name': snapshot_name,
            "storageLocations": [self.credential.region]
        }

        oeration = self.client.disks().createSnapshot(
            project=self.credential.project,
            zone=volume.zone,
            disk=volume.resource_id,
            body=config
        ).execute()

        self._wait_zone_operation(volume.zone, oeration.get('name'))

        snap = self.client.snapshots().get(
            project=self.credential.project,
            snapshot=snapshot_name
        ).execute()

        snapshot.identifier  = snap.get('id')
        snapshot.size_bytes = snap.get('downloadBytes')

    def _remove_snapshot(self, snapshot, *args, **kwrgs):
        oeration = self.client.snapshots().delete(
                project=self.credential.project,
                snapshot=snapshot.description
        ).execute()
        self._wait_global_operation(oeration.get('name'))
        return True

    def _restore_snapshot(self, snapshot, volume):
        return self._create_volume(volume, snapshot=snapshot)

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

    def attach_disk(self, volume):
        disk = self.get_disk(volume.resource_id, volume.zone)

        config = {
            "source": disk.get('selfLink'),
            "deviceName": self.get_device_name(volume.resource_id),
            "autoDelete": True
        }

        self.client\
            .instances().attachDisk(
                project=self.credential.project,
                zone=volume.zone,
                instance=volume.vm_name,
                body=config
            ).execute()

        return self.__wait_disk_attach(volume)

    def _detach_disk(self, volume):
        self.client.instances().detachDisk(
                project=self.credential.project,
                zone=volume.zone,
                instance=volume.vm_name,
                deviceName=self.get_device_name(volume.resource_id)
        ).execute()
        self.__wait_disk_detach(volume)

    def _move_volume(self, volume, zone):
        if volume.zone == zone:
            return True

        config = {
            "targetDisk": "zones/%(zone)s/disks/%(disk_name)s" % {
                "zone": volume.zone,
                "disk_name": volume.resource_id
            },
            "destinationZone": "zones/%s" % zone
        }
        self.client.projects().moveDisk(
            project=self.credential.project,
            body=config
        ).execute()

        return self.__wait_disk_move(volume, zone)

    def __wait_disk_move(self, volume, zone):
        disk_previous = self.get_disk(
            volume.resource_id,
            volume.zone,
            execute_request=False
        )

        disk_next = self.get_disk(
            volume.resource_id,
            zone,
            execute_request=False
        )

        # waiting for 404
        while True:
            try:
                disk_previous.execute()
            except HttpError as ex:
                if ex.resp.status == 404:
                    break
                else:
                    raise(ex)
            sleep(self.seconds_to_wait)

        while True:
            try:
                disk = disk_next.execute()
                if disk.get('status') == "READY":
                    break
            except HttpError as ex:
                if ex.resp.status == 404:
                    pass
                else:
                    raise Exception(ex)
            sleep(self.seconds_to_wait)
        return True

    def __wait_instance_status(self, volume, status):
        while self.get_instance_status(volume) != status:
            sleep(self.seconds_to_wait)

        return True

    def __wait_disk_detach(self, volume):
        '''while self.get_device_name(volume.resource_id) in\
         self.__get_instance_disks(volume.zone, volume.vm_name):
            sleep(self.seconds_to_wait)'''
        while self.client.disks().get(
            project=self.credential.project,
            zone=volume.zone,
            disk=volume.resource_id
        ).execute().get("users"):
            sleep(self.seconds_to_wait)

        return True

    def __wait_disk_create(self, volume):
        while self.get_disk(
            volume.resource_id,
            volume.zone
        ).get('status') != "READY":
            sleep(self.seconds_to_wait)

        return True

    def __wait_disk_attach(self, volume):
        attach = False
        while not attach:
            disk = self.get_disk(volume.resource_id, volume.zone)
            if not disk.get('lastAttachTimestamp'):
                sleep(self.seconds_to_wait)
            else:
                attach = True

    def _delete_old_volume(self, volume):
        return self.__destroy_volume(volume, snapshot_offset=1)

    def _delete_volume(self, volume):
        # self._remove_all_snapshots(volume.group)
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

    def _check_operation_status(self, operation):

        if operation.get('error'):
            error = 'Error in {} operation: {}'.format(
                operation.get('operationType'),
                operation.get('error')
            )
            raise Exception(error)

        if operation.get('status') != 'DONE':
            error = 'Operation {} is not Done. Status: {}'.format(
                operation.get('operationType'),
                operation.get('status')
            )
            raise Exception(error)

    def _wait_zone_operation(self, zone, operation):
        op = self.client.zoneOperations().wait(
            project=self.credential.project,
            zone=zone,
            operation=operation
        ).execute()
        self._check_operation_status(op)

    def _wait_global_operation(self, operation):
        op = self.client.globalOperations().wait(
            project=self.credential.project,
            operation=operation
        ).execute()
        self._check_operation_status(op)


class CommandsGce(CommandsBase):

    def __init__(self, provider):
        self.provider = provider

    def _mount(self, volume, fstab=True,
               host_vm=None, host_zone=None, *args, **kwargs):

        volume.vm_name = host_vm or volume.vm_name
        volume.zone = host_zone or volume.zone
        volume.save()

        self.provider.attach_disk(volume)

        # waiting symlink creation
        command = """while ! [[ -L "%(disk_path)s" ]];\
            do echo "waiting symlink" && sleep 3; done"""

        # verify if volume is ex4 and create a fs
        command += """ && formatted=$(blkid -o value -s TYPE %(disk_path)s \
            | grep ext4 | wc -l);"""
        command += """if [ "$formatted" -eq 0 ]; \
            then  mkfs -t ext4 -F %(disk_path)s;fi"""

        # mount disk
        command += " && mount %(disk_path)s %(data_directory)s"
        command = command % {
            "disk_path": volume.path,
            "data_directory": self.data_directory
        }

        if fstab:
            command += " && %s" % self.fstab_script(
                                    volume.path,
                                    self.data_directory)

        return command

    def _umount(self, volume, data_directory=None, *args, **kw):
        return "umount %s" % data_directory

    def fstab_script(self, filer_path, mount_path):
        command = "cp /etc/fstab /etc/fstab.bkp"
        command += """ && sed \'/\{mount_path}/d\' \
             /etc/fstab.bkp > /etc/fstab"""
        command += ' && echo "{filer_path}  {mount_path}  \
              ext4 defaults    0   0" >> /etc/fstab'
        return command.format(mount_path=mount_path, filer_path=filer_path)
