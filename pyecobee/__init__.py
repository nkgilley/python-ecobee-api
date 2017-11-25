''' Python Code for Communication with the Ecobee Thermostat '''
import requests
import json
import os
import logging

logger = logging.getLogger('pyecobee')


def config_from_file(filename, config=None):
    ''' Small configuration file management function'''
    if config:
        # We're writing configuration
        try:
            with open(filename, 'w') as fdesc:
                fdesc.write(json.dumps(config))
        except IOError as error:
            logger.exception(error)
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

    def __init__(self, config_filename=None, api_key=None, config=None):
        self.thermostats = list()
        self.pin = None
        self.authenticated = False

        if config is None:
            self.file_based_config = True
            if config_filename is None:
                if api_key is None:
                    logger.error("Error. No API Key was supplied.")
                    return
                jsonconfig = {"API_KEY": api_key}
                config_filename = 'ecobee.conf'
                config_from_file(config_filename, jsonconfig)
            config = config_from_file(config_filename)
        else:
            self.file_based_config = False
        self.api_key = config['API_KEY']
        self.config_filename = config_filename

        if 'ACCESS_TOKEN' in config:
            self.access_token = config['ACCESS_TOKEN']
        else:
            self.access_token = ''

        if 'AUTHORIZATION_CODE' in config:
            self.authorization_code = config['AUTHORIZATION_CODE']
        else:
            self.authorization_code = ''

        if 'REFRESH_TOKEN' in config:
            self.refresh_token = config['REFRESH_TOKEN']
        else:
            self.refresh_token = ''
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
        logger.error('Please authorize your ecobee developer app with PIN code '
              + self.pin + '\nGoto https://www.ecobee.com/consumerportal'
              '/index.html, click\nMy Apps, Add application, Enter Pin'
              ' and click Authorize.\nAfter authorizing, call request_'
              'tokens() method.')

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
            logger.warn('Error while requesting tokens from ecobee.com.'
                  ' Status code: ' + str(request.status_code))
            return

    def refresh_tokens(self):
        ''' Method to refresh API tokens from ecobee '''
        url = 'https://api.ecobee.com/token'
        params = {'grant_type': 'refresh_token',
                  'refresh_token': self.refresh_token,
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
        params = {'json': ('{"selection":{"selectionType":"registered",'
                            '"includeRuntime":"true",'
                            '"includeSensors":"true",'
                            '"includeProgram":"true",'
                            '"includeEquipmentStatus":"true",'
                            '"includeEvents":"true",'
                            '"includeWeather":"true",'
                            '"includeSettings":"true"}}')}
        request = requests.get(url, headers=header, params=params)
        if request.status_code == requests.codes.ok:
            self.authenticated = True
            self.thermostats = request.json()['thermostatList']
            return self.thermostats
        else:
            self.authenticated = False
            logger.info("Error connecting to Ecobee while attempting to get "
                  "thermostat data.  Refreshing tokens and trying again.")
            if self.refresh_tokens():
                return self.get_thermostats()
            else:
                return None

    def get_thermostat(self, index):
        ''' Return a single thermostat based on index '''
        return self.thermostats[index]

    def get_remote_sensors(self, index):
        ''' Return remote sensors based on index '''
        return self.thermostats[index]['remoteSensors']

    def write_tokens_to_file(self):
        ''' Write api tokens to a file '''
        config = dict()
        config['API_KEY'] = self.api_key
        config['ACCESS_TOKEN'] = self.access_token
        config['REFRESH_TOKEN'] = self.refresh_token
        config['AUTHORIZATION_CODE'] = self.authorization_code
        if self.file_based_config:
            config_from_file(self.config_filename, config)
        else:
            self.config = config

    def update(self):
        ''' Get new thermostat data from ecobee '''
        self.get_thermostats()

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

    def set_hvac_mode(self, index, hvac_mode):
        ''' possible hvac modes are auto, auxHeatOnly, cool, heat, off '''
        body = ('{"selection":{"selectionType":"thermostats","selectionMatch":'
                '"' + self.thermostats[index]['identifier'] +
                '"},"thermostat":{"settings":{"hvacMode":"' + hvac_mode +
                '"}}}')
        log_msg_action = "set HVAC mode"
        return self.make_request(body, log_msg_action)

    def set_fan_min_on_time(self, index, fan_min_on_time):
        ''' The minimum time, in minutes, to run the fan each hour. Value from 1 to 60 '''
        body = ('{"selection":{"selectionType":"thermostats","selectionMatch":'
                '"' + self.thermostats[index]['identifier'] +
                '"},"thermostat":{"settings":{"fanMinOnTime":"' + fan_min_on_time +
                '"}}}')
        log_msg_action = "set fan minimum on time."
        return self.make_request(body, log_msg_action)

    def set_fan_mode(self, index, fan_mode):
        ''' Set fan mode. Values: auto, minontime, on '''
        body = ('{"selection":{"selectionType":"thermostats","selectionMatch":'
                '"' + self.thermostats[index]['identifier'] +
                '"},"thermostat":{"settings":{"vent":"' + fan_mode +
                '"}}}')
        log_msg_action = "set fan mode"
        return self.make_request(body, log_msg_action)

    def set_hold_temp(self, index, cool_temp, heat_temp,
                      hold_type="nextTransition"):
        ''' Set a hold '''
        body = ('{"functions":[{"type":"setHold","params":{"holdType":"'
                + hold_type + '","coolHoldTemp":"' + str(int(cool_temp * 10)) +
                '","heatHoldTemp":"' + str(int(heat_temp * 10)) + '"}}],'
                '"selection":{"selectionType":"thermostats","selectionMatch"'
                ':"' + self.thermostats[index]['identifier'] + '"}}')
        log_msg_action = "set hold temp"
        return self.make_request(body, log_msg_action)

    def set_climate_hold(self, index, climate, hold_type="nextTransition"):
        ''' Set a climate hold - ie away, home, sleep '''
        body = ('{"functions":[{"type":"setHold","params":{"holdType":"'
                + hold_type + '","holdClimateRef":"' + climate + '"}}],'
                '"selection":{"selectionType":"thermostats","selectionMatch"'
                ':"' + self.thermostats[index]['identifier'] + '"}}')
        log_msg_action = "set climate hold"
        return self.make_request(body, log_msg_action)

    def delete_vacation(self, index, vacation):
        ''' Delete the vacation with name vacation '''
        body = ('{"functions":[{"type":"deleteVacation","params":{"name":"'
                + vacation + '"}}],'
                '"selection":{"selectionType":"registered","selectionMatch":"'
                '"}}')
        log_msg_action = "delete a vacation"
        return self.make_request(body, log_msg_action)

    def resume_program(self, index, resume_all="false"):
        ''' Resume currently scheduled program '''
        body = ('{"functions":[{"type":"resumeProgram","params":{"resumeAll"'
                ':"' + resume_all + '"}}],"selection":{"selectionType"'
                ':"thermostats","selectionMatch":"'
                + self.thermostats[index]['identifier'] + '"}}')
        log_msg_action = "resume program"
        return self.make_request(body, log_msg_action)

    def send_message(self, index, message="Hello from python-ecobee!"):
        ''' Send a message to the thermostat '''
        body = ('{"functions":[{"type":"sendMessage","params":{"text"'
                ':"' + message[0:500] + '"}}],"selection":{"selectionType"'
                ':"thermostats","selectionMatch":"'
                + self.thermostats[index]['identifier'] + '"}}')
        log_msg_action = "send message"
        return self.make_request(body, log_msg_action)

    def set_humidity(self, index, humidity):
        ''' Set humidity level'''
        body = ('{"selection":{"selectionType":"thermostats","selectionMatch":'
                '"' + self.thermostats[index]['identifier'] +
                '"},"thermostat":{"settings":{"humidity":"' + str(int(humidity)) +
                '"}}}')
        log_msg_action = "set humidity level"
        return self.make_request(body, log_msg_action)
