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

   
    @patch('volume_provider.providers.gce.ProviderGce.get_disk')
    @patch('volume_provider.providers.gce.ProviderGce.build_client')
    @patch('volume_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_CREDENTIAL))
    @patch('volume_provider.providers.gce.ProviderGce._get_new_disk_name',
       new=MagicMock(return_value='fake_group-disk2'))
    def test_create_disk_flow(self, client_mock, get_disk_mock):
        disk_insert = client_mock().disks().insert().execute
        get_disk_mock.return_value = {'status': 'READY'}
        disk_insert.return_value = {'id': 'disk_id123'}

        created = self.provider._create_volume(self.disk)
        self.assertTrue(disk_insert.called)
        self.assertTrue(created)
        self.assertEqual(self.disk.path, '/dev/disk/by-id/google-disk2')
        self.assertEqual(self.disk.resource_id, 'fake_group-disk2')
        self.assertEqual(self.disk.identifier, disk_insert.return_value['id'])