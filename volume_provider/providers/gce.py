import json
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


class ProviderGce(ProviderBase):

    
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

    def __get_new_disk_name(self, volume):

        all_disks = self.client.instances().get(
            project=self.credential.project,
            zone=volume.zone,
            instance=volume.vm_name
        ).execute().get('disks')

        disk_names = [x['deviceName'] for x in all_disks]

        if len(disk_names) == 1:
            disk_name = "data1"
        else:
            disk_name = "data%s" % (int(disk_names[-1].split("data")[1]) + 1)
                
        return "%s-%s" % (volume.vm_name, disk_name)
    
    def _create_volume(self, volume, snapshot=None, *args, **kwargs):
        disk_name = self.__get_new_disk_name(volume) 
        
        config = {
            'name': disk_name,
            'sizeGb': volume.convert_kb_to_gb(volume.size_kb, to_int=True),
            'labels': {
                'group': volume.group
            }
        }

        if snapshot:
            config['sourceSnapshot'] = "global/snapshots/%s" % (snapshot.description)

        disk_create = self.client.disks().insert(
            project=self.credential.project,
            zone=volume.zone,
            body=config
        ).execute()
        
        volume.identifier = disk_create.get('id')
        volume.resource_id = disk_name
        volume.path = "/dev/disk/by-id/google-%s" % self.get_device_name(disk_name)

        return self.__wait_disk_create(volume)
    
    def _add_access(self, volume, to_address, *args, **kwargs):
        pass

    def _delete_volume(self, volume):
        '''
            this mehtod detach and delete disks
            in 'happy flow' it does not necessary
            because we use "autoDelete" attr on disk attach
            the code below is usefull in snapshot restore
            abd rollback command,
            When we got an error on mount command.
        '''
        try:
            self.client.instances().detachDisk(
                    project=self.credential.project,
                    zone=volume.zone,
                    instance=volume.vm_name,
                    deviceName=self.get_device_name(volume.resource_id)
            ).execute()
        except HttpError:
            pass
        else:
            self.__wait_disk_detach(volume)
        
        try:
            self.client.disks().delete(
                project=self.credential.project,
                zone=volume.zone,
                disk=volume.resource_id
            ).execute()
        except HttpError:
            pass
        
        return
    
    def _resize(self, volume, new_size_kb):
        if new_size_kb <= volume.size_kb:
            raise Exception("New size must be greater than current size")

        config = {
            "sizeGb": volume.convert_kb_to_gb(new_size_kb, to_int=True)
        }
        self.client.disks().resize(
            project=self.credential.project,
            zone=volume.zone,
            disk=volume.resource_id,
            body=config
        ).execute()

        return
    def __verify_none(self, dict_var, key, var):
        if var:
            dict_var[key] = var

    def __get_snapshot_name(self, volume):
        return "s-%(volume_name)s-%(timestamp)s" % {
            'volume_name': volume.resource_id.replace('-',''),
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
        self.__verify_none(ex_metadata, TAG_BACKUP_DBAAS.lower(), 1)
        
        config = {
            'labels': ex_metadata,
            'name': snapshot_name
        }

        new_snapshot = self.client.disks().createSnapshot(
            project=self.credential.project,
            zone=volume.zone,
            disk=volume.resource_id,
            body=config
        ).execute()

        snapshot.identifier = new_snapshot.get('id')
        snapshot.description = snapshot_name
        return
    
    def _get_snapshot_status(self, snapshot):
        ss = self.client.snapshots().get(
            project=self.credential.project,
            snapshot=snapshot.description
        ).execute()
            
        return ss.get('status')
    
    def _remove_snapshot(self, snapshot, *args, **kwrgs):
        self.client.snapshots().delete(
            project=self.credential.project,
            snapshot=snapshot.description
        ).execute()
    
        return True

    def _restore_snapshot(self, snapshot, volume):
        return self._create_volume(volume, snapshot=snapshot)

    def stop_instance(self, volume):
        self.client.instances().stop(
            project=self.credential.project,
            zone=volume.zone,
            instance=volume.vm_name
        ).execute() 

        return self.__wait_instance_status(volume, 'TERMINATED')

    def get_disk(self, volume):

        return self.client.disks().get(
            project=self.credential.project,
            zone=volume.zone,
            disk=volume.resource_id
        ).execute()
    
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
        disk = self.get_disk(volume)
        
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
    
    def __wait_instance_status(self, volume, status):
        while self.get_instance_status(volume) != status:
            sleep(5)

        return True
    
    def __wait_disk_detach(self, volume):
        detached = False
        while not detached:
            try:
                disk = self.get_disk(volume)
            except HttpError:
                return False

            if not disk.get('lastDetachTimestamp')\
             and disk.get('lastAttachTimestamp'):
                sleep(3)
            else:
                detached = True

        return True

    def __wait_disk_create(self, volume, retry_not_found=3):
        while self.get_disk(volume).get('status') != "READY":
            sleep(3)

        return True
    
    def __wait_disk_attach(self, volume):
        attach = False
        while not attach:
            disk = self.get_disk(volume)
            if not disk.get('lastAttachTimestamp'):
                sleep(3)
            else:
                attach = True
   
class CommandsGce(CommandsBase):

    def __init__(self, provider):
        self.provider = provider
    
    def _mount(self, volume, fstab=True, *args, **kw):
        self.provider.attach_disk(volume)

        # waiting symlink creation
        command = """while ! [[ -L "%(disk_path)s" ]];do echo "waiting symlink" && sleep 3; done"""

        # verify if volume is ex4 and create a fs
        command += """ && formatted=$(blkid -o value -s TYPE %(disk_path)s | grep ext4 | wc -l);"""
        command += """if [ "$formatted" -eq 0 ]; then  mkfs -t ext4 -F %(disk_path)s;fi"""

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
        command += " && sed \'/\{mount_path}/d\' /etc/fstab.bkp > /etc/fstab"
        command += ' && echo "{filer_path}  {mount_path}    ext4 defaults    0   0" >> /etc/fstab'
        return command.format(mount_path=mount_path, filer_path=filer_path)

        

    
