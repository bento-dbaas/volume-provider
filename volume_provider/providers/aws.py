from collections import namedtuple
from time import sleep
from traceback import print_exc
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from volume_provider.settings import AWS_PROXY, TAG_BACKUP_DBAAS
from volume_provider.credentials.aws import CredentialAWS, CredentialAddAWS
from volume_provider.providers.base import ProviderBase, CommandsBase
from volume_provider.clients.team import TeamClient


STATE_AVAILABLE = 'available'
STATE_INUSE = 'inuse'
ATTEMPTS = 60
DELAY = 5
SimpleEbs = namedtuple('ebs', 'id')


class ProviderAWS(ProviderBase):

    def get_commands(self):
        return CommandsAWS(self)

    @classmethod
    def get_provider(cls):
        return 'ebs'

    def build_client(self):
        cls = get_driver(Provider.EC2)
        client = cls(
            self.credential.access_id,
            self.credential.secret_key,
            region=self.credential.region,
            **{'proxy_url': AWS_PROXY} if AWS_PROXY else {}
        )

        if AWS_PROXY:
            client.connection.connection.session.proxies.update({
                'https': AWS_PROXY.replace('http://', 'https://')
            })
        return client

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
        for ebs in self.client.list_volumes():
            if ebs.id == volume.identifier:
                return ebs
        return None

    def __waiting_be(self, state, volume):
        ebs = self.__get_ebs(volume)
        for _ in range(ATTEMPTS):
            if ebs.state == state:
                return True
            sleep(DELAY)
            ebs = self.__get_ebs(volume)
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
        self.client.attach_volume(node, ebs, volume.path)
        self.__waiting_be_in_use(volume)

    def umount(self, volume):
        self.__detach_volume(volume)

    def __detach_volume(self, volume):
        ebs = self.__get_ebs(volume)
        if ebs.state != STATE_INUSE:
            return

        node = self.__get_node(volume)
        if ebs.extra['instance_id'] != node.id:
            raise EnvironmentError(
                "Volume {} not attached in instance {}".format(ebs.id, node.id)
            )
        self.client.detach_volume(ebs, self.credential.force_detach)
        self.__waiting_be_available(volume)

    def _create_volume(self, volume, snapshot=None):
        node = self.__get_node(volume)
        if snapshot:
            snapshot = self.__get_snapshot(snapshot)
        ebs = self.client.create_volume(
            size=volume.size_gb, name=volume.group,
            ex_volume_type=self.credential.ebs_type,
            ex_iops=self.credential.iops,
            location=self.__get_location(node),
            snapshot=snapshot
        )
        volume.identifier = ebs.id
        volume.resource_id = ebs.name
        volume.path = self.credential.next_device(volume.owner_address)

    def _add_access(self, volume, to_address):
        volume.owner_address = to_address
        volume.save()
        return

    def _delete_volume(self, volume):
        for snapshot in volume.snapshots:
            self._remove_snapshot(snapshot, True)
        ebs = self.__get_ebs(volume)
        self.__detach_volume(volume)
        self.client.destroy_volume(ebs)

    def _remove_access(self, volume, to_address):
        return

    def _resize(self, volume, new_size_kb):
        ebs = self.__get_ebs(volume)
        new_size_gb = volume.convert_kb_to_gb(new_size_kb)
        self.client.ex_modify_volume(ebs, {'Size': new_size_gb})

    def __verify_none(self, dict_var, key, var):
        if var:
            dict_var[key] = var

    def _take_snapshot(self, volume, snapshot, team, engine, db_name):
        ebs = self.__get_ebs(volume)
        ex_metadata = {}
        if team and engine:
            ex_metadata = TeamClient.make_tags(team, engine)
        self.__verify_none(ex_metadata, 'engine', engine)
        self.__verify_none(ex_metadata, 'db_name', db_name)
        self.__verify_none(ex_metadata, 'team', team)
        self.__verify_none(ex_metadata, TAG_BACKUP_DBAAS, 1)

        new_snapshot = self.client.create_volume_snapshot(ebs,
                                                          ex_metadata=ex_metadata)
        snapshot.identifier = new_snapshot.id
        snapshot.description = new_snapshot.name

    def __get_snapshot(self, snapshot):
        ebs = self.__get_ebs(snapshot.volume)
        for ebs_snapshot in ebs.list_snapshots():
            if ebs_snapshot.id == snapshot.identifier:
                return ebs_snapshot
        raise EnvironmentError("Snapshot {} not found to volume {}".format(
            snapshot.identifier, snapshot.volume.identifier
        ))

    def _remove_snapshot(self, snapshot, force):
        if force:
            ebs_snapshot = self.__get_snapshot(snapshot)
            ebs_snapshot.destroy()
            return True
        try:
            ebs_snapshot = self.__get_snapshot(snapshot)
        except OSError as e:
            return True
        return False

    def _restore_snapshot(self, snapshot, volume):
        ebs_snapshot = self.__get_snapshot(snapshot)
        self._create_volume(volume, ebs_snapshot)

class CommandsAWS(CommandsBase):

    def __init__(self, provider):
        self.provider = provider

    def _scp(self, snap, source_dir, target_ip, target_dir):
        script = self.die_if_error_script()
        script += self.scp_script(
            source_dir=source_dir,
            target_ip=target_ip,
            target_dir=target_dir
        )
        return script

    def scp_script(self, **kw):
        return """
scp -i "/root/.ssh/dbaas.key" -Crp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {source_dir}/* root@{target_ip}:{target_dir}
die_if_error "Error scp from {source_dir} to {target_ip}:{target_dir}"
""".format(**kw)

    def _mount(self, volume, *args, **kw):
        fstab = kw.get('fstab')
        mount_devide = ''
        self.provider.mount(volume)
        device = "/dev/xv{}".format(volume.path.split('/')[-1][-2:])
        command = 'yum clean all && yum -y install xfsprogs'
        command += """ &&
formatted=$(blkid -o value -s TYPE {0} | grep xfs | wc -l)
if [ "$formatted" -eq 0 ]
then
    mkfs -t xfs {0}
fi """.format(device)
        if fstab:
            command += ' && ' + self.fstab_script(device, self.data_directory)
        else:
            mount_devide = '-o nouuid {}'.format(device)
        command += ' && mkdir -p {}'.format(self.data_directory)

        command += ' && mount {} {}'.format(
            mount_devide, self.data_directory
        )
        return command

    def fstab_script(self, filer_path, mount_path):
        command = "cp /etc/fstab /etc/fstab.bkp"
        command += " && sed \'/\{mount_path}/d\' /etc/fstab.bkp > /etc/fstab"
        command += ' && echo "{filer_path}  {mount_path}    xfs defaults    0   0" >> /etc/fstab'
        return command.format(mount_path=mount_path, filer_path=filer_path)

    def _umount(self, volume, *args, **kw):
        self.provider.umount(volume)
        return "umount {}".format(kw.get('data_directory', '/data'))

    def _clean_up(self, volume):
        return None
