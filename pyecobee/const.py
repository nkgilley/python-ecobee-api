"""Constants used in this library."""
import logging
from typing import Dict, Final

_LOGGER: Final[logging.Logger] = logging.getLogger("pyecobee")

ECOBEE_USERNAME: Final[str] = "USERNAME"
ECOBEE_PASSWORD: Final[str] = "PASSWORD"

ECOBEE_ACCESS_TOKEN: Final[str] = "ACCESS_TOKEN"
ECOBEE_API_KEY: Final[str] = "API_KEY"
ECOBEE_AUTHORIZATION_CODE: Final[str] = "AUTHORIZATION_CODE"
ECOBEE_REFRESH_TOKEN: Final[str] = "REFRESH_TOKEN"
ECOBEE_AUTH0_TOKEN: Final[str] = "AUTH0_TOKEN"

ECOBEE_CONFIG_FILENAME: Final[str] = "ecobee.conf"

ECOBEE_DEFAULT_TIMEOUT: Final[int] = 30

ECOBEE_OPTIONS_NOTIFICATIONS: Final[str] = "INCLUDE_NOTIFICATIONS"

ECOBEE_STATE_UNKNOWN: Final[int] = -5002
ECOBEE_STATE_CALIBRATING: Final[int] = -5003
ECOBEE_VALUE_UNKNOWN: Final[str] = "unknown"

ECOBEE_BASE_URL: Final[str] = "https://api.ecobee.com"
ECOBEE_AUTH_BASE_URL: Final[str] = "https://auth.ecobee.com"
ECOBEE_ENDPOINT_AUTH: Final[str] = "authorize"
ECOBEE_ENDPOINT_TOKEN: Final[str] = "token"
ECOBEE_ENDPOINT_THERMOSTAT: Final[str] = "thermostat"
ECOBEE_API_VERSION: Final[str] = "1"

ECOBEE_WEB_CLIENT_ID: Final[str] = "183eORFPlXyz9BbDZwqexHPBQoVjgadh"
ECOBEE_REDIRECT_URI: Final[str] = "https://www.ecobee.com/home/authCallback"
ECOBEE_AUDIENCE: Final[str] = "https://prod.ecobee.com/api/v1"
ECOBEE_WEB_SCOPE: Final[str] = (
    "openid offline_access smartWrite piiWrite piiRead smartRead deleteGrants"
)
ECOBEE_OAUTH_TOKEN_URL: Final[str] = f"{ECOBEE_AUTH_BASE_URL}/oauth/token"
ECOBEE_MFA_OTP_CHALLENGE_PATH: Final[str] = "/u/mfa-otp-challenge"
ECOBEE_MFA_SMS_CHALLENGE_PATH: Final[str] = "/u/mfa-sms-challenge"

ECOBEE_MODEL_TO_NAME: Final[Dict[str, str]] = {
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
