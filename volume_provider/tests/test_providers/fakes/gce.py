from recordclass import recordclass


FAKE_TAGS = {
    'db_name': 'fake_db_name'
}

FAKE_CREDENTIAL = {
    "provider":"gce",
    "region": "fake_region",
    "service_account":{
        "type":"service_account",
        "project_id":"fake-proj-id",
        "private_key_id":"fake_pvt_key_id",
        "private_key":'-----BEGIN RSA PRIVATE KEY-----\nMIICXAIBAAKBgQDgsEaDGCiCm/dFT1pHzvok1PTpSa9lsuUBVzUt4WeXXwdH7jC1\n46rAULeNCZwJQYgjPzpikwDd3lKnr395euK90EEqQLdMh1EJK0/+ja0OfKxxFLZv\noqOyKsjxWAipEYKjMvWH/vYQZNPG3gMaf4X5RxuvSggXAVDq4MRkw+ZtGQIDAQAB\nAoGAbgdEcFv7MoJn40QJpNKBglnamQchYj7pj++BtjcEQIcjjKDir5+OdWDRkbpb\n89hob0I+OBleukdt2HnDhdycfYXftqShM4Q03fWxCEK3OacRw4CplYLaxlGWxMuZ\nGVFsE0gAS4QXu87ZutXeXIXkd2Bv5F53gBPOMQCtI+qXfVUCQQD99hTa4QDlmZpO\ngV4Ah1IHBVddjv/E+68rlw952j0CwM4fFLTWQC3iRQqfWngLw9t7ZNyKHzQJ/o38\n8yZDF6STAkEA4n4JDg+6M/4K4nZ3vnTKnbeLSTV5i9PsNlBf5hAy2ABLDd35FfBl\nQuX009j6nCUdUWM0LPY6OuQmEPkVaKJ/IwJAL0GyQcRqqU660u7psgl8LwhEaIlq\neJooz2CtpYwBnFiKQmhU+iU5JIiaYGqyOeY5Gi37h8wkn9N5Ul9geE2W9wJAIPBJ\natUYtFT+yj6GXZlomhVGWWhAe/hfAusfdzrl2gn44FRm1Cz43QjKWUDV+X1gTSTL\nQrqwbz4c1x0SYvw21wJBAI7onsip6jWZDTevWu0hHozm5pB20EPcYVobwClwv0Q1\n+WLKuBnXEVlUMaJC/e7VSyY9bwbZQEUpF0jvVmTd3nw=\n-----END RSA PRIVATE KEY-----',
        "client_email":"2423423-compute@developer.gserviceaccount.com",
        "client_id":"fake_client_id",
        "auth_uri":"https://accounts.google.com/o/oauth2/auth",
        "token_uri":"https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url":"https://fake_cert_url.com"
    },
    "environment":"gcp-fake-dev",
    "offerings":{
        "fake_micro":{
            "id":"e2-micro",
            "name":"micro instance"
        },
        "fake_medium":{
            "id":"e2-small",
            "name":"small instance"
        },
        "fake_medium":{
            "id":"e2-medium",
            "name":"medium instance"
        }
    },
    "project":"fake-project",
    "availability_zones":{
        "southamerica-east1-a":{
            "active": True,
            "id":"southamerica-east1-a",
            "name":"southamerica-east1-a"
        }
    },
    "subnetwork":"projects/fake-subnet/regions/southamerica-east1/subnetworks/fake-snet",
    "templates":{
        "mongodb_3_4_1":"img-fke1",
        "mongodb_4_0_3":"img-fke2",
        "mongodb_4_2_3":"img-fke3"
        },
    "scopes": ["fake_scope"]
    }

FAKE_DISK_OBJ = recordclass(
    'FakeDiskObj', 'id name zone identifier vm_name group convert_kb_to_gb\
    size_kb resource_id path labels' )
FAKE_SNAP_OBJ = recordclass('FakeSnapshotObj', 'id volume identifier description labels size_bytes')


FAKE_DISK = FAKE_DISK_OBJ(
    '507f191e810c19729de860ea', 'fake_disk_name',
    'fake_zone', 'fake_identifier',
    'fake_vm_name', 'fake_group',
    lambda x,to_int: x/1000/1000, 1024,
    '0000123', '', FAKE_TAGS
)

FAKE_SNAP = FAKE_SNAP_OBJ(
    '507f191e810c19729de8602', FAKE_DISK,
    'fake_identifier', 'fake_description', 'labels', 0,
)

FAKE_DISK_LIST = ['fake_group-data1', 'fake_group-data2']