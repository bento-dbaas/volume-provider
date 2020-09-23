from uuid import UUID, uuid4


def is_uuid(value, version):
    try:
        UUID(value, version=version)
    except ValueError:
        return False
    return True


def is_uuid4(value):
    return is_uuid(value, 4)


def generate_random_uuid():
    return str(uuid4())
