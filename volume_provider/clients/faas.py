import os
from logging import error
from time import sleep
from faasclient.client import Client
from volume_provider.clients.errors import APIError
from volume_provider.settings import TEAM_API_URL
from dbaas_base_provider.team import TeamClient


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

    def execute(self, call, expected_code, *args, **kw):
        status, content = call(*args, **kw)
        error("[FaaS] Response from {} with {}: {} - {}".format(
            call, args, status, content
        ))
        if status != expected_code:
            raise APIError(status, content)
        return content

    def get_team_id(self, team_name):
        team_id = os.getenv('DBAAS_TEAM_ID')
        if team_id:
            return team_id
        team = TeamClient(api_url=TEAM_API_URL, team_name=team_name)
        return team.team_id

    def create_export(self, size_kb, resource_id, team_name=None):
        if not team_name:
            raise Exception("The team name must be passed")

        return self.execute(
            self.client.export_create,
            201,
            size_kb,
            self.credential.category_id,
            self.get_team_id(team_name),
            resource_id
        )

    def delete_export(self, export):
        return self.execute(
            self.client.export_force_delete,
            200,
            export.identifier
        )

    def export_get(self, export):
        return self.execute(
            self.client.export_get, 200, export.identifier)

    def list_access(self, export):
        return self.execute(self.client.access_list, 200, export.identifier)

    def check_access_exist(self, export, address):
        for access in self.list_access(export):
            if access['host'] == address:
                return access

    def create_access(self, export, address, access_type=None):
        error("Check access for {}:{}".format(export.identifier, address))
        access = self.check_access_exist(export, address)
        error("access {}".format(access))
        if access:
            return access
        return self.execute(
            self.client.access_create, 201,
            export.identifier,
            access_type or self.credential.access_type,
            address
        )

    def delete_access(self, export, address):
        access = self.check_access_exist(export, address)
        if not access:
            return True

        return self.execute(
            self.client.access_delete, 200, export.identifier, access['id']
        )

    def resize(self, export, new_size_kb):
        return self.execute(
            self.client.quota_post, 200, export.identifier, new_size_kb
        )

    def create_snapshot(self, export):
        return self.execute(
            self.client.snapshot_create, 201, export.identifier
        )

    def delete_snapshot(self, export, snapshot):
        return self.execute(
            self.client.snapshot_delete, 200,
            export.identifier, snapshot.identifier
        )

    def restore_snapshot(self, export, snapshot):
        return self.execute(
            self.client.snapshot_restore, 200,
            export.identifier, snapshot.identifier
        )

    def wait_for_job_finished(self, job_id, attempts=50, interval=30):
        job_result = None
        for i in range(attempts):
            sleep(interval)
            job = self.execute(self.client.jobs_get, 200, job_id)
            if job['status'] == 'finished':
                job_result = job['result']
                break

        if not job_result or 'id' not in job_result:
            raise APIError(500, 'Error while restoring snapshot - {}'.format(
                job_result
            ))

        return job_result
