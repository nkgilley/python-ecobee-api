import os,json
import md5

class Config(object):
    def __init__(self, data, filename='pyecobee.conf'):
        self.data = data
        self.filename = filename

        if os.path.exists('pyecobee.conf'):
            print "reading config"
            self.data = self.read()
        else:
            return

    def read(self, filename='pyecobee.conf'):
        if os.path.isfile(self.filename):
            try:
                with open(self.filename, 'r') as fdesc:
                    return json.loads(fdesc.read())
            except IOError as error:
                print "read io error"
        else:
            return {}

    def write(self, data, filename='pyecobee.conf'):
        try:
            with open(self.filename, 'w') as fdesc:
                fdesc.write(json.dumps(data.store, indent=4, sort_keys=True))
        except IOError as error:
            if self.log is not None:
                self.log.exception(error)
            return False
        return True
