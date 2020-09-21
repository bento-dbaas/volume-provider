from cryptography.fernet import Fernet
from volume_provider.settings import CRYPTOGRAPHY_KEY


def encrypt(value):
    fernet = Fernet(CRYPTOGRAPHY_KEY)
    return fernet.encrypt(bytes(value, "utf-8"))


def decrypt(value):
    fernet = Fernet(CRYPTOGRAPHY_KEY)
    return fernet.decrypt(value).decode()
