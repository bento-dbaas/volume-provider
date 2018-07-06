from volume_provider.credentials.faas import CredentialFaaS, CredentialAddFaaS
from volume_provider.providers.base import ProviderBase, CommandsBase
from volume_provider.clients.faas import FaaSClient


class ProviderFaaS(ProviderBase):

    def get_commands(self):
        return CommandsFaaS()

    @classmethod
    def get_provider(cls):
        return 'faas'

    def build_client(self):
        return FaaSClient(self.credential)

    def build_credential(self):
        return CredentialFaaS(self.provider, self.environment)

    def get_credential_add(self):
        return CredentialAddFaaS

    def _create_volume(self, volume):
        export = self.client.create_export(volume.size_kb, volume.resource_id)
        volume.identifier = export['id']
        volume.resource_id = export['resource_id']
        volume.path = export['full_path']

    def _add_access(self, volume, to_address):
        self.client.create_access(volume, to_address)

    def _delete_volume(self, volume):
        self.client.delete_export(volume)

    def _remove_access(self, volume, to_address):
        self.client.delete_access(volume, to_address)

    def _resize(self, volume, new_size_kb):
        self.client.resize(volume, new_size_kb)

    def _take_snapshot(self, volume, snapshot):
        new_snapshot = self.client.create_snapshot(volume)
        snapshot.identifier = str(new_snapshot['snapshot']['id'])
        snapshot.description = new_snapshot['snapshot']['name']

    def _remove_snapshot(self, snapshot):
        self.client.delete_snapshot(snapshot.volume, snapshot)

    def _restore_snapshot(self, snapshot, volume):
        restore_job = self.client.restore_snapshot(snapshot.volume, snapshot)
        job_result = self.client.wait_for_job_finished(restore_job['job'])

        volume.identifier = job_result['id']
        volume.path = job_result['full_path']


class CommandsFaaS(CommandsBase):

    def _mount(self, volume):
        return '''
sed '{data}/d' "/etc/fstab"
echo "{volume_path}	{data} nfs defaults,bg,intr,nolock 0 0" >> /etc/fstab
die_if_error "Error setting fstab"

if mount | grep {data} > /dev/null; then
    umount {data}
    die_if_error "Error umount {data}"
fi
mount {data}
die_if_error "Error mounting {data}"
            '''.format(data=self.data_directory, volume_path=volume.path)
