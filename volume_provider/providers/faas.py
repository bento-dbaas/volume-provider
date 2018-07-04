from logging import info
from mongoengine import Document, StringField, IntField
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
        volume = FaaSVolume()
        volume.size_kb = size_kb
        volume.set_group(group)

        export = self.client.create_export(volume.size_kb, volume.resource_id)
        info("Export created: {}".format(export))
        volume.identifier = export['id']
        volume.resource_id = export['resource_id']
        volume.path = export['full_path']
        volume.owner_address = to_address
        volume.save()

        return volume


class FaaSVolume(Document):
    size_kb = IntField(max_length=255, required=True)
    group = StringField(max_length=50, required=True)
    resource_id = StringField(max_length=255, required=True)
    identifier = IntField(required=True)
    path = StringField(max_length=1000, required=True)
    owner_address = StringField(max_length=20, required=True)

    def set_group(self, group):
        self.group = group
        pair = FaaSVolume.objects(group=group).first()
        if pair:
            self.resource_id = pair.resource_id

    @property
    def uuid(self):
        return str(self.pk)
