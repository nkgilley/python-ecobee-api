import platform, pkg_resources, json
from collections import defaultdict

class Data(object):
    def __init__(self, api_key):
        self.store = self.nested_dict(7, dict)
        self.store['rest']['request_pin']['params'] = {}

        # Rest stuff
        #self.store = self.nested_dict(7, str)

#        ''' Base URL for EcoBee REST API '''
        self.store['rest']['base_url'] = 'https://api.ecobee.com/'
        self.store['rest']['api_version'] = "1"

    def request_pin(self):
        ''' Method to request a PIN from ecobee for authorization '''
        #params = {}
        #url = self.store['rest']['base_url'] + 'authorize'
        #params = self.store['rest']['request_pin']['params']
        params['response_type'] = "ecobeePin"
        params['client_id'] = self.store['auth']['api_key']
        params['scope'] = 'smartWrite'

        self.store['rest']['request_pin']['url'] = self.store['rest']['base_url'] + 'authorize'
        self.store['rest']['request_pin']['params'].update(params)

        print json.dumps(self.store)

    def request_token(self):
        ''' Method to request TOKENS from ecobee '''
        self.store['request_token']['url'] = self.store['rest']['base_url'] + 'token'
        self.store['request_token']['params']['grant_type'] = "ecobeePin"
        self.store['rest']['request_token']['params']['code'] = self.store['auth']['code']
        self.store['rest']['request_token']['params']['client_id'] = self.store['auth']['api_key']

    def nested_dict(self, n, type):
        if n == 1:
            return defaultdict(type)
        else:
            return defaultdict(lambda: self.nested_dict(n-1, type))
