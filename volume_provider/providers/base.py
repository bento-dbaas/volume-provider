from volume_provider.models import Volume, Snapshot


class ProviderBase(object):

    def __init__(self, environment):
        self.environment = environment
        self._client = None
        self._credential = None
        self._commands = None

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
    def commands(self):
        if not self._commands:
            self._commands = self.get_commands()
        return self._commands

    def get_commands(self):
        raise NotImplementedError

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

    def delete_volume(self, identifier):
        volume = Volume.objects(identifier=identifier).get()
        self._delete_volume(volume)
        volume.delete()

    def _delete_volume(self, volume):
        raise NotImplementedError

    def add_access(self, identifier, to_address):
        volume = Volume.objects(identifier=identifier).get()
        self._add_access(volume, to_address)

    def _add_access(self, volume, to_address):
        raise NotImplementedError

    def remove_access(self, identifier, to_address):
        volume = Volume.objects(identifier=identifier).get()
        self._remove_access(volume, to_address)

    def _remove_access(self, volume, to_address):
        raise NotImplementedError

    def resize(self, identifier, new_size_kb):
        volume = Volume.objects(identifier=identifier).get()
        self._resize(volume, new_size_kb)
        volume.size_kb = new_size_kb
        volume.save()

    def _resize(self, volume, new_size_kb):
        raise NotImplementedError

    def take_snapshot(self, identifier):
        volume = Volume.objects(identifier=identifier).get()
        snapshot = Snapshot(volume=volume)
        self._take_snapshot(volume, snapshot)
        snapshot.save()
        return snapshot

    def _take_snapshot(self, volume, snapshot):
        raise NotImplementedError

    def remove_snapshot(self, identifier):
        snapshot = Snapshot.objects(identifier=identifier).get()
        self._remove_snapshot(snapshot)
        snapshot.delete()

    def _remove_snapshot(self, snapshot):
        raise NotImplementedError

    def restore_snapshot(self, identifier):
        snapshot = Snapshot.objects(identifier=identifier).get()
        volume = Volume()
        volume.size_kb = snapshot.volume.size_kb
        volume.set_group(snapshot.volume.group)
        volume.owner_address = snapshot.volume.owner_address
        self._restore_snapshot(snapshot, volume)
        volume.save()
        return volume

    def _restore_snapshot(self, snapshot, volume):
        raise NotImplementedError


class CommandsBase(object):

    @property
    def data_directory(self):
        return "/data"

    def mount(self, identifier):
        volume = Volume.objects(identifier=identifier).get()
        return self._mount(volume)

    def _mount(self, volume):
        raise NotImplementedError

    def clean_up(self, identifier):
        volume = Volume.objects(identifier=identifier).get()
        return self._clean_up(volume)

    def _clean_up(self, volume):
        raise NotImplementedError
