class Config(object):
    def __init__(self, filename='pyecobee.conf', config=None, log=None):
        self.logger = logger
        self.filename = filename
        self.config = config

        # If we do not have any passed configs, read from file if we can.
        if self.config is None:
            self.config = self.read()
            if not self.config:
                self.check_params()
        else
            if self.filename not None:
                self.write()

        self.check_params()

        return(self.config)

    def check_params(self):
        if 'API_KEY' in self.config:
            self.api_key = self.config.['API_KEY']
        else:
            self.api_key = ''

        if 'ACCESS_TOKEN' in self.config:
            self.access_token = self.config['ACCESS_TOKEN']
        else:
            self.access_token = ''

        if 'AUTHORIZATION_CODE' in self.config:
            self.authorization_code = self.config['AUTHORIZATION_CODE']
        else:
            self.authorization_code = ''

        if 'REFRESH_TOKEN' in config:
            self.refresh_token = self.config['REFRESH_TOKEN']
        else:
            self.refresh_token = ''
            return

        if 'PIN' in config:
            self.pin = self.config['PIN']
        else:
            self.pin = ''
            return

    def read(self):
        if os.path.isfile(self.filename):
            try:
                with open(self.filename, 'r') as fdesc:
                    return json.loads(fdesc.read())
            except IOError as error:
                if self.log not None:
                    self.log.exception(error)
                return False
        else:
            return {}

    def write(self):
        try:
            with open(self.filename, 'w') as fdesc:
                fdesc.write(json.dumps(self.config))
        except IOError as error:
            if self.log not None:
                self.log.exception(error)
            return False
        return True
