from os import getenv


MONGODB_HOST = getenv("MONGODB_HOST", "127.0.0.1")
MONGODB_PORT = int(getenv("MONGODB_PORT", 27017))
MONGODB_DB = getenv("MONGODB_DB", "volume_provider")
MONGODB_USER = getenv("MONGODB_USER", None)
MONGODB_PWD = getenv("MONGODB_PWD", None)
MONGODB_ENDPOINT = getenv("DBAAS_MONGODB_ENDPOINT", None)


APP_USERNAME = getenv("APP_USERNAME", None)
APP_PASSWORD = getenv("APP_PASSWORD", None)
