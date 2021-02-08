from volume_provider.credentials.base import CredentialBase, CredentialAdd


class CredentialGce(CredentialBase):
    @property
    def project(self):
        return self.content['project']

    @property
    def availability_zones(self):
        return self.content['availability_zones']

    @property
    def _zones_field(self):
        return self.availability_zones


class CredentialAddGce(CredentialAdd):

    @property
    def valid_fields(self):
        return []