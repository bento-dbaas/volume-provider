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

    def __get_new_disk_name(self, project, zone):
        all_disks = self.client.disks().list(
            project=self.credential.project,
            zone=zone,
        )
        # @TODO - improve query params
        all_disks.uri = "%s&orderBy=creationTimestamp%%20desc" % (all_disks.uri)
        all_disks = all_disks.execute().get('items')

        name = all_disks[ len(all_disks) - 1 ].get('name')
        return "%s-data%s" % (name, len(all_disks))
    
    def _create_volume(self, volume, snapshot=None, zone=None, size_kb=None, *args, **kwargs):
        disk_name = self.__get_new_disk_name(
                         project=self.credential.project, 
                         zone=zone)
        
        config = {
            'name': disk_name,
            'sizeGb': int(size_kb / 1000)
        }

        disk_create = self.client.disks().insert(
            project=self.credential.project,
            zone=zone,
            body=config
        ).execute()
        
        volume.identifier = disk_create.get('id')
        volume.resource_id = disk_create.get('name')
        volume.path = "%s/" % disk_name

        return
    
    def _add_access(self, volume, to_address):
        pass
   
class CommandsGce(CommandsBase):

    def __init__(self, provider):
        self.provider = provider

    
