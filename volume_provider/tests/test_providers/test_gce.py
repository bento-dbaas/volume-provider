from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, MagicMock, PropertyMock
from volume_provider.providers.gce import ProviderGce
from volume_provider.credentials.gce import CredentialAddGce
from volume_provider.models import Volume
from .fakes.gce import FAKE_CREDENTIAL, FAKE_DISK_LIST
from .base import GCPBaseTestCase

import googleapiclient


ENVIRONMENT = "dev"
ENGINE = "redis"


class TestCredentialGCE(GCPBaseTestCase):
    
    @patch('volume_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_CREDENTIAL))
    def setUp(self, ):
        self.provider = ProviderGce(ENVIRONMENT, ENGINE)
        self.provider.wait_operation_state = MagicMock()

    def test_provider_name(self):
        self.assertEqual(self.provider.get_provider(), 'gce')

    def test_get_credential_add(self):
        self.assertEqual(
            self.provider.get_credential_add(), CredentialAddGce
        )

    def test_validate_credential(self):
        invalid_content = deepcopy(FAKE_CREDENTIAL)
        del(invalid_content['region'])
        success, error = self.provider.credential_add(invalid_content)

        self.assertFalse(success)
        self.assertIn("Required fields", error)

    @patch(
        'volume_provider.providers.gce.CredentialGce.get_content'
    )
    def test_build_client(self, content):
        self.build_credential_content(content)

        self.assertEqual(
            type(self.provider.build_client()),
            googleapiclient.discovery.Resource
        )

    def build_credential_content(self, content, **kwargs):
        values = deepcopy(FAKE_CREDENTIAL)
        values.update(kwargs)
        content.return_value = values


@patch('volume_provider.providers.gce.ProviderGce.build_client')
@patch('volume_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_CREDENTIAL))
@patch('volume_provider.providers.gce.ProviderGce.get_disk',
       new=MagicMock(return_value={'status': 'READY'}))
@patch('base_provider.BaseProvider.wait_operation',
       new=MagicMock(return_value={'status': 'READY'}))
class CreateVolumeTestCase(GCPBaseTestCase):

    @patch('volume_provider.providers.gce.ProviderGce._get_volumes',
           new=MagicMock(return_value=FAKE_DISK_LIST))
    def test_get_disk_name(self, client_mock):
        disk_name = self.provider._get_new_disk_name(self.disk)
        self.assertEqual(disk_name, 'fake_group-data3')

    @patch('volume_provider.providers.gce.ProviderGce._get_volumes',
           new=MagicMock(return_value=[]))
    def test_get_disk_name_first_disk(self, client_mock):
        disk_name = self.provider._get_new_disk_name(self.disk)
        self.assertEqual(disk_name, 'fake_group-data1')

    @patch('volume_provider.providers.gce.ProviderGce._get_new_disk_name',
           new=MagicMock(return_value='fake_group-disk2'))
    def test_create_disk(self, client_mock):
        disk_insert = client_mock().disks().insert().execute
        disk_insert.return_value = {'id': 'disk_id123'}

        created = self.provider._create_volume(self.disk)
        self.assertTrue(disk_insert.called_once)
        self.assertTrue(created)
        self.assertEqual(self.disk.path, '/dev/disk/by-id/google-disk2')
        self.assertEqual(self.disk.resource_id, 'fake_group-disk2')
        self.assertEqual(self.disk.identifier, disk_insert.return_value['id'])


@patch('volume_provider.providers.gce.ProviderGce.build_client')
@patch('volume_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_CREDENTIAL))
@patch('base_provider.BaseProvider.wait_operation',
       new=MagicMock(return_value={'status': 'READY'}))
class ResizeVolumeTestCase(GCPBaseTestCase):
    def test_resize_disk_wrong_size(self, client_mock):
        with self.assertRaises(EnvironmentError):
            self.provider._resize(self.disk, 1000)

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
@patch('volume_provider.providers.gce.ProviderGce._detach_disk',
       new=MagicMock(return_value=True))
@patch('base_provider.BaseProvider.wait_operation',
       new=MagicMock(return_value={'status': 'READY'}))
class DeleteVolumeTestCase(GCPBaseTestCase):
    def test_delete_disk(self, client_mock):
        disk_delete = client_mock().disks().delete().execute
        disk_detach = client_mock().instances().detachDisk().execute
        snapshots_list = client_mock().snapshots().list().execute

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
        self.assertTrue(deleted)


@patch('volume_provider.providers.gce.ProviderGce.build_client')
@patch('volume_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_CREDENTIAL))
@patch('volume_provider.providers.gce.ProviderGce.get_snapshots_from',
       new=MagicMock(return_value=[]))
@patch('volume_provider.providers.gce.ProviderGce._get_snapshot_status',
       new=MagicMock(return_value='READY'))
@patch('volume_provider.providers.gce.ProviderGce._get_new_disk_name',
       new=MagicMock(return_value='fake_group-disk2'))
@patch('volume_provider.providers.gce.ProviderGce.get_disk',
       new=MagicMock(return_value={'status': 'READY'}))
@patch('base_provider.BaseProvider.wait_operation',
       new=MagicMock(return_value={'status': 'READY'}))
@patch('base_provider.BaseProvider.wait_operation',
       new=MagicMock(return_value={'status': 'READY'}))
class SnapshotTestCase(GCPBaseTestCase):

    def test_create_snapshot(self, client_mock):
        take_snap = client_mock().disks().createSnapshot().execute
        get_snaps = client_mock().snapshots().get().execute

        take_snap.return_value = {'id': 'idtest'}
        get_snaps.return_value = {'id': 'newid'}

        self.provider._take_snapshot(self.disk, self.snapshot,
                                     'fake_team',
                                     'fake_engine',
                                     'fake_db_name')

        self.assertTrue(take_snap.called)
        self.assertEqual(self.snapshot.labels['db_name'], 'fake_db_name')
        self.assertEqual(self.snapshot.identifier, "newid")
        # self.assertTrue(snap)

    def test_create_disk_with_snapshot(self, client_mock):
        disk_insert = client_mock().disks().insert().execute
        disk_insert.return_value = {'id': 'disk_id123'}

        created = self.provider._create_volume(self.disk, self.snapshot)

        self.assertTrue(created)

    def test_delete_snapshot(self, client_mock):
        delete_snap = client_mock().snapshots().delete().execute

        deleted = self.provider._remove_snapshot(self.snapshot)

        self.assertTrue(delete_snap.called)
        self.assertTrue(deleted)


@patch('volume_provider.providers.gce.ProviderGce.build_client')
@patch('volume_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_CREDENTIAL))
@patch('base_provider.BaseProvider.wait_operation',
       new=MagicMock(return_value={'status': 'READY'}))
class MoveDiskTestCase(GCPBaseTestCase):

    def test_move_disk(self, client_mock):
        disk_move = client_mock().projects().moveDisk().execute
        moved = self.provider._move_volume(self.disk, 'zone1')

        self.assertTrue(moved)
        self.assertTrue(disk_move.called)

    def test_move_disk_to_same_zone(self, client_mock):
        disk_move = client_mock().projects().moveDisk().execute
        moved = self.provider._move_volume(self.disk, 'fake_zone')

        self.assertTrue(moved)
        self.assertFalse(disk_move.called)
