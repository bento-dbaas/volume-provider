from volume_provider.models import Volume
from volume_provider.credentials.base import CredentialBase, CredentialAdd


class CredentialAWS(CredentialBase):

    @property
    def access_id(self):
        return self.content['access_id']

    @property
    def secret_key(self):
        return self.content['secret_key']

    @property
    def region(self):
        return self.content['region']

    @property
    def ebs_type(self):
        return self.content['ebs_type']

    @staticmethod
    def next_device(owner_address):
        base = '/dev/sd{}'
        linux_devices = ['f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p']
        for volume in Volume.objects.filter(owner_address=owner_address):
            device = volume.path[-1]
            if device in linux_devices:
                linux_devices.remove(device)
        print(linux_devices)
        return base.format(linux_devices[0])

    @property
    def iops(self):
        return self.content.get('iops', None)

    @property
    def force_detach(self):
        return self.content.get('force_detach', False)


class CredentialAddAWS(CredentialAdd):

    @property
    def valid_fields(self):
        return [
            'access_id', 'secret_key', 'region', 'ebs_type', 'device'
        ]
