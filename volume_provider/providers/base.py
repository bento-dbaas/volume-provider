from volume_provider.models import Volume


class ProviderBase(object):

    def __init__(self, environment):
        self.environment = environment
        self._client = None
        self._credential = None

    @property
    def client(self):
        if not self._client:
            self._client = self.build_client()
        return self._client

    @property
    def credential(self):
        if not self._credential:
            self._credential = self.build_credential()
        return self._credential

    def credential_add(self, content):
        credential_cls = self.get_credential_add()
        credential = credential_cls(self.provider, self.environment, content)
        is_valid, error = credential.is_valid()
        if not is_valid:
            return False, error

        try:
            insert = credential.save()
        except Exception as e:
            return False, str(e)
        else:
            return True, insert.get('_id')

    @property
    def provider(self):
        return self.get_provider()

    @classmethod
    def get_provider(cls):
        raise NotImplementedError

    def build_client(self):
        raise NotImplementedError

    def build_credential(self):
        raise NotImplementedError

    def get_credential_add(self):
        raise NotImplementedError

    def create_volume(self, group, size_kb, to_address):
        volume = Volume()
        volume.size_kb = size_kb
        volume.set_group(group)
        volume.owner_address = to_address
        self._create_volume(volume)
        self._add_access(volume, volume.owner_address)
        volume.save()

        return volume

    def _create_volume(self, volume):
        raise NotImplementedError

    def delete_volume(self, uuid):
        volume = Volume.objects(pk=uuid).get()
        self._delete_volume(volume)
        volume.delete()

    def _delete_volume(self, volume):
        raise NotImplementedError

    def add_access(self, uuid, to_address):
        volume = Volume.objects(pk=uuid).get()
        self._add_access(volume, to_address)

    def _add_access(self, volume, to_address):
        raise NotImplementedError
