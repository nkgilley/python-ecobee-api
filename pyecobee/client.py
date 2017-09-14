''' Python Code for Communication with the Ecobee Thermostat '''
<<<<<<< HEAD
import requests
import json
import os
import logging

logger = logging.getLogger('pyecobee')

class Ecobee(object):
    ''' Class for storing Ecobee Thermostats and Sensors '''

    def __init__(self, config_filename=None, api_key=None, config=None):
        self.thermostats = list()
        self.config = Config(log=logger)

=======

class Thermostat(object):
>>>>>>> getting_working
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

<<<<<<< HEAD
    def get_remote_sensors(self, index):
        ''' Return remote sensors based on index '''
        return self.thermostats[index]['remoteSensors']
=======
    def send_message(self, index, message="Hello from python-ecobee!"):
        ''' Send a message to the thermostat '''
        body = ('{"functions":[{"type":"sendMessage","params":{"text"'
                ':"' + message[0:500] + '"}}],"selection":{"selectionType"'
                ':"thermostats","selectionMatch":"'
                + self.thermostats[index]['identifier'] + '"}}')
        log_msg_action = "send message"
        return self.make_request(body, log_msg_action)
>>>>>>> getting_working

    def update(self):
        ''' Get new thermostat data from ecobee '''
        self.get_thermostats()

<<<<<<< HEAD
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
=======
    class Fan(object):
        def __init__(self):
            return True

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


    class HVAC(object):
        def __init__(self):
            return True

        def set_hvac_mode(self, index, hvac_mode):
            ''' possible hvac modes are auto, auxHeatOnly, cool, heat, off '''
            body = ('{"selection":{"selectionType":"thermostats","selectionMatch":'
                    '"' + self.thermostats[index]['identifier'] +
                    '"},"thermostat":{"settings":{"hvacMode":"' + hvac_mode +
                    '"}}}')
            log_msg_action = "set HVAC mode"
            return self.make_request(body, log_msg_action)


class Sensor(object):
    def get_remote_sensors(self, index):
        ''' Return remote sensors based on index '''
        return self.thermostats[index]['remoteSensors']

class Schedule(object):
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
>>>>>>> getting_working
        return self.make_request(body, log_msg_action)

    def set_hold_temp(self, index, cool_temp, heat_temp,
                      hold_type="nextTransition"):
        ''' Set a hold '''
        body = ('{"functions":[{"type":"setHold","params":{"holdType":"'
                + hold_type + '","coolHoldTemp":"' + str(cool_temp * 10) +
                '","heatHoldTemp":"' + str(heat_temp * 10) + '"}}],'
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

<<<<<<< HEAD
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
=======
class Ecobee(object):
    ''' Class for storing Ecobee Thermostats and Sensors '''

    def __init__(self, config_filename=None, api_key=None, config=None):
        self.thermostats = list()
        self.config = Config(log=logger)
>>>>>>> getting_working
