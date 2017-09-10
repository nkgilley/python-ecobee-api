class Config(object):
    def __init__(self, filename='pyecobee.conf', config=None, log=None):
        self.logger = logger
        self.filename = filename
        self.settings = config

    def read(self):
        if os.path.isfile(self.filename):
            try:
                with open(self.filename, 'r') as fdesc:
                    return json.loads(self.settings)
            except IOError as error:
                if self.log not None:
                    self.log.exception(error)
                return False
        else:
            return {}

    def write(self):
        try:
            with open(self.filename, 'w') as fdesc:
                fdesc.write(json.dumps(self.settings))
        except IOError as error:
            if self.log not None:
                self.log.exception(error)
            return False
        return True
