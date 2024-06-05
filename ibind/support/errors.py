class ExternalBrokerError(Exception):
    """ Something unexpected happened externally """

    def __init__(self, *args, status_code: int = None, **kwargs):
        self.status_code = status_code
        super().__init__(*args)
