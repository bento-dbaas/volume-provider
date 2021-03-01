from unittest import TestCase
from volume_provider.models import Volume

from mongoengine import errors

from mongoengine import connect
from volume_provider.settings import *

connect(MONGODB_DB, **MONGODB_PARAMS)

class PropertiesTestCase(TestCase):

    def setUp(self):
        self.volume = Volume()
        self.volume._data = {
            'id': '123456789abcdef000000000',
            'group': 'fake_name',
            'size_kb': 123,
            'resource_id': 'a1234a',
            'identifier': 'aaa123',
            'path': '/path/to/volume',
            'owner_address': '/addr'
        }

    def test_return_normal_fields(self):
        self.assertIn('id', self.volume)
        self.assertIn('group', self.volume)

    def test_save_with_invalid_fields(self):
        self.volume._data = {
            'invalid': 12
        }

        self.assertRaises(errors.ValidationError, self.volume.save)
    
    def test_save_valid_fields(self):
        self.assertEqual(str(type(self.volume.save().id)), "<class 'bson.objectid.ObjectId'>")