from collections import namedtuple

HOST_ORIGIN_TAG = {}

FAKE_TAGS = {
    'cliente-id': 'fake_client-id',
    'componente-id': 'fake_component_id',
    'consumo-detalhado': True,
    'equipe-id': 'fake_team_id',
    'servico-de-negocio-id': 'fake_business_service_id',
    'sub-componente-id': 'fake_sub_component_id'
}

FAKE_CREDENTIAL = {
    "provider":"gce",
    "service_account":{
        "type":"service_account",
        "project_id":"fake-proj-id",
        "private_key_id":"fake_pvt_key_id",
        "private_key":"fake_pvt_key",
        "client_email":"fake_mail@fakemail.com",
        "client_id":"fake_client_id",
        "auth_uri":"https://fake_url_auth.com/auth",
        "token_uri":"https://fakeurlauth.com/token",
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
        }
    }