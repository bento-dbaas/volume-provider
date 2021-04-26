from volume_provider.credentials.base import CredentialBase, CredentialAdd


class CredentialGce(CredentialBase):

    @property
    def project(self):
        return self.content['project']

    @property
    def service_account(self):
        return self.content['service_account']

    @property
    def scopes(self):
        return self.content['scopes']

    @property
    def region(self):
        return self.content['region']


class CredentialAddGce(CredentialAdd):
    @property
    def valid_fields(self, *args, **kwargs):
        return ['provider', 'service_account',
                'environment', 'offerings',
                'project', 'availability_zones', 'subnetwork',
                'templates', 'region', 'scopes']
