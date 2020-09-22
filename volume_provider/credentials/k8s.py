from volume_provider.credentials.base import CredentialBase, CredentialAdd


class CredentialK8s(CredentialBase):
    pass


class CredentialAddK8s(CredentialAdd):

    @property
    def valid_fields(self):
        return []
