import requests
from .rest import Rest

class Auth(object):
    def __init__(self, data):
        #self.authenticated = False
        #self.pin = None
        self.rest = Rest(data)
        self.data = data

    def request_pin(self):
        ''' Method to request a PIN from ecobee for authorization '''

        params = {'response_type': 'ecobeePin', 'scope': 'smartWrite', 'client_id': self.data['auth']['api_key']}
        request = self.rest._get("authorize", params=params)

        self.data['auth']['code'] = request.json()['authorization_code']
        self.data['auth']['pin'] = request.json()['ecobeePin']
        self.data['auth']['pin']['scoope'] = request.json()['scope']
        self.data['auth']['pin']['expires'] = request.json()['expires_in']

    def request_tokens(self):
        ''' Method to request API tokens from ecobee '''

        params = {'grant_type': 'ecobeePin', 'code': self.data['auth']['code'], 'client_id': self.data['auth']['api_key']}
        request = rest._get("token", params=params)

        self.data['token']['access'] = request.json()['access_token']
        self.data['token']['expires'] = request.json()['expires_in']
        self.data['token']['refresh'] = request.json()['refresh_token']
        self.data['token']['scope'] = request.json()['scope']


    def refresh_tokens(self):
        ''' Method to refresh API tokens from ecobee '''

        params = {'grant_type': 'refresh_token', 'refresh_token': self.data['token']['refresh'], 'client_id': self.data['auth']['api_key']}
        request = self.rest._post("token", params=params)

        self.data['token']['access'] = request.json()['access_token']
        self.data['token']['expires'] = request.json()['expires_in']
        self.data['token']['refresh'] = request.json()['refresh_token']
        self.data['token']['scope'] = request.json()['scope']

    def make_request(self, body, log_msg_action):
        url = 'https://api.ecobee.com/1/thermostat'
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.data['token']['access']}
        params = {'format': 'json'}
        request = requests.post(url, headers=header, params=params, data=body)
        if request.status_code == requests.codes.ok:
            return request
        else:
            logger.info("Error connecting to Ecobee while attempting to %s.  "
                        "Refreshing tokens and trying again.", log_msg_action)
            if self.refresh_tokens():
                return self.make_request(body)
            else:
                return None
