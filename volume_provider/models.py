from mongoengine import (
    Document, StringField, IntField, ReferenceField, CASCADE, DictField,
    DateTimeField
)


class Volume(Document):
    size_kb = IntField(required=True)
    group = StringField(max_length=50, required=True)
    resource_id = StringField(max_length=255, required=True)
    identifier = StringField(required=True)
    path = StringField(max_length=1000, required=True)
    owner_address = StringField(max_length=20, required=True)
    zone = StringField(max_length=200, required=False)
    vm_name = StringField(max_length=200, required=False)
    labels = DictField(required=False)
    disk_offering_type = StringField(max_length=255, required=False, default=None)

    def set_group(self, group):
        self.group = group
        pair = Volume.objects(group=group).first()
        if pair:
            self.resource_id = pair.resource_id

    @property
    def uuid(self):
        return str(self.pk)

    @property
    def get_json(self):
        return {
            'size_kb': self.size_kb,
            'group': self.group,
            'resource_id': self.resource_id,
            'identifier': self.identifier,
            'path': self.path,
            'owner_address': self.owner_address,
        }

    @property
    def pairs(self):
        return Volume.objects(group=self.group).all()

    def convert_kb_to_gb(self, size_kb, to_int=False):
        gb_size = round((float(size_kb)/1024.0)/1024.0)
        return int(gb_size) if to_int else gb_size

    @property
    def size_gb(self):
        return self.convert_kb_to_gb(self.size_kb)

    @property
    def snapshots(self):
        return Snapshot.objects.filter(volume=self)


class Snapshot(Document):
    volume = ReferenceField(Volume, required=True, reverse_delete_rule=CASCADE)
    identifier = StringField(required=True, max_length=255)
    description = StringField(required=True, max_length=255)
    labels = DictField(required=False)
    size_bytes = IntField(required=False)
    created_at = DateTimeField(required=False)

    @property
    def uuid(self):
        return str(self.pk)

    def to_json(self):
        return {
            'id': self._id,
            'identifier': self.identifier,
            'path': self.description,
            'volume': self.volume,
            'size_bytes': self.size_bytes,
        }
