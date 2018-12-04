from volume_provider.clients.faas import FaaSClient
from volume_provider.credentials.faas import CredentialFaaS, CredentialAddFaaS
from volume_provider.providers.base import ProviderBase, CommandsBase
from volume_provider.utils.uuid_helper import is_uuid4


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
        resource_id = None
        if volume.resource_id and is_uuid4(volume.resource_id):
            resource_id = volume.resource_id
        export = self.client.create_export(volume.size_kb, resource_id)
        volume.identifier = str(export['id'])
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

    def _remove_snapshot(self, snapshot, force):
        self.client.delete_snapshot(snapshot.volume, snapshot)
        return True

    def _restore_snapshot(self, snapshot, volume):
        restore_job = self.client.restore_snapshot(snapshot.volume, snapshot)
        job_result = self.client.wait_for_job_finished(restore_job['job'])

        volume.identifier = str(job_result['id'])
        volume.path = job_result['full_path']


class CommandsFaaS(CommandsBase):

    def _mount(self, volume):
        script = self.die_if_error_script()
        script += self.fstab_script(volume.path, self.data_directory)
        script += self.mount_script(self.data_directory)
        return script

    def die_if_error_script(self):
        return """
die_if_error()
{
    local err=$?
    if [ "$err" != "0" ]; then
        echo "$*"
        exit $err
    fi
}
"""

    def fstab_script(self, filer_path, mount_path):
        return """
cp /etc/fstab /etc/fstab.bkp;
sed \'/\{mount_path}/d\' /etc/fstab.bkp > /etc/fstab;
echo "{filer_path} {mount_path} nfs defaults,bg,intr,nolock 0 0" >> /etc/fstab
die_if_error "Error setting fstab"
""".format(mount_path=mount_path, filer_path=filer_path)

    def mount_script(self, mount_path):
        return """
if mount | grep {mount_path} > /dev/null; then
    umount {mount_path}
    die_if_error "Error umount {mount_path}"
fi
mount {mount_path}
die_if_error "Error mounting {mount_path}"
wcl=$(mount -l | grep data | grep nfs | wc -l)
if [ "$wcl" -eq 0 ]
then
    echo "Could not mount /data"
    exit 1
fi
""".format(mount_path=mount_path)

    def _umount(self, volume):
        script = self.die_if_error_script()
        script += 'umount /data'
        return script

    def _clean_up(self, volume):
        mount_path = "/mnt_{}".format(volume.identifier)
        command = "mkdir -p {}".format(mount_path)
        command += "\nmount -t nfs -o bg,intr {} {}".format(
            volume.path, mount_path
        )
        command += "\nrm -rf {}/*".format(mount_path)
        command += "\numount {}".format(mount_path)
        command += "\nrm -rf {}".format(mount_path)
        return command
