from collections import OrderedDict
from unittest import TestCase
from unittest.mock import patch
from volume_provider.settings import MONGODB_HOST, MONGODB_PORT, MONGODB_USER, \
    MONGODB_PWD
from volume_provider.credentials.base import CredentialAdd, CredentialBase
from volume_provider.tests.test_credentials import CredentialAddFake, CredentialBaseFake, \
    FakeMongoDB


PROVIDER = "fake"
ENVIRONMENT = "dev"
FAKE_CERT_PATH = "/path/to/certs/"
GROUP = "fake-group"


class TestBaseProvider(TestCase):

    def tearDown(self):
        FakeMongoDB.clear()

    def test_base_content(self):
        credential_add = CredentialAddFake(
            PROVIDER, ENVIRONMENT, {"fake": "info"}
        )
        credential_add.save()
        credential = CredentialBaseFake(PROVIDER, ENVIRONMENT)
        self.assertIsNone(credential._content)
        self.assertEqual(credential.content, credential._content)
        self.assertIsNotNone(credential.content)

    def test_base_content_empty(self):
        credential = CredentialBaseFake(PROVIDER, ENVIRONMENT + "-new")
        self.assertIsNone(credential._content)
        self.assertRaises(NotImplementedError, credential.get_content)


    @patch('base_provider.baseCredential.MongoClient')
    def test_mongo_db_connection(self, mongo_client):
        credential = CredentialBase(PROVIDER, ENVIRONMENT)
        self.assertIsNotNone(credential.credential)
        self.assertIsNotNone(credential.db)
        mongo_client.assert_called_once_with(
            host=MONGODB_HOST, port=MONGODB_PORT,
            username=MONGODB_USER, password=MONGODB_PWD,
            document_class=OrderedDict
        )

    @patch('volume_provider.credentials.base.CredentialAdd.credential')
    def test_delete(self, credential):
        env = "env"
        provider = "fake"
        CredentialAdd(provider, env, {}).delete()
        credential.delete_one.assert_called_once_with({
            "environment": env, "provider": provider
        })
