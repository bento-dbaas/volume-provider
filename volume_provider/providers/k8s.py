import jinja2
import yaml
from kubernetes import client, config

from volume_provider.credentials.k8s import CredentialK8s, CredentialAddK8s
from volume_provider.providers.base import ProviderBase, CommandsBase
from volume_provider.models import Volume


class ProviderK8s(ProviderBase):

    def get_commands(self):
        return CommandsK8s()

    @classmethod
    def get_provider(cls):
        return 'k8s'

    def render_to_string(self, template_contenxt):
        env = jinja2.Environment(
            loader=jinja2.PackageLoader('volume_provider', 'templates')
        )
        template = env.get_template('k8s/yamls/persistent_volume_claim.yaml')
        return template.render(**template_contenxt)

    def yaml_file(self, context):
        yaml_file = self.render_to_string(
            context
        )
        return yaml.safe_load(yaml_file)

    def build_client(self):
        config.load_kube_config(
            self.credential.kube_config_path
        )

        conf = client.configuration.Configuration()
        conf.verify_ssl = False

        return client.CoreV1Api(client.ApiClient(conf))

    def build_credential(self):
        return CredentialK8s(self.provider, self.environment)

    def get_credential_add(self):
        return CredentialAddK8s

    def _get_snapshot_status(self, snapshot):
        return 'available'

    def create_volume(self, group, size_kb, to_address, snapshot_id=None,
                      **kw):
        volume = Volume()
        volume.size_kb = int(size_kb)
        volume.set_group(group)
        self.client.create_namespaced_persistent_volume_claim(
            kw.get('namespace', 'default'), self.yaml_file({
                'STORAGE_NAME': kw.get('volume_name'),
                'STORAGE_SIZE': volume.size_gb
            })
        )
        volume.identifier = kw.get('volume_name')
        volume.resource_id = ''
        volume.path = ''
        volume.owner_address = ''
        volume.save()

        return volume

    def _delete_volume(self, volume, **kw):
        self.client.delete_namespaced_persistent_volume_claim(
            volume.identifier,
            kw.get('namespace', 'default')
        )

    def _resize(self, volume, new_size_kb):
        self.client.resize(volume, new_size_kb)

    def _take_snapshot(self, volume, snapshot, *args):
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
        export = self.client.export_get(volume)
        volume.resource_id = export['resource_id']
        volume.path = job_result['full_path']


class CommandsK8s(CommandsBase):
    pass
