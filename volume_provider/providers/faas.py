from volume_provider.models import Volume
from volume_provider.credentials.faas import CredentialFaaS, CredentialAddFaaS
from volume_provider.providers.base import ProviderBase
from volume_provider.clients.faas import FaaSClient


class ProviderFaaS(ProviderBase):

    @classmethod
    def get_provider(cls):
        return 'faas'

    def build_client(self):
        return FaaSClient(self.credential)

    def build_credential(self):
        return CredentialFaaS(self.provider, self.environment)

    def get_credential_add(self):
        return CredentialAddFaaS

    def create_volume(self, group, size_kb, to_address):
        volume = Volume()
        volume.size_kb = size_kb
        volume.set_group(group)

        export = self.client.create_export(volume.size_kb, volume.resource_id)
        volume.identifier = export['id']
        volume.resource_id = export['resource_id']
        volume.path = export['full_path']
        volume.owner_address = to_address
        volume.save()

        self.client.create_access(volume, to_address)

        return volume
