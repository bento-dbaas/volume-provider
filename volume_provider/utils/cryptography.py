from cryptography.fernet import Fernet
from volume_provider.settings import CRYPTOGRAPHY_KEY

ENCODING = "utf-8"


def encrypt(value):
    fernet = Fernet(CRYPTOGRAPHY_KEY)
    return fernet.encrypt(bytes(value, ENCODING)).decode(ENCODING)


def decrypt(value):
    fernet = Fernet(CRYPTOGRAPHY_KEY)
    return fernet.decrypt(bytes(value, ENCODING)).decode(ENCODING)
