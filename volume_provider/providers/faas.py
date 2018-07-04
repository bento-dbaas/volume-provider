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

    def _create_volume(self, volume):
        export = self.client.create_export(volume.size_kb, volume.resource_id)
        volume.identifier = export['id']
        volume.resource_id = export['resource_id']
        volume.path = export['full_path']

    def _add_access(self, volume, to_address):
        self.client.create_access(volume, to_address)

    def _delete_volume(self, volume):
        self.client.delete_export(volume)

    def _remove_access(self, volume, to_address):
        self.client.delete_access(volume, to_address)

    def _resize(self, volume, new_size_kb):
        self.client.resize(volume, new_size_kb)
