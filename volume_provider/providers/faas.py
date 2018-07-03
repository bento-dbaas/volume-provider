from volume_provider.credentials.faas import CredentialFaaS, CredentialAddFaaS
from volume_provider.providers.base import ProviderBase
from volume_provider.clients.faas import FaaSClient


class ProviderFaaS(ProviderBase):

    @classmethod
    def get_provider(cls):
        return 'FaaS'

    def build_client(self):
        return FaaSClient(self.credential)

    def build_credential(self):
        return CredentialFaaS(self.provider, self.environment)

    def get_credential_add(self):
        return CredentialAddFaaS



