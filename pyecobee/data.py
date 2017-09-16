import platform, pkg_resources
from collections import defaultdict

class Data(object):
    def __init__(self):
        # Rest stuff
        #version = pkg_resources.require("pyecobee")[0].version

        self.store = self.nested_dict(7, str)

        self.store['name'] = 'pyecobee-v2'
        self.store['author'] = 'Matt Deren'

        self.store['sources'][0]['name'] = 'Nolan Gilley'
        self.store['sources'][0]['company'] = 'Unknown'
        self.store['sources'][0]['url'][0] = 'https://github.com/nkgilley/python-ecobee-api'
        self.store['sources'][0]['license'][0] = 'https://github.com/derenma/python-ecobee-api/blob/master/LICENSE.txt'
        self.store['sources'][0]['comment'] = "Core code; v1; Designed for use with Home-Assistant "

        self.store['sources'][1]['name'] = 'Justin Cooper & Tony DiCola'
        self.store['sources'][1]['company'] = 'Adafruit Industries'
        self.store['sources'][1]['license'][0] = 'https://github.com/derenma/io-client-python/blob/master/LICENSE.md'
        self.store['sources'][1]['url'][0] = 'https://github.com/adafruit/io-client-python'
        self.store['sources'][1]['url'][1] = 'https://github.com/adafruit/io-client-python/blob/master/Adafruit_IO/client.py'
        self.store['sources'][1]['url'][2] = 'https://github.com/adafruit/io-client-python/blob/master/Adafruit_IO/errors.py'
        self.store['sources'][1]['comment'] = "REST structuring; Error handling"

        self.store['sources'][2]['name'] = 'Matt Deren'
        self.store['sources'][2]['company'] = 'N/A'
        self.store['sources'][2]['license'][0] = 'https://github.com/derenma/python-ecobee-api/blob/master/LICENSE.txt'
        self.store['sources'][2]['url'][0] = 'https://github.com/nkgilley/python-ecobee-api'
        self.store['sources'][2]['comment'] = "V2; Major refactor; Function additions; Branched away from Home-Assistant"

        self.store['version'] = "0.2.0"
        '''
        self.store['rest']['default_headers'] = {'User-Agent': 'pyechobe-agent/{0} ({1}, {2} {3})'.format(self.store['version'],
                                                                              platform.platform(),
                                                                              platform.python_implementation(),
                                                                              platform.python_version()),
                                                'Content-Type': 'application/json;charset=UTF-8'}

        # Place holder for all parameters
        self.store['rest']['default_params'] = {}
        '''

        # Auth
        self.store['auth']['api_key'] = ''
        self.store['auth']['code'] = ''
        self.store['auth']['pin']['value'] = ''
        self.store['auth']['pin']['scope'] = ''
        self.store['auth']['pin']['expires'] = ''
        self.store['token']['access'] = ''
        self.store['token']['expires'] = ''
        self.store['token']['refresh'] = ''
        self.store['token']['scope'] = ''

        #Thermostat array
        self.store['thermostats'] = []

        #All of our JSON
        #Header for making requests
        ''' make_request '''
        url = 'https://api.ecobee.com/1/thermostat'
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.store['token']['access']}
        params = {'format': 'json'}

        #Auth
        ''' Base URL for EcoBee REST API '''
        self.store['rest']['base_url'] = 'https://api.ecobee.com/'
        self.store['rest']['api_version'] = "1"

        ''' Method to request a PIN from ecobee for authorization '''
        self.store['rest']['request_pin']['url'] = self.store['rest']['base_url'] + 'authorize'
        self.store['rest']['request_pin']['params']['response_type'] = "ecobeePin"
        self.store['rest']['request_pin']['params']['client_id'] = self.store['auth']['api_key']
        self.store['rest']['request_pin']['params']['scope'] = 'smartWrite'

        ''' Method to request API tokens from ecobee '''
        self.store['rest']['request_token']['url'] = self.store['rest']['base_url'] + 'token'
        self.store['rest']['request_token']['params']['grant_type'] = "ecobeePin"
        self.store['rest']['request_token']['params']['code'] = self.store['auth']['code']
        self.store['rest']['request_token']['params']['client_id'] = self.store['auth']['api_key']


        ''' Method to refresh API tokens from ecobee '''
        self.store['rest']['refresh_token']['url'] = self.store['rest']['base_url'] + 'token'
        self.store['rest']['refresh_token']['params']['grant_type'] = "refresh_token"
        self.store['rest']['refresh_token']['params']['code'] = self.store['auth']['token']['refresh']
        self.store['rest']['refresh_token']['params']['client_id'] = self.store['auth']['api_key']

        #Control
        '''
        Set self.thermostats to a json list of thermostats from ecobee
        Input: access_token

        url = 'https://api.ecobee.com/1/thermostat'
        header = {'Authorization': 'Bearer ' + self.access_token}
        params = {'json': ('{"selection":'
                                '{"selectionType":"registered",'
                                '"includeRuntime":"true",'
                                '"includeSensors":"true",'
                                '"includeProgram":"true",'
                                '"includeEquipmentStatus":"true",'
                                '"includeEvents":"true",'
                                '"includeSettings":"true"}}')}
        '''

        #All of our rest stuff... We can convert this to JSON directly we also have our python dictionary!

        '''
        Thermostat Functions
        '''
        self.store['rest']['thermostat']['base_url'] = self.store['rest']['base_url'] + '/' + self.store['rest']['api_version'] + '/thermostat'
        self.store['rest']['thermostat']['selection']['selectionType'] = "registered"
        self.store['rest']['thermostat']['selection']['selectionMatch'] = ""

        # Ack!
        self.store['rest']['thermostat']['functions']['acknoledge']['type'] = "acknoledge"
        self.store['rest']['thermostat']['functions']['acknoledge']['params']['ackRef'] = ""
        # ackType: accept, decline, defer, unacknowledged
        self.store['rest']['thermostat']['functions']['acknoledge']['params']['ackType'] = ""
        self.store['rest']['thermostat']['functions']['acknoledge']['params']['remindMeLater'] = False

        # controlPlug
        self.store['rest']['thermostat']['functions']['controlPlug']['type'] = 'controlPlug'
        self.store['rest']['thermostat']['functions']['controlPlug']['params']['plugName'] = ""
        # plugState: on, off, resume.
        self.store['rest']['thermostat']['functions']['controlPlug']['params']['plugState'] = ""
        self.store['rest']['thermostat']['functions']['controlPlug']['params']['startDate'] = ""
        self.store['rest']['thermostat']['functions']['controlPlug']['params']['startTime'] = ""
        self.store['rest']['thermostat']['functions']['controlPlug']['params']['endDate'] = ""
        self.store['rest']['thermostat']['functions']['controlPlug']['params']['endTime'] = ""
        # holdType: dateTime, nextTransition, indefinite, holdHours
        self.store['rest']['thermostat']['functions']['controlPlug']['params']['holdType'] = ""
        self.store['rest']['thermostat']['functions']['controlPlug']['params']['holdHours'] = ""

        # createVaction
        self.store['rest']['thermostat']['functions']['createVacation']['type'] = 'createVacation'
        self.store['rest']['thermostat']['functions']['createVacation']['params']['name'] = ""
        self.store['rest']['thermostat']['functions']['createVacation']['params']['coolHoldTemp'] = ""
        self.store['rest']['thermostat']['functions']['createVacation']['params']['heatHoldTemp'] = ""
        self.store['rest']['thermostat']['functions']['createVacation']['params']['startDate'] = ""
        self.store['rest']['thermostat']['functions']['createVacation']['params']['startTime'] = ""
        self.store['rest']['thermostat']['functions']['createVacation']['params']['endDate'] = ""
        self.store['rest']['thermostat']['functions']['createVacation']['params']['endTime'] = ""
        # fan: auto, on Default: auto
        self.store['rest']['thermostat']['functions']['createVacation']['params']['fan'] = ""
        # fanMinOnTime: 0-60 Default: )
        self.store['rest']['thermostat']['functions']['createVacation']['params']['fanMinOnTime'] = ""

        # deleteVacation
        self.store['rest']['thermostat']['functions']['deleteVacation']['type'] = 'deleteVacation'
        self.store['rest']['thermostat']['functions']['deleteVacation']['params']['name'] = ""

        # resetPreferences
        self.store['rest']['thermostat']['functions']['resetPreferences']['type'] = 'resetPreferences'
        self.store['rest']['thermostat']['functions']['resetPreferences']['params'] = None

        # resumeProgram
        self.store['rest']['thermostat']['functions']['resumeProgram']['type'] = 'resumeProgram'
        self.store['rest']['thermostat']['functions']['resumeProgram']['params'] = None

        # sendMessage
        self.store['rest']['thermostat']['functions']['sendMessage']['type'] = 'sendMessage'
        self.store['rest']['thermostat']['functions']['sendMessage']['params']['text'] = ""

        # setHold
        # datetime: not set for NOW
        self.store['rest']['thermostat']['functions']['setHold']['type'] = 'setHold'
        self.store['rest']['thermostat']['functions']['setHold']['params']['coolHoldTemp'] = ""
        self.store['rest']['thermostat']['functions']['setHold']['params']['heatHoldTemp'] = ""
        self.store['rest']['thermostat']['functions']['setHold']['params']['holdClimateRef'] = ""
        # datetime: not set for NOW
        self.store['rest']['thermostat']['functions']['setHold']['params']['startDate'] = ''
        self.store['rest']['thermostat']['functions']['setHold']['params']['startTime'] = ''
        self.store['rest']['thermostat']['functions']['setHold']['params']['endDate'] = ''
        self.store['rest']['thermostat']['functions']['setHold']['params']['endTime'] = ''
        self.store['rest']['thermostat']['functions']['setHold']['params']['holdType'] = ''
        # holdHours: number of hours to hold
        self.store['rest']['thermostat']['functions']['setHold']['params']['holdHours'] = ''

        # setOccupied
        self.store['rest']['thermostat']['functions']['setOccupied']['type'] = 'setOccupied'
        self.store['rest']['thermostat']['functions']['setOccupied']['params']['occupied'] = False
        self.store['rest']['thermostat']['functions']['setOccupied']['params']['startDate'] = ''
        self.store['rest']['thermostat']['functions']['setOccupied']['params']['startTime'] = ''
        self.store['rest']['thermostat']['functions']['setOccupied']['params']['endDate'] = ''
        self.store['rest']['thermostat']['functions']['setOccupied']['params']['endTime'] = ''
        self.store['rest']['thermostat']['functions']['setOccupied']['params']['holdType'] = ''
        # holdHours: number of hours to hold
        self.store['rest']['thermostat']['functions']['setHold']['params']['holdHours'] = ''

        # unlinkVoiceEngine
        self.store['rest']['thermostat']['functions']['unlinkVoiceEngine']['type'] = 'unlinkVoiceEngine'
        self.store['rest']['thermostat']['functions']['unlinkVoiceEngine']['params']['name'] = ""

        # updateSensor
        self.store['rest']['thermostat']['functions']['updateSensor']['type'] = 'updateSensor'
        self.store['rest']['thermostat']['functions']['updateSensor']['params']['name'] = ""
        self.store['rest']['thermostat']['functions']['updateSensor']['params']['deviceId'] = ""
        self.store['rest']['thermostat']['functions']['updateSensor']['params']['sensorId'] = ""

    def nested_dict(self, n, type):
        if n == 1:
            return defaultdict(type)
        else:
            return defaultdict(lambda: self.nested_dict(n-1, type))
