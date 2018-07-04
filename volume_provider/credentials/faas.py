from volume_provider.credentials.base import CredentialBase, CredentialAdd


class CredentialFaaS(CredentialBase):

    @property
    def user(self):
        return self.content['user']

    @property
    def password(self):
        return self.content['password']

    @property
    def endpoint(self):
        return self.content['endpoint']

    @property
    def project(self):
        return self.content['project']

    @property
    def is_secure(self):
        return self.content['is_secure']

    @property
    def category_id(self):
        return self.content['category_id']

    @property
    def access_type(self):
        return self.content['access_type']

    @property
    def token_endpoint(self):
        return self.content['token_endpoint']

    @property
    def tenant_id(self):
        return self.content['tenant_id']


class CredentialAddFaaS(CredentialAdd):

    def valid_fields(self):
        return [
            'environment', 'user', 'password', 'endpoint', 'is_secure',
            'category_id', 'access_type', 'token_endpoint', 'tenant_id'
        ]
