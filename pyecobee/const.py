"""Constants used in this library."""
import logging

_LOGGER = logging.getLogger("pyecobee")

ECOBEE_USERNAME = "USERNAME"
ECOBEE_PASSWORD = "PASSWORD"

ECOBEE_ACCESS_TOKEN = "ACCESS_TOKEN"
ECOBEE_API_KEY = "API_KEY"
ECOBEE_AUTHORIZATION_CODE = "AUTHORIZATION_CODE"
ECOBEE_REFRESH_TOKEN = "REFRESH_TOKEN"
ECOBEE_AUTH0_TOKEN = "AUTH0_TOKEN"

ECOBEE_CONFIG_FILENAME = "ecobee.conf"

ECOBEE_DEFAULT_TIMEOUT = 30

ECOBEE_OPTIONS_NOTIFICATIONS = "INCLUDE_NOTIFICATIONS"

ECOBEE_STATE_UNKNOWN = -5002
ECOBEE_STATE_CALIBRATING = -5003
ECOBEE_VALUE_UNKNOWN = "unknown"

ECOBEE_BASE_URL = "https://api.ecobee.com"
ECOBEE_AUTH_BASE_URL = "https://auth.ecobee.com"
ECOBEE_ENDPOINT_AUTH = "authorize"
ECOBEE_ENDPOINT_TOKEN = "token"
ECOBEE_ENDPOINT_THERMOSTAT = "thermostat"
ECOBEE_API_VERSION = "1"

ECOBEE_WEB_CLIENT_ID = "183eORFPlXyz9BbDZwqexHPBQoVjgadh"

ECOBEE_MODEL_TO_NAME = {
    "idtSmart": "ecobee Smart Thermostat",
    "idtEms": "ecobee Smart EMS Thermostat",
    "siSmart": "ecobee Si Smart Thermostat",
    "siEms": "ecobee Si EMS Thermostat",
    "athenaSmart": "ecobee3 Smart Thermostat",
    "athenaEms": "ecobee3 EMS Thermostat",
    "corSmart": "Carrier/Bryant Cor Thermostat",
    "nikeSmart": "ecobee3 lite Smart Thermostat",
    "nikeEms": "ecobee3 lite EMS Thermostat",
    "apolloSmart": "ecobee4 Smart Thermostat",
    "vulcanSmart": "ecobee Smart Thermostat with Voice Control",
}
