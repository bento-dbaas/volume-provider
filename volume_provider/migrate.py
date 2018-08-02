import MySQLdb
from re import search
from mongoengine import connect
from volume_provider.models import Volume, Snapshot
from volume_provider.settings import MONGODB_PARAMS, MONGODB_DB


connect(MONGODB_DB, **MONGODB_PARAMS)
my_dbaas = MySQLdb.connect(user='root', db='dbaas')

dbaas_cur = my_dbaas.cursor()
dbaas_cur.execute("""
    select nfs.nfsaas_export_id,
           nfs.nfsaas_size_kb,
           nfs.nfsaas_path,
           h.address,
           h.hostname,
           g.resource_id
    from dbaas_nfsaas_hostattr nfs
      inner join physical_host h
        on h.id = nfs.host_id
      inner join dbaas_nfsaas_group g
        on g.id = nfs.group_id
    order by 1;
""")


for nfsaas in dbaas_cur.fetchall():
    volume = Volume()
    volume.identifier = nfsaas[0]
    volume.size_kb = nfsaas[1]
    volume.path = nfsaas[2]
    volume.owner_address = nfsaas[3]
    volume.group = ''.join(search("(\w+)-\d{2}-(\d+)\..*", nfsaas[4]).groups())
    volume.resource_id = nfsaas[5]
    print(volume.group, volume.identifier)
    volume.save()

    backup_cur = my_dbaas.cursor()
    backup_cur.execute("""
        select s.snapshopt_id,
               s.snapshot_name
        from backup_snapshot s
          inner join physical_volume v
            on s.volume_id = v.id
        where s.purge_at IS NULL
          and v.identifier = {}
        order by 1;
    """.format(volume.identifier))
    for backup in backup_cur.fetchall():
        snapshot = Snapshot()
        snapshot.volume = volume
        snapshot.identifier = backup[0]
        snapshot.description = backup[1]
        snapshot.save()

my_dbaas.close()
