from volume_provider.providers.base import ProviderBase
from volume_provider.providers.faas import ProviderFaaS


def get_provider_to(provider_name):
    for cls in ProviderBase.__subclasses__():
        if cls.get_provider() == provider_name:
            return cls

    raise NotImplementedError("No provider to '{}'".format(provider_name))
