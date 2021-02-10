from volume_provider.credentials.base import CredentialBase, CredentialAdd


class CredentialGce(CredentialBase):
    @property
    def project(self):
        return self.content['project']
class CredentialAddGce(CredentialAdd):

    @property
    def valid_fields(self):
        return []