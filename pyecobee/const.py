"""Constants used in this library."""
import logging

_LOGGER = logging.getLogger("pyecobee")

ECOBEE_ACCESS_TOKEN = "ACCESS_TOKEN"
ECOBEE_API_KEY = "API_KEY"
ECOBEE_AUTHORIZATION_CODE = "AUTHORIZATION_CODE"
ECOBEE_REFRESH_TOKEN = "REFRESH_TOKEN"

ECOBEE_CONFIG_FILENAME = "ecobee.conf"

ECOBEE_STATE_UNKNOWN = -5002
ECOBEE_STATE_CALIBRATING = -5003
ECOBEE_VALUE_UNKNOWN = "unknown"

ECOBEE_BASE_URL = "https://api.ecobee.com"
ECOBEE_ENDPOINT_AUTH = "authorize"
ECOBEE_ENDPOINT_TOKEN = "token"
ECOBEE_ENDPOINT_THERMOSTAT = "thermostat"
ECOBEE_API_VERSION = "1"

ECOBEE_MODEL_TO_NAME = {
    "idtSmart": "ecobee Smart",
    "idtEms": "ecobee Smart EMS",
    "siSmart": "ecobee Si Smart",
    "siEms": "ecobee Si EMS",
    "athenaSmart": "ecobee3 Smart",
    "athenaEms": "ecobee3 EMS",
    "corSmart": "Carrier/Bryant Cor",
    "nikeSmart": "ecobee3 lite Smart",
    "nikeEms": "ecobee3 lite EMS",
    "apolloSmart": "ecobee4 Smart",
    "vulcanSmart": "ecobee4 Smart",
}
