import requests
from .rest import Rest

class Auth(object):
    def __init__(self, api_key, config):
        self.authenticated = False
        self.pin = None
        self.rest = Rest()
        self.config = config

    def request_pin(self):
        ''' Method to request a PIN from ecobee for authorization '''

        params = {'response_type': 'ecobeePin', 'scope': 'smartWrite', 'client_id': self.config.api_key}
        request = self.rest._get("authorize", params=params)

        self.config.authorization_code = request.json()['code']
        self.config.pin = request.json()['ecobeePin']
        self.config.pin_scope = request.json()['scope']
        self.config.pin_expires_in = request.json()['expires_in']

    def request_tokens(self):
        ''' Method to request API tokens from ecobee '''

        params = {'grant_type': 'ecobeePin', 'code': self.config.authorization_code, 'client_id': self.config.api_key}
        request = rest._get("token", params=params)

        self.config.token_access = request.json()['access_token']
        self.config.token_expires = request.json()['expires_in']
        self.config.token_refresh = request.json()['refresh_token']
        self.config.token_scope = request.json()['scope']


    def refresh_tokens(self):
        ''' Method to refresh API tokens from ecobee '''

        params = {'grant_type': 'refresh_token', 'refresh_token': self.refresh_token, 'client_id': self.api_key}
        request = self.rest._post("token", params=params)

        self.config.token_access = request.json()['access_token']
        self.config.token_expires = request.json()['expires_in']
        self.config.token_refresh = request.json()['refresh_token']
        self.config.token_scope = request.json()['scope']

    def make_request(self, body, log_msg_action):
        url = 'https://api.ecobee.com/1/thermostat'
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.access_token}
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
