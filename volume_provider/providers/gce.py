from os import getenv
from collections import namedtuple
from time import sleep

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

    def __get_new_disk_name(self, volume,project):

        all_disks = self.client.instances().get(
            project=self.credential.project,
            zone=volume.zone,
            instance=volume.vm_name
        ).execute().get('disks')

        return "%s-data%s" % (volume.vm_name, len(all_disks))
    
    def _create_volume(self, volume, snapshot=None, *args, **kwargs):
        disk_name = self.__get_new_disk_name(
                         volume,
                         project=self.credential.project)
        
        
        config = {
            'name': disk_name,
            'sizeGb': int(volume.size_kb / 1000),
            'labels': {
                'group': volume.group
            }
        }

        disk_create = self.client.disks().insert(
            project=self.credential.project,
            zone=volume.zone,
            body=config
        ).execute()
        
        volume.identifier = disk_create.get('id')
        volume.resource_id = disk_name
        volume.path = "/%s" % disk_name

        return
    
    def _add_access(self, volume, to_address):
        pass
   
class CommandsGce(CommandsBase):

    def __init__(self, provider):
        self.provider = provider
    
    def _mount(self, volume, *args, **kw):
        print(volume.vm_name)

        disk = self.provider.client.disks().get(
            project=self.provider.credential.project,
            zone=volume.zone,
            disk=volume.resource_id
        ).execute()

        
        config = {
            "source": disk.get('selfLink')
        }

        instance = self.provider.client\
                    .instances().attachDisk(
                        project=self.provider.credential.project,
                        zone=volume.zone,
                        instance=volume.vm_name,
                        body=config
                    ).execute()
        

        print(instance, dir(instance))

        

    
