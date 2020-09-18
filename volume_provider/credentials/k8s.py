from volume_provider.credentials.base import CredentialBase, CredentialAdd


class CredentialK8s(CredentialBase):

    @property
    def pools(self):
        return self.content["pools"]

    @property
    def kube_config_path(self):
        return self.content['kube_config_path']

    @property
    def kube_config_content(self):
        return self.content['kube_config_content']

    def pool_add(self, name, token, endpoint, namespace=None, storage_type=None):
        credential = self.content
        if "pools" not in credential:
            credential["pools"] = {}
        if name in credential["pools"]:
            return False, "The {} are already registered".format(name)
        credential["pools"][name] = {
            "token": token,
            "endpoint": endpoint,
        }
        if namespace:
            credential["pools"][name]["namespace"] = namespace
        if storage_type:
            credential["pools"][name]["storage_type"] = storage_type
        self._content = credential
        self.save()
        return True, ""

    def pool_remove(self, name):
        credential = self.content
        if name not in credential["pools"]:
            return False, "The {} is not registered".format(name)
        del credential["pools"][name]
        self._content = credential
        self.save()
        return True, ""


class CredentialAddK8s(CredentialAdd):

    @property
    def valid_fields(self):
        return ['kube_config_path', 'kube_config_content']
