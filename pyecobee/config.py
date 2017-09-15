class Config(object):
    def __init__(self, filename='pyecobee.conf', data=None):
        self.filename = filename

    def read(self):
        if os.path.isfile(self.filename):
            try:
                with open(self.filename, 'r') as fdesc:
                    return json.loads(fdesc.read())
            except IOError as error:
                if self.log is not None:
                    self.log.exception(error)
                return False
        else:
            return {}

    def write(self):
        try:
            with open(self.filename, 'w') as fdesc:
                fdesc.write(json.dumps(self.data))
        except IOError as error:
            if self.log is not None:
                self.log.exception(error)
            return False
        return True
