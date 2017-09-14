class Data(object):
    def __init__(self):
        # Rest stuff
        self.default_headers = {'User-Agent': 'pyechobe-agent/{0} ({1}, {2} {3})'.format(version,
                                                                              platform.platform(),
                                                                              platform.python_implementation(),
                                                                              platform.python_version()),
                                'Content-Type': 'application/json;charset=UTF-8'}

        self.default_params = {}

        # Auth
        self.api_key = ''
        self.authorization_code = ''
        self.refresh_token = ''
        self.pin = ''
