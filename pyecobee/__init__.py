''' Python Code for Communication with the Ecobee Thermostat '''
import requests
import json
import os


def config_from_file(filename, config=None):
    ''' Small configuration file management function'''
    if config:
        # We're writing configuration
        try:
            with open(filename, 'w') as fdesc:
                fdesc.write(json.dumps(config))
        except IOError as error:
            print(error)
            return False
        return True
    else:
        # We're reading config
        if os.path.isfile(filename):
            try:
                with open(filename, 'r') as fdesc:
                    return json.loads(fdesc.read())
            except IOError as error:
                return False
        else:
            return {}


class Ecobee(object):
    ''' Class for storing Ecobee Thermostats and Sensors '''

    def __init__(self, config_filename=None, api_key=None):
        self.thermostats = list()
        self.sensors = list()
        self.pin = None
        if config_filename is None:
            if api_key is None:
                print("Error. No API Key was supplied via config file or argument")
                return
            jsonconfig = {"API_KEY": api_key}
            config_filename = 'ecobee.conf'
            config_from_file(config_filename, jsonconfig)
        config = config_from_file(config_filename)
        self.api_key = config['API_KEY']
        self.config_filename = config_filename
        if 'ACCESS_TOKEN' in config:
            self.access_token = config['ACCESS_TOKEN']
        if 'AUTHORIZATION_CODE' in config:
            self.authorization_code = config['AUTHORIZATION_CODE']
        if 'sensors' in config:
            self.sensors = config['sensors']
        if 'REFRESH_TOKEN' in config:
            self.refresh_token = config['REFRESH_TOKEN']
        else:
            self.request_pin()
            return

        self.update()

    def request_pin(self):
        ''' Method to request a PIN from ecobee for authorization '''
        url = 'https://api.ecobee.com/authorize'
        params = {'response_type': 'ecobeePin',
                  'client_id': self.api_key, 'scope': 'smartWrite'}
        request = requests.get(url, params=params)
        self.authorization_code = request.json()['code']
        self.pin = request.json()['ecobeePin']
        print('Please authorize your ecobee developer app with PIN code ' + self.pin)
        print('Goto https://www.ecobee.com/consumerportal/index.html, click My Apps,')
        print('Add application, Enter Pin and click Authorize.  After authorizing, call')
        print('the request_tokens() method.')

    def request_tokens(self):
        ''' Method to request API tokens from ecobee '''
        url = 'https://api.ecobee.com/token'
        params = {'grant_type': 'ecobeePin', 'code': self.authorization_code,
                  'client_id': self.api_key}
        request = requests.post(url, params=params)
        if request.status_code == requests.codes.ok:
            self.access_token = request.json()['access_token']
            self.refresh_token = request.json()['refresh_token']
            self.write_tokens_to_file()
            self.pin = None
        else:
            print("Error while requesting tokens from ecobee.com. Status code: " + str(request.status_code))
            return

    def refresh_tokens(self):
        ''' Method to refresh API tokens from ecobee '''
        url = 'https://api.ecobee.com/token'
        params = {'grant_type': 'refresh_token', 'refresh_token': self.refresh_token,
                  'client_id': self.api_key}
        request = requests.post(url, params=params)
        if request.status_code == requests.codes.ok:
            self.access_token = request.json()['access_token']
            self.refresh_token = request.json()['refresh_token']
            self.write_tokens_to_file()
            return True
        else:
            self.request_pin()

    def get_thermostats(self):
        ''' Set self.thermostats to a json list of thermostats from ecobee '''
        url = 'https://api.ecobee.com/1/thermostat'
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.access_token}
        params = {'json': '{"selection":{"selectionType":"registered","includeRuntime":"true","includeSensors":"true","includeProgram":"true","includeEquipmentStatus":true,"includeSettings":true}}'}
        request = requests.get(url, headers=header, params=params)
        if request.status_code == requests.codes.ok:
            self.thermostats = request.json()['thermostatList']
        else:
            print("Error connecting to Ecobee while attempting to get thermostat data.  Refreshing tokens and trying again.")
            if self.refresh_tokens():
                self.get_thermostats()

    def get_thermostat(self, index):
        ''' Return a single thermostat based on index '''
        return self.thermostats[index]

    def get_remote_sensors(self, index):
        ''' Get remote sensor data and store in sensors '''
        return self.thermostats[index]['remoteSensors']

    def set_hvac_mode(self, index, hvac_mode):
        ''' possible hvac modes are auto, auxHeatOnly, cool, heat, off '''
        url = 'https://api.ecobee.com/1/thermostat'
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.access_token}
        params = {'format': 'json'}
        body = '{"selection":{"selectionType":"thermostats","selectionMatch":"' + self.thermostats[index]['identifier'] + '"},"thermostat":{"settings":{"hvacMode":"' + hvac_mode + '"}}}'
        request = requests.post(url, headers=header, params=params, data=body)
        if request.status_code == requests.codes.ok:
            return request
        else:
            print("Error connecting to Ecobee while attempting to set HVAC mode.  Refreshing tokens...")
            self.refresh_tokens()

    def set_hold_temp(self, index, cool_temp, heat_temp, hold_type="nextTransition"):
        ''' Set a hold '''
        url = 'https://api.ecobee.com/1/thermostat'
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.access_token}
        params = {'format': 'json'}
        body = '{"functions":[{"type":"setHold","params":{"holdType":"' + hold_type + '","coolHoldTemp":"' + str(
            cool_temp * 10) + '","heatHoldTemp":"' + str(heat_temp * 10) + '"}}],"selection":{"selectionType":"thermostats","selectionMatch":"' + self.thermostats[index]['identifier'] + '"}}'
        request = requests.post(url, headers=header, params=params, data=body)
        if request.status_code == requests.codes.ok:
            return request
        else:
            print("Error connecting to Ecobee while attempting to set hold temp.  Refreshing tokens...")
            self.refresh_tokens()

    def set_climate_hold(self, index, climate, hold_type="nextTransition"):
        ''' Set a climate hold - ie away, home, sleep '''
        url = 'https://api.ecobee.com/1/thermostat'
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.access_token}
        params = {'format': 'json'}
        body = '{"functions":[{"type":"setHold","params":{"holdType":"' + hold_type + '","holdClimateRef":"' + \
            climate + \
            '"}}],"selection":{"selectionType":"thermostats","selectionMatch":"' + self.thermostats[index]['identifier'] + '"}}'
        request = requests.post(url, headers=header, params=params, data=body)
        if request.status_code == requests.codes.ok:
            return request
        else:
            print("Error connecting to Ecobee while attempting to set climate hold.  Refreshing tokens...")
            self.refresh_tokens()

    def resume_program(self, index, resume_all="false"):
        ''' Resume currently scheduled program '''
        url = 'https://api.ecobee.com/1/thermostat'
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.access_token}
        params = {'format': 'json'}
        body = '{"functions":[{"type":"resumeProgram","params":{"resumeAll":"' + \
            resume_all + \
            '"}}],"selection":{"selectionType":"thermostats","selectionMatch":"' + self.thermostats[index]['identifier'] + '"}}'
        request = requests.post(url, headers=header, params=params, data=body)
        if request.status_code == requests.codes.ok:
            return request
        else:
            print("Error connecting to Ecobee while attempting to resume program.  Refreshing tokens...")
            self.refresh_tokens()

    def write_tokens_to_file(self):
        ''' Write api tokens to a file '''
        config = dict()
        config['API_KEY'] = self.api_key
        config['ACCESS_TOKEN'] = self.access_token
        config['REFRESH_TOKEN'] = self.refresh_token
        config['AUTHORIZATION_CODE'] = self.authorization_code
        config_from_file(self.config_filename, config)

    def update(self):
        ''' Get new thermostat data from ecobee '''
        self.get_thermostats()

