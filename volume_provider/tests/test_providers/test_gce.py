from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, MagicMock, PropertyMock
from volume_provider.providers.gce import ProviderGce
from volume_provider.credentials.gce import CredentialAddGce
from volume_provider.models import Volume
from .fakes.gce import *
from .base import GCPBaseTestCase

import googleapiclient


ENVIRONMENT = "dev"
ENGINE = "redis"


# @patch(
#     'volume_provider.providers.gce.HOST_ORIGIN_TAG',
#     new=str('dbaas')
# )
class TestCredentialGCE(GCPBaseTestCase):

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

    @patch(
        'volume_provider.providers.gce.CredentialGce.get_content'
    )
    def test_build_client(self, content):
        self.build_credential_content(content)

        self.assertEqual(
            type(self.provider.build_client()), googleapiclient.discovery.Resource
        )

    def build_credential_content(self, content, **kwargs):
        values = deepcopy(FAKE_CREDENTIAL)
        values.update(kwargs)
        content.return_value = values

class CreateVolumeTestCase(GCPBaseTestCase):
    
    @patch('volume_provider.providers.gce.ProviderGce._get_volumes')
    def test_get_disk_name(self, volume_list):
        volume_list.return_value = FAKE_DISK_LIST
        disk_name = self.provider._get_new_disk_name(self.disk)
        self.assertEqual(disk_name, 'fake_group-data3')
    

    @patch('volume_provider.providers.gce.ProviderGce._get_volumes')
    def test_get_disk_name_first_disk(self, volume_list):
        volume_list.return_value = []
        disk_name = self.provider._get_new_disk_name(self.disk)
        self.assertEqual(disk_name, 'fake_group-data1')

   
