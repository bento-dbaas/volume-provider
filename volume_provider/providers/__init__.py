from volume_provider.providers.base import ProviderBase
from volume_provider.providers.faas import ProviderFaaS
from volume_provider.providers.aws import ProviderAWS
from volume_provider.providers.k8s import ProviderK8s
from volume_provider.providers.gce import ProviderGce


def get_provider_to(provider_name):
    for cls in ProviderBase.__subclasses__():
        if cls.get_provider() == provider_name:
            return cls

    raise NotImplementedError("No provider to '{}'".format(provider_name))
