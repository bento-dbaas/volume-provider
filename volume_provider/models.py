from mongoengine import Document, StringField, IntField, ReferenceField, CASCADE


class Volume(Document):
    size_kb = IntField(required=True)
    group = StringField(max_length=50, required=True)
    resource_id = StringField(max_length=255, required=True)
    identifier = IntField(required=True)
    path = StringField(max_length=1000, required=True)
    owner_address = StringField(max_length=20, required=True)

    def set_group(self, group):
        self.group = group
        pair = Volume.objects(group=group).first()
        if pair:
            self.resource_id = pair.resource_id

    @property
    def uuid(self):
        return str(self.pk)


class Snapshot(Document):
    volume = ReferenceField(Volume, required=True, reverse_delete_rule=CASCADE)
    identifier = StringField(required=True, max_length=255)
    description = StringField(required=True, max_length=255)

    @property
    def uuid(self):
        return str(self.pk)
