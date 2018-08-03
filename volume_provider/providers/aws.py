from collections import namedtuple
from time import sleep
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from volume_provider.credentials.aws import CredentialAWS, CredentialAddAWS
from volume_provider.providers.base import ProviderBase, CommandsBase


STATE_AVAILABLE = 'available'
STATE_INUSE = 'inuse'
ATTEMPTS = 60
DELAY = 1
SimpleEbs = namedtuple('ebs', 'id')


class ProviderAWS(ProviderBase):

    def get_commands(self):
        return CommandsAWS(self)

    @classmethod
    def get_provider(cls):
        return 'ebs'

    def build_client(self):
        cls = get_driver(Provider.EC2)
        return cls(
            self.credential.access_id,
            self.credential.secret_key,
            region=self.credential.region
        )

    def build_credential(self):
        return CredentialAWS(self.provider, self.environment)

    def get_credential_add(self):
        return CredentialAddAWS

    def __get_node(self, volume):
        nodes = self.client.list_nodes()
        for node in nodes:
            if volume.owner_address in node.private_ips:
                return node

    def __get_location(self, node):
        subnet_id = node.extra.get('subnet_id')
        subnet = self.client.ex_list_subnets(subnet_ids=[subnet_id])[0]
        zone = subnet.extra.get('zone')
        for location in self.client.list_locations():
            if location.name == zone:
                return location

    def __get_ebs(self, volume):
        ebs = self.client.list_volumes(volume=SimpleEbs(volume.identifier))
        if len(ebs) != 1:
            return None
        ebs = ebs[0]
        if ebs.id != volume.identifier:
            return None
        return ebs

    def __waiting_be(self, state, volume):
        for _ in range(ATTEMPTS):
            ebs = self.__get_ebs(volume)
            if ebs.state == state:
                return True
            sleep(DELAY)
        raise EnvironmentError("Volume {} is {} should be {}".format(
            volume.id, ebs.state, state
        ))

    def __waiting_be_available(self, volume):
        return self.__waiting_be(STATE_AVAILABLE, volume)

    def __waiting_be_in_use(self, volume):
        return self.__waiting_be(STATE_INUSE, volume)

    def mount(self, volume):
        node = self.__get_node(volume)
        ebs = self.__get_ebs(volume)
        if ebs.state == STATE_INUSE:
            if ebs.extra['instance_id'] == node.id:
                return
            raise EnvironmentError(
                'Volume {} being used in {}'.format(ebs.id, node.id)
            )
        self.__waiting_be_available(volume)
        self.client.attach_volume(node, ebs, self.credential.device)
        self.__waiting_be_in_use(volume)

    def _create_volume(self, volume):
        node = self.__get_node(volume)
        ebs = self.client.create_volume(
            size=volume.size_gb, name=node.name,
            ex_volume_type=self.credential.ebs_type,
            ex_iops=self.credential.iops,
            location=self.__get_location(node)
        )
        volume.identifier = ebs.id
        volume.resource_id = ebs.name
        volume.path = self.credential.device

    def _add_access(self, volume, to_address):
        return

    def _delete_volume(self, volume):
        node = self.__get_node(volume)
        ebs = self.__get_ebs(volume)
        if ebs.state == STATE_INUSE:
            if ebs.extra['instance_id'] != node.id:
                raise EnvironmentError(
                    "Volume {} not attached in instance {}".format(
                        ebs.id, node.id
                    )
                )
            self.client.detach_volume(ebs, self.credential.force_detach)
            self.__waiting_be_available(volume)
        self.client.destroy_volume(ebs)

    def _remove_access(self, volume, to_address):
        pass
        # TODO
        # self.client.delete_access(volume, to_address)

    def _resize(self, volume, new_size_kb):
        pass
        #TODO
        #for vol in self.get_volumes_from_node(inst_id):
        #    if vol.extra.get('volume_type') != 'standard':
        #        self.driver.ex_modify_volume(vol, {'Size': size})

    def _take_snapshot(self, volume, snapshot):
        pass
        #for vol in self.get_volumes_from_node(inst_id):
        #    print("Creating snapshot of volume {}".format(vol.id))
        #    self.driver.create_volume_snapshot(vol, name)
        #    snapshot.identifier = str(new_snapshot['snapshot']['id'])
        #    snapshot.description = new_snapshot['snapshot']['name']

    def _remove_snapshot(self, snapshot):
        pass
        #for vol in self.get_volumes_from_node(inst_id):
        #    for snapshot in vol.list_snapshots():
        #        if snapshot.name == name:
        #            print("Destroying snap {}".format(snapshot.id))
        #            snapshot.destroy()

    def _restore_snapshot(self, snapshot, volume):
        pass
        # TODO
        #restore_job = self.client.restore_snapshot(snapshot.volume, snapshot)
        #job_result = self.client.wait_for_job_finished(restore_job['job'])

        #volume.identifier = job_result['id']
        #volume.path = job_result['full_path']


class CommandsAWS(CommandsBase):

    def __init__(self, provider):
        self.provider = provider

    def _mount(self, volume):
        self.provider.mount(volume)
        device = "/dev/xv{}".format(
            self.provider.credential.device.split('/')[-1][-2:]
        )
        command = 'yum -y install xfsprogs'
        command += ' && mkfs -t xfs {}'.format(device)
        command += ' && mkdir -p /data'
        command += ' && mount {} /data'.format(device)
        return command

    def _clean_up(self, volume):
        return None


