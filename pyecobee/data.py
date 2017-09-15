import platform, pkg_resources

class Data(object):
    def __init__(self):
        # Rest stuff

        #version = pkg_resources.require("pyecobee")[0].version
        self.data['version'] = "0.2.0"

        self.data['default_headers'] = {'User-Agent': 'pyechobe-agent/{0} ({1}, {2} {3})'.format(self.data['version'],
                                                                              platform.platform(),
                                                                              platform.python_implementation(),
                                                                              platform.python_version()),
                                        'Content-Type': 'application/json;charset=UTF-8'}

        self.data['default_params'] = {}

        # Auth
        self.data['api_key'] = ''
        self.data['authorization_code'] = ''
        self.data['refresh_token'] = ''
        self.data['pin'] = ''
