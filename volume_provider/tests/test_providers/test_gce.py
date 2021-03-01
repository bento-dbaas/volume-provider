from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, MagicMock, PropertyMock
from volume_provider.providers.gce import ProviderGce
from volume_provider.credentials.gce import CredentialAddGce
from .fakes.gce import FAKE_TAGS, FAKE_CREDENTIAL


ENVIRONMENT = "dev"
ENGINE = "redis"


# @patch(
#     'volume_provider.providers.gce.HOST_ORIGIN_TAG',
#     new=str('dbaas')
# )
class TestCredentialGCE(TestCase):

    def setUp(self):
        self.provider = ProviderGce(ENVIRONMENT, ENGINE)
        self.provider.wait_state = MagicMock()

    def test_provider_name(self):
        self.assertEqual(self.provider.get_provider(), 'gce')

    def test_get_credential_add(self):
        self.assertEqual(
            self.provider.get_credential_add(), CredentialAddGce
        )
    def test_validate_credential(self):
        invalid_content = deepcopy(FAKE_CREDENTIAL)
        success, error = self.provider.credential_add(invalid_content)

        self.assertFalse(success)
        self.assertIn("Required fields",error)


