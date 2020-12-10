import jinja2
import yaml
from kubernetes.client import Configuration, ApiClient, CoreV1Api

from volume_provider.utils.uuid_helper import generate_random_uuid
from volume_provider.credentials.k8s import CredentialK8s, CredentialAddK8s
from volume_provider.providers.base import ProviderBase, CommandsBase


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
        configuration = Configuration()
        configuration.api_key['authorization'] = "Bearer {}".format(self.auth_info['K8S-Token'])
        configuration.host = self.auth_info['K8S-Endpoint']
        configuration.verify_ssl = self._verify_ssl
        api_client = ApiClient(configuration)
        return CoreV1Api(api_client)

    @property
    def _verify_ssl(self):
        verify_ssl = self.auth_info.get("K8S-Verify-Ssl", 'false')
        return verify_ssl != 'false' and verify_ssl != 0

    def build_credential(self):
        return CredentialK8s(self.provider, self.environment)

    def get_credential_add(self):
        return CredentialAddK8s

    def _get_snapshot_status(self, snapshot):
        return 'available'

    def _create_volume(self, volume, snapshot=None):
        volume.owner_address = ''
        volume.identifier = generate_random_uuid()
        volume.resource_id = volume.identifier
        volume.path = "/"
        self.client.create_namespaced_persistent_volume_claim(
            self.auth_info.get("K8S-Namespace", "default"),
            self.yaml_file({
                'STORAGE_NAME': volume.identifier,
                'STORAGE_SIZE': volume.size_gb,
                'STORAGE_TYPE': self.auth_info.get('K8S-Storage-Type', '')
            })
        )
        return volume

    def _delete_volume(self, volume, **kw):
        self.client.delete_namespaced_persistent_volume_claim(
            volume.identifier,
            self.auth_info.get("K8S-Namespace", "default"),
        )

    def _resize(self, volume, new_size_kb):
        new_size_gb = volume.convert_kb_to_gb(new_size_kb)
        self.client.patch_namespaced_persistent_volume_claim(
            name=volume.identifier,
            namespace=self.auth_info.get("K8S-Namespace", "default"),
            body=self.yaml_file({
                'STORAGE_NAME': volume.identifier,
                'STORAGE_SIZE': new_size_gb,
                'STORAGE_TYPE': self.auth_info.get('K8S-Storage-Type', '')
            })
        )

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

    def _add_access(self, volume, to_address):
        pass


class CommandsK8s(CommandsBase):
    pass
