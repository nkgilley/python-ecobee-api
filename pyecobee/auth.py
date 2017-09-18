import requests, json
from .rest import Rest

class Auth(object):
    def __init__(self, data):
        self.data = data
        self.rest = Rest(data)
        self.request_pin()
        self.request_tokens()

    def connect(self):
        return True

    def test_pin(self):
        ''' Test previously saved PIN '''

    def request_pin(self):
        ''' Method to request a PIN from ecobee for authorization '''

        self.data.request_pin()
        params = self.data.store['rest']['request_pin']['params']
        url = self.data.store['rest']['request_pin']['url']
        request = self.rest._get(url, params=json.loads(params))
        self.data.store['auth']['pin'] = request


    def request_tokens(self):
        ''' Method to request API tokens from ecobee '''

        self.data.request_token()
        params = json.dumps(self.data.store['rest']['request_token']['params'])
        url = self.data.store['rest']['request_token']['url']
        request = self.rest._get(url, params=json.loads(params))

        print request
        self.data.store['auth']['token'] = request

    def refresh_tokens(self):
        ''' Method to refresh API tokens from ecobee '''

        params = {'grant_type': 'refresh_token', 'refresh_token': self.data.store['token']['refresh'], 'client_id': self.data.store['auth']['api_key']}
        request = self.rest._post("token", params=params)

        print json.dumps(self.data.store['auth'])

        #self.data.store['token']['access'] = request.json()['access_token']
        #self.data.store['token']['expires'] = request.json()['expires_in']
        #self.data.store['token']['refresh'] = request.json()['refresh_token']
        #self.data.store['token']['scope'] = request.json()['scope']

    def make_request(self, body, log_msg_action):
        url = 'https://api.ecobee.com/1/thermostat'
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.data.store['token']['access']}
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
