from mongoengine import (Document, StringField, IntField, ReferenceField,
                         CASCADE)


class Volume(Document):
    size_kb = IntField(required=True)
    group = StringField(max_length=50, required=True)
    resource_id = StringField(max_length=255, required=True)
    identifier = StringField(required=True)
    path = StringField(max_length=1000, required=True)
    owner_address = StringField(max_length=20, required=True)
    volume_name = StringField(max_length=255, required=False)

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
            'volume_name': self.volume_name,
            'owner_address': self.owner_address,
        }

    @property
    def pairs(self):
        return Volume.objects(group=self.group).all()

    def convert_kb_to_gb(self, size_kb):
        return round((float(size_kb)/1024.0)/1024.0)

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

    @property
    def uuid(self):
        return str(self.pk)

    def to_json(self):
        return {
            'id': self._id,
            'identifier': self.identifier,
            'path': self.description,
            'volume': self.volume
        }
