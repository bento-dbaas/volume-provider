class VolumeClientError(EnvironmentError):
    pass


class APIError(VolumeClientError):

    def __init__(self, status_code, error):
        super(APIError, self).__init__('{}-{}'.format(status_code, error))
