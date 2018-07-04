from time import sleep
from faasclient.client import Client
from volume_provider.clients.errors import APIError


class FaaSClient(object):

    def __init__(self, credential):
        self.credential = credential
        self._client = None

    @property
    def client(self):
        if not self._client:
            self._client = Client(
                authurl=self.credential.endpoint,
                user=self.credential.user, key=self.credential.password,
                tenant_name=self.credential.project,
                insecure=not self.credential.is_secure
            )
        return self._client

    def execute(self, call, expected_code, *args):
        status, content = call(args)
        if status != expected_code:
            raise APIError(status, content)
        return content


    def create_export(self, size_kb, resource_id):
        status, content = self.client.export_create(
            size_kb, self.credential.category_id, resource_id
        )
        if status != 201:
            raise APIError(status, content)
        return content

    def delete_export(self, export):
        self.create_access(export, export.owner_address)
        #self.delete_all_disk_files(export) TODO Host Provider execute command
        return self.execute(self.client.export_delete, 200, export.identifier)

    def list_access(self, export):
        return self.execute(self.client.access_list, 200, export.identifier)

    def check_access_exist(self, export, address):
        for access in self.list_access(export):
            if access['host'] == address:
                return access

    def create_access(self, export, address):
        access = self.check_access_exist(export, address)
        if access:
            return access
        return self.execute(
            self.client.access_create, 201,
            export.identifier, self.credential.access_permission, address
        )

    def delete_access(self, export, address):
        access = self.check_access_exist(export, address)
        if not access:
            return True

        return self.execute(
            self.client.access_delete, 200, export.id, access['id']
        )

    def create_snapshot(self, export):
        return self.execute(
            self.client.snapshot_create, 201, export.id
        )

    def delete_snapshot(self, export, snapshot):
        return self.execute(
            self.client.snapshot_delete, 200, export.id, snapshot.id
        )

    def restore_snapshot(self, export, snapshot):
        return self.execute(
            self.client.snapshot_restore, 200, export.id, snapshot.id
        )

    def wait_for_job_finished(self, job, attempts=50, interval=30):
        for i in range(attempts):
            job = self.execute(self.client.jobs_get, 200, job)
            if job['status'] == 'finished':
                return job['result']
            sleep(interval)

    def get_export_size(self, export):
        return self.execute(self.client.quota_get, 200, export.id)

    def resize(self, export, new_size_kb):
        return self.execute(
            self.client.quota_post, 200, export.id, new_size_kb
        )
