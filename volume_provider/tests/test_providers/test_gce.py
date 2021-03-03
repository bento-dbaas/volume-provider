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
    
    @patch('volume_provider.providers.gce.ProviderGce._get_volumes',
        new=MagicMock(return_value=FAKE_DISK_LIST))
    def test_get_disk_name(self):
        disk_name = self.provider._get_new_disk_name(self.disk)
        self.assertEqual(disk_name, 'fake_group-data3')
    

    @patch('volume_provider.providers.gce.ProviderGce._get_volumes',
        new=MagicMock(return_value=[]))
    def test_get_disk_name_first_disk(self):
        disk_name = self.provider._get_new_disk_name(self.disk)
        self.assertEqual(disk_name, 'fake_group-data1')

   
    @patch('volume_provider.providers.gce.ProviderGce.build_client')
    @patch('volume_provider.providers.gce.CredentialGce.get_content',
        new=MagicMock(return_value=FAKE_CREDENTIAL))
    @patch('volume_provider.providers.gce.ProviderGce.get_disk',
        new=MagicMock(return_value={'status': 'READY'}))
    @patch('volume_provider.providers.gce.ProviderGce._get_new_disk_name',
        new=MagicMock(return_value='fake_group-disk2'))
    def test_create_disk_flow(self, client_mock):
        disk_insert = client_mock().disks().insert().execute
        disk_insert.return_value = {'id': 'disk_id123'}

        created = self.provider._create_volume(self.disk)
        self.assertTrue(disk_insert.called_once)
        self.assertTrue(created)
        self.assertEqual(self.disk.path, '/dev/disk/by-id/google-disk2')
        self.assertEqual(self.disk.resource_id, 'fake_group-disk2')
        self.assertEqual(self.disk.identifier, disk_insert.return_value['id'])
    

    def test_resize_disk_wrong_size(self):
        with self.assertRaises(EnvironmentError):
            self.provider._resize(self.disk, 1000)
        
    @patch('volume_provider.providers.gce.ProviderGce.build_client')
    @patch('volume_provider.providers.gce.CredentialGce.get_content',
        new=MagicMock(return_value=FAKE_CREDENTIAL))
    def test_resize_disk(self, client_mock):
        disk_resize = client_mock().disks().resize().execute
        resized = self.provider._resize(self.disk, 10000000)

        self.assertTrue(disk_resize.called_once)
        self.assertTrue(resized)
    
    @patch('volume_provider.providers.gce.ProviderGce.build_client')
    @patch('volume_provider.providers.gce.CredentialGce.get_content',
        new=MagicMock(return_value=FAKE_CREDENTIAL))
    @patch('volume_provider.providers.gce.ProviderGce.get_snapshots_from',
        new=MagicMock(return_value=[]))
    def test_delete_disk(self, client_mock):
        disk_delete = client_mock().disks().delete().execute
        disk_detach = client_mock().instances().detachDisk().execute
        snapshots_list = client_mock().snapshots().list().execute
        snapshots_delete = client_mock().snapshots().delete().execute

        snapshots_list.return_value = {
            'items': [
                {
                    'name': 'test 123'
                },
                {
                    'name': 'test 456'
                }
            ]
        }
        
        deleted = self.provider._delete_volume(self.disk)

        self.assertTrue(disk_delete.called_once)
        self.assertTrue(disk_detach.called_once)
        self.assertTrue(snapshots_list.called_once)
        self.assertTrue(snapshots_delete.called)
        self.assertTrue(deleted)