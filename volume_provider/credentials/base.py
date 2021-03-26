from volume_provider.settings import MONGODB_PARAMS, MONGODB_DB
from base_provider import BaseCredential
from base_provider.base import ReturnDocument

class CredentialMongoDB(BaseCredential):

    def __init__(self, provider, environment):
        super(CredentialMongoDB, self).__init__(
            'volume_provider',
            provider,
            environment
        )
        self.MONGODB_PARAMS = MONGODB_PARAMS
        self.MONGODB_DB = MONGODB_DB


class CredentialBase(CredentialMongoDB):

    def get_content(self):
        content = self.credential.find_one({
            "provider": self.provider,
            "environment": self.environment,
        })
        if content:
            return content

        raise NotImplementedError("No {} credential for {}".format(
            self.provider, self.environment
        ))

    @property
    def content(self):
        if not self._content:
            self._content = self.get_content()
        
        return super(CredentialBase, self).content

    def get_by(self, **kwargs):
        return self.credential.find({'provider': self.provider, **kwargs})

    def all(self, **kwargs):
        return self.get_by()

    def delete(self):
        return self.credential.remove({
            'provider': self.provider,
            'environment': self.environment
        })


class CredentialAdd(CredentialMongoDB):

    def __init__(self, provider, environment, content):
        super(CredentialAdd, self).__init__(provider, environment)
        self._content = content

    def save(self):
        return self.credential.find_one_and_update(
            {
                'provider': self.provider,
                'environment': self.environment
            },
            {'$set': {
                'provider': self.provider,
                'environment': self.environment,
                **self.content
            }},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

    def delete(self):
        return self.credential.delete_one({
            'provider': self.provider, 'environment': self.environment
        })

    @property
    def valid_fields(self):
        raise NotImplementedError

    def is_valid(self):
        error = "Required fields {}".format(self.valid_fields)
        if len(self.valid_fields) != len(self.content.keys()):
            return False, error

        for field in self.valid_fields:
            if field not in self.content:
                return False, error

        return True, ''
