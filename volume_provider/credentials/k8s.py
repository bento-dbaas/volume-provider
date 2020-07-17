from volume_provider.credentials.base import CredentialBase, CredentialAdd


class CredentialK8s(CredentialBase):

    @property
    def kube_config_path(self):
        return self.content['kube_config_path']

    @property
    def kube_config_content(self):
        return self.content['kube_config_content']


class CredentialAddK8s(CredentialAdd):

    @property
    def valid_fields(self):
        return ['kube_config_path', 'kube_config_content']
