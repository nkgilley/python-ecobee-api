""" Python Code for Communication with the Ecobee Thermostat """
import datetime
from typing import Optional

import requests
from requests.exceptions import HTTPError, RequestException, Timeout

try:
    import simplejson as json
except ImportError:
    import json

from .const import (
    _LOGGER,
    ECOBEE_ACCESS_TOKEN,
    ECOBEE_API_KEY,
    ECOBEE_API_VERSION,
    ECOBEE_AUTH0_TOKEN,
    ECOBEE_AUTH_BASE_URL,
    ECOBEE_AUTHORIZATION_CODE,
    ECOBEE_BASE_URL,
    ECOBEE_CONFIG_FILENAME,
    ECOBEE_DEFAULT_TIMEOUT,
    ECOBEE_ENDPOINT_AUTH,
    ECOBEE_ENDPOINT_THERMOSTAT,
    ECOBEE_ENDPOINT_TOKEN,
    ECOBEE_OPTIONS_NOTIFICATIONS,
    ECOBEE_PASSWORD,
    ECOBEE_REFRESH_TOKEN,
    ECOBEE_USERNAME,
    ECOBEE_WEB_CLIENT_ID,
)
from .errors import ExpiredTokenError, InvalidSensorError, InvalidTokenError
from .util import config_from_file, convert_to_bool


class Ecobee(object):
    """Class for communicating with the ecobee API."""

    def __init__(self, config_filename: str = None, config: dict = None):
        self.thermostats = None
        self.config_filename = config_filename
        self.config = config
        self.api_key = None
        self.pin = None
        self.authorization_code = None
        self.access_token = None
        self.refresh_token = None
        self.username = None
        self.password = None
        self.auth0_token = None
        self.include_notifications = False

        if self.config_filename is None and self.config is None:
            _LOGGER.error("No ecobee credentials supplied, unable to continue")
            return

        if self.config:
            self._file_based_config = False
            self.api_key = self.config.get(ECOBEE_API_KEY)
            if ECOBEE_ACCESS_TOKEN in self.config:
                self.access_token = self.config[ECOBEE_ACCESS_TOKEN]
            if ECOBEE_AUTHORIZATION_CODE in self.config:
                self.authorization_code = self.config[ECOBEE_AUTHORIZATION_CODE]
            if ECOBEE_REFRESH_TOKEN in self.config:
                self.refresh_token = self.config[ECOBEE_REFRESH_TOKEN]
            if ECOBEE_USERNAME in self.config:
                self.username = self.config[ECOBEE_USERNAME]
            if ECOBEE_PASSWORD in self.config:
                self.password = self.config[ECOBEE_PASSWORD]
            if ECOBEE_AUTH0_TOKEN in self.config:
                self.auth0_token = self.config[ECOBEE_AUTH0_TOKEN]
            if ECOBEE_OPTIONS_NOTIFICATIONS in self.config:
                self.include_notifications = convert_to_bool(self.config[ECOBEE_OPTIONS_NOTIFICATIONS])
        else:
            self._file_based_config = True

    def read_config_from_file(self) -> None:
        """Reads config info from passed-in config filename."""
        if self._file_based_config:
            self.config = config_from_file(self.config_filename)
            self.api_key = self.config[ECOBEE_API_KEY]
            if ECOBEE_ACCESS_TOKEN in self.config:
                self.access_token = self.config[ECOBEE_ACCESS_TOKEN]
            if ECOBEE_AUTHORIZATION_CODE in self.config:
                self.authorization_code = self.config[ECOBEE_AUTHORIZATION_CODE]
            if ECOBEE_REFRESH_TOKEN in self.config:
                self.refresh_token = self.config[ECOBEE_REFRESH_TOKEN]
            if ECOBEE_USERNAME in self.config:
                self.username = self.config[ECOBEE_USERNAME]
            if ECOBEE_PASSWORD in self.config:
                self.password = self.config[ECOBEE_PASSWORD]
            if ECOBEE_AUTH0_TOKEN in self.config:
                self.auth0_token = self.config[ECOBEE_AUTH0_TOKEN]
            if ECOBEE_OPTIONS_NOTIFICATIONS in self.config:
                self.include_notifications = convert_to_bool(self.config[ECOBEE_OPTIONS_NOTIFICATIONS])

    def _write_config(self) -> None:
        """Writes API tokens to a file or self.config if self.file_based_config is False."""
        config = dict()
        config[ECOBEE_API_KEY] = self.api_key
        config[ECOBEE_ACCESS_TOKEN] = self.access_token
        config[ECOBEE_REFRESH_TOKEN] = self.refresh_token
        config[ECOBEE_USERNAME] = self.username
        config[ECOBEE_PASSWORD] = self.password
        config[ECOBEE_AUTH0_TOKEN] = self.auth0_token
        config[ECOBEE_AUTHORIZATION_CODE] = self.authorization_code
        config[ECOBEE_OPTIONS_NOTIFICATIONS] = str(self.include_notifications)
        if self._file_based_config:
            config_from_file(self.config_filename, config)
        else:
            self.config = config

    def request_pin(self) -> bool:
        """Requests a PIN from ecobee for authorization on ecobee.com."""
        params = {
            "response_type": "ecobeePin",
            "client_id": self.api_key,
            "scope": "smartWrite",
        }
        log_msg_action = "request pin"

        response = self._request(
            "GET",
            ECOBEE_ENDPOINT_AUTH,
            log_msg_action,
            params=params,
            auth_request=True,
        )

        try:
            self.authorization_code = response["code"]
            self.pin = response["ecobeePin"]
            _LOGGER.debug(
                f"Authorize your ecobee developer app with PIN code {self.pin}. "
                f"Goto https://www.ecobee/com/consumerportal/index.html, "
                f"Click My Apps, Add Application, Enter Pin and click Authorize. "
                f"After authorizing, call request_tokens method."
            )
            return True
        except (KeyError, TypeError) as err:
            _LOGGER.debug(f"Error obtaining PIN code from ecobee: {err}")
            return False

    def request_tokens(self) -> bool:
        """Requests API tokens from ecobee."""
        if self.auth0_token is not None:
            return self.request_tokens_web()
        
        params = {
            "grant_type": "ecobeePin",
            "code": self.authorization_code,
            "client_id": self.api_key,
        }
        log_msg_action = "request tokens"

        response = self._request(
            "POST",
            ECOBEE_ENDPOINT_TOKEN,
            log_msg_action,
            params=params,
            auth_request=True,
        )

        try:
            self.access_token = response["access_token"]
            self.refresh_token = response["refresh_token"]
            self._write_config()
            self.pin = None
            _LOGGER.debug(f"Obtained tokens from ecobee: access {self.access_token}, "
                          f"refresh {self.refresh_token}")
            return True
        except (KeyError, TypeError) as err:
            _LOGGER.debug(f"Error obtaining tokens from ecobee: {err}")
            return False
        
    def request_tokens_web(self) -> bool:
        assert self.auth0_token is not None, "auth0 token must be set before calling request_tokens_web"

        resp = requests.get(ECOBEE_AUTH_BASE_URL + "/" + ECOBEE_ENDPOINT_AUTH, cookies={"auth0": self.auth0_token}, params={
            "client_id": ECOBEE_WEB_CLIENT_ID,
            "scope": "smartWrite",
            "response_type": "token",
            "response_mode": "form_post",
            "redirect_uri": "https://www.ecobee.com/home/authCallback",
            "audience": "https://prod.ecobee.com/api/v1",
        }, timeout=ECOBEE_DEFAULT_TIMEOUT)

        if resp.status_code != 200:
            _LOGGER.error(f"Failed to refresh access token: {resp.status_code} {resp.text}")
            return False
        
        if (auth0 := resp.cookies.get("auth0")) is None:
            _LOGGER.error("Failed to refresh access token: no auth0 cookie in response")
        self.auth0_token = auth0

        # Parse the response HTML for the access token and expiration
        if (access_token := resp.text.split('name="access_token" value="')[1].split('"')[0]) is None:
            _LOGGER.error("Failed to refresh bearer token: no access token in response")
            return False
        
        self.access_token = access_token

        if (expires_in := resp.text.split('name="expires_in" value="')[1].split('"')[0]) is None:
            _LOGGER.error("Failed to refresh bearer token: no expiration in response")
            return False

        expires_at = datetime.datetime.now() + datetime.timedelta(seconds=int(expires_in))
        _LOGGER.debug(f"Access token expires at {expires_at}")

        self._write_config()

        return True

    def refresh_tokens(self) -> bool:
        if self.username and self.password:
            self.request_auth0_token()

        if self.auth0_token is not None:
            return self.request_tokens_web()
        
        """Refreshes ecobee API tokens."""
        params = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.api_key,
        }
        log_msg_action = "refresh tokens"

        response = self._request(
            "POST",
            ECOBEE_ENDPOINT_TOKEN,
            log_msg_action,
            params=params,
            auth_request=True,
        )

        try:
            self.access_token = response["access_token"]
            self.refresh_token = response["refresh_token"]
            self._write_config()
            _LOGGER.debug(f"Refreshed tokens from ecobee: access {self.access_token}, "
                          f"refresh {self.refresh_token}")
            return True
        except (KeyError, TypeError) as err:
            _LOGGER.debug(f"Error refreshing tokens from ecobee: {err}")
            return False

    def request_auth0_token(self) -> bool:
        """Get the auth0 token via username/password."""
        session = requests.Session()
        url = f"{ECOBEE_AUTH_BASE_URL}/{ECOBEE_ENDPOINT_AUTH}"
        resp = session.get(
            url,
            params = {
                "response_type": "token",
                "response_mode": "form_post",
                "client_id": ECOBEE_WEB_CLIENT_ID,
                "redirect_uri": "https://www.ecobee.com/home/authCallback",
                "audience": "https://prod.ecobee.com/api/v1",
                "scope": "openid smartWrite piiWrite piiRead smartRead deleteGrants",
            }
        )
        if resp.status_code != 200:
            _LOGGER.error(f"Failed to obtain auth0 token from {url}: {resp.status_code} {resp.text}")
            return False

        redirect_url = resp.url
        resp = session.post(
            redirect_url,
            data={
                "username": self.username,
                "password": self.password,
                "action": "default"
            }
        )
        if resp.status_code != 200:
            _LOGGER.error(f"Failed to obtain auth0 token from {redirect_url}: {resp.status_code} {resp.text}")
            return False
        if (auth0 := resp.cookies.get("auth0")) is None:
            _LOGGER.error(f"Failed to obtain auth0 token from {redirect_url}: no auth0 cookie in response")
            self.auth0_token = None
            return False

        _LOGGER.debug(f"Obtained auth0 token: {auth0}")
        self.auth0_token = auth0
        return True

    def get_thermostats(self) -> bool:
        """Gets a json-list of thermostats from ecobee and caches in self.thermostats."""
        param_string = {
            "selection": {
                "selectionType": "registered",
                "includeRuntime": "true",
                "includeSensors": "true",
                "includeProgram": "true",
                "includeEquipmentStatus": "true",
                "includeEvents": "true",
                "includeWeather": "true",
                "includeSettings": "true",
                "includeLocation": "true",
            }
        }
        if self.include_notifications:
            param_string["selection"]["includeNotificationSettings"] = self.include_notifications
        params = {"json": json.dumps(param_string)}
        log_msg_action = "get thermostats"

        response = self._request_with_refresh(
            "GET", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, params=params
        )

        try:
            self.thermostats = response["thermostatList"]
            return True
        except (KeyError, TypeError):
            return False

    def get_thermostat(self, index: int) -> str:
        """Returns a single thermostat based on list index of self.thermostats."""
        return self.thermostats[index]

    def get_remote_sensors(self, index: int) -> str:
        """Returns remote sensors from a thermostat based on list index of self.thermostats."""
        return self.thermostats[index]["remoteSensors"]

    def get_equipment_notifications(self, index: int) -> str:
        """Returns equipment notifications from a thermostat based on list index of self.thermostats."""
        return self.thermostats[index]["notificationSettings"]["equipment"]

    def update(self) -> bool:
        """Gets new thermostat data from ecobee; wrapper for get_thermostats."""
        return self.get_thermostats()

    def set_hvac_mode(self, index: int, hvac_mode: str) -> None:
        """Sets the HVAC mode (auto, auxHeatOnly, cool, heat, off)."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"settings": {"hvacMode": hvac_mode}},
        }
        log_msg_action = "set HVAC mode"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_fan_min_on_time(self, index: int, fan_min_on_time: int) -> None:
        """Sets the minimum time, in minutes, to run the fan each hour (1 to 60)."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"settings": {"fanMinOnTime": fan_min_on_time}},
        }
        log_msg_action = "set fan minimum on time"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_fan_mode(
        self,
        index: int,
        fan_mode: str,
        hold_type: str,
        **optional_arg,
    ) -> None:
        """
        Sets the fan mode (auto, minontime, on).
            valid optional_arg
                holdHours - required if HoldType is holdHours
                coolHoldTemp
                heatHoldTemp
        """
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "functions": [
                {
                    "type": "setHold",
                    "params": {
                        "holdType": hold_type,
                        "fan": fan_mode,
                    },
                }
            ],
        }

        # Set the optional args
        if "holdHours" in optional_arg:
            # Required if and only if hold_type == holdHours
            if hold_type == "holdHours":
                body["functions"][0]["params"]["holdHours"] = int(optional_arg["holdHours"])
        if "coolHoldTemp" in optional_arg:
            body["functions"][0]["params"]["coolHoldTemp"] = int(optional_arg["coolHoldTemp"]) * 10
        if "heatHoldTemp" in optional_arg:
            body["functions"][0]["params"]["heatHoldTemp"] = int(optional_arg["heatHoldTemp"]) * 10

        log_msg_action = "set fan mode"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_hold_temp(
        self,
        index: int,
        cool_temp: float,
        heat_temp: float,
        hold_type: str = "nextTransition",
        hold_hours: str = "2",
    ) -> None:
        """Sets a hold temperature."""
        if hold_type == "holdHours":
            body = {
                "selection": {
                    "selectionType": "thermostats",
                    "selectionMatch": self.thermostats[index]["identifier"],
                },
                "functions": [
                    {
                        "type": "setHold",
                        "params": {
                            "holdType": hold_type,
                            "coolHoldTemp": int(cool_temp * 10),
                            "heatHoldTemp": int(heat_temp * 10),
                            "holdHours": hold_hours,
                        },
                    }
                ],
            }
        else:
            body = {
                "selection": {
                    "selectionType": "thermostats",
                    "selectionMatch": self.thermostats[index]["identifier"],
                },
                "functions": [
                    {
                        "type": "setHold",
                        "params": {
                            "holdType": hold_type,
                            "coolHoldTemp": int(cool_temp * 10),
                            "heatHoldTemp": int(heat_temp * 10),
                        },
                    }
                ],
            }
        log_msg_action = "set hold temp"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_climate_hold(
        self, index: int, climate: str, hold_type: str = "nextTransition", hold_hours: int = None
    ) -> None:
        """Sets a climate hold (away, home, sleep)."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "functions": [
                {
                    "type": "setHold",
                    "params": {"holdType": hold_type, "holdClimateRef": climate, "holdHours": hold_hours},
                }
            ],
        }

        if hold_type != "holdHours":
            del body["functions"][0]["params"]["holdHours"]

        log_msg_action = "set climate hold"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def create_vacation(
        self,
        index: int,
        vacation_name: str,
        cool_temp: float,
        heat_temp: float,
        start_date: str = None,
        start_time: str = None,
        end_date: str = None,
        end_time: str = None,
        fan_mode: str = "auto",
        fan_min_on_time: str = "0",
    ) -> None:
        """Creates a vacation."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "functions": [
                {
                    "type": "createVacation",
                    "params": {
                        "name": vacation_name,
                        "coolHoldTemp": int(cool_temp * 10),
                        "heatHoldTemp": int(heat_temp * 10),
                        "startDate": start_date,
                        "startTime": start_time,
                        "endDate": end_date,
                        "endTime": end_time,
                        "fan": fan_mode,
                        "fanMinOnTime": fan_min_on_time,
                    },
                }
            ],
        }
        log_msg_action = "create a vacation"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def delete_vacation(self, index: int, vacation: str) -> None:
        """Deletes a vacation."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "functions": [{"type": "deleteVacation", "params": {"name": vacation}}],
        }
        log_msg_action = "delete a vacation"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def resume_program(self, index: int, resume_all: bool = False) -> None:
        """Resumes the currently scheduled program."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "functions": [
                {"type": "resumeProgram", "params": {"resumeAll": resume_all}}
            ],
        }
        log_msg_action = "resume program"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def send_message(self, index: int, message: str = None) -> None:
        """Sends the first 500 characters of a message to the thermostat."""
        if message is None:
            message = "Hello from pyecobee!"

        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "functions": [{"type": "sendMessage", "params": {"text": message[0:500]}}],
        }
        log_msg_action = "send message"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_dehumidifier_mode(self, index: int, dehumidifier_mode: str) -> None:
        """Sets the dehumidifier mode (on, off)."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"settings": {"dehumidifierMode": dehumidifier_mode}},
        }
        log_msg_action = "set dehumidifier mode"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_dehumidifier_level(self, index: int, dehumidifier_level: int) -> None:
        """Sets the dehumidification set point in percentage."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"settings": {"dehumidifierLevel": dehumidifier_level}}
        }
        log_msg_action = "set dehumidifier level"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_humidifier_mode(self, index: int, humidifier_mode: str) -> None:
        """Sets the humidifier mode (auto, off, manual)."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"settings": {"humidifierMode": humidifier_mode}},
        }
        log_msg_action = "set humidifier mode"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_humidity(self, index: int, humidity: str) -> None:
        """Sets target humidity level."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"settings": {"humidity": str(humidity)}},
        }
        log_msg_action = "set humidity level"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_mic_mode(self, index: int, mic_enabled: bool) -> None:
        """Enables/Disables Alexa microphone (only for ecobee4)."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"audio": {"microphoneEnabled": mic_enabled}},
        }
        log_msg_action = "set mic mode"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_occupancy_modes(
        self, index: int, auto_away: bool = None, follow_me: bool = None
    ) -> None:
        """Enables/Disables Smart Home/Away and Follow Me modes."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {
                "settings": {"autoAway": auto_away, "followMeComfort": follow_me}
            },
        }
        log_msg_action = "set occupancy modes"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_dst_mode(self, index: int, enable_dst: bool) -> None:
        """Enables/Disables daylight savings time."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"location": {"isDaylightSaving": enable_dst}},
        }
        log_msg_action = "set dst mode"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_vent_mode(self, index: int, vent_mode: str) -> None:
        """Sets the ventilator mode. Values: auto, minontime, on, off."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"settings": {"vent": vent_mode}},
        }
        log_msg_action = "set vent mode"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_ventilator_min_on_time(self, index: int, ventilator_min_on_time: int) -> None:
        """Sets the minimum time in minutes the ventilator is configured to run."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"settings": {"ventilatorMinOnTime": ventilator_min_on_time}},
        }
        log_msg_action = "set ventilator minimum on time"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_ventilator_min_on_time_home(self, index: int, ventilator_min_on_time_home: int) -> None:
        """Sets the number of minutes to run ventilator per hour when home."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"settings": {"ventilatorMinOnTimeHome": ventilator_min_on_time_home}},
        }
        log_msg_action = "set ventilator minimum on time when homw"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_ventilator_min_on_time_away(self, index: int, ventilator_min_on_time_away: int) -> None:
        """Sets the number of minutes to run ventilator per hour when away."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"settings": {"ventilatorMinOnTimeAway": ventilator_min_on_time_away}},
        }
        log_msg_action = "set ventilator minimum on time when away"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_ventilator_timer(self, index: int, ventilator_on: bool) -> None:
        """Sets whether the ventilator timer is on or off."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"settings": {"isVentilatorTimerOn": ventilator_on}},
        }
        log_msg_action = "set ventilator timer"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def set_aux_cutover_threshold(self, index: int, threshold: int) -> None:
        """Set the threshold for outdoor temp below which alt heat will be used."""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {"settings": {"compressorProtectionMinTemp": int(threshold * 10)}},
        }
        log_msg_action = "set outdoor temp threshold for aux"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def update_climate_sensors(self, index: int, climate_name: str, sensor_names: Optional[list]=None, sensor_ids: Optional[list]=None) -> None:
        """Get current climate program. Must provide either `sensor_names` or `ids`."""
        # Ensure only either `sensor_names` or `ids` was provided.
        if sensor_names is None and sensor_ids is None:
            raise ValueError("Need to provide either `sensor_names` or `ids`.")
        if sensor_names and sensor_ids:
            raise ValueError("Either `sensor_names` or `ids` should be provided, not both.")

        programs: dict = self.thermostats[index]["program"]
        # Remove currentClimateRef key.
        programs.pop("currentClimateRef", None)

        for i, climate in enumerate(programs["climates"]):
            if climate["name"] == climate_name:
                climate_index = i
        sensors = self.get_remote_sensors(index)
        sensor_list = []

        if sensor_ids:
            """Update climate sensors with sensor_ids list."""
            for id in sensor_ids:
                for sensor in sensors:
                    if sensor["id"] == id:
                        sensor_list.append(
                            {"id": "{}:1".format(id), "name": sensor["name"]})

        if sensor_names:
            """Update climate sensors with sensor_names list."""
            for name in sensor_names:
                """Find the sensor id from the name."""
                for sensor in sensors:
                    if sensor["name"] == name:
                        sensor_list.append(
                            {"id": "{}:1".format(sensor["id"]), "name": name})

        if len(sensor_list) == 0:
            raise InvalidSensorError("no sensor matching provided ids or names on thermostat")

        try:
            programs["climates"][climate_index]["sensors"] = sensor_list
        except UnboundLocalError:
            """This would occur if the climate_index was not assigned
                because the climate name does not exist in the program climates."""
            return

        """Updates Climate"""
        body = {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": self.thermostats[index]["identifier"],
            },
            "thermostat": {
                "program": programs
            }
        }
        log_msg_action = "upate climate sensors"

        try:
            self._request_with_refresh(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, log_msg_action, body=body
            )
        except (ExpiredTokenError, InvalidTokenError) as err:
            raise err

    def _request_with_refresh(
        self,
        method: str,
        endpoint: str,
        log_msg_action: str,
        params: dict = None,
        body: dict = None,
        auth_request: bool = False,
    ) -> Optional[str]:
        """
        Wrapper around _request, to refresh tokens if needed.
        If an ExpiredTokenError is seen call refresh_tokens and
        try one more time. Otherwise, send the results up
        """
        response = None
        refreshed = False
        for _ in range(0, 2):
            try:
                response = self._request(
                    method, endpoint, log_msg_action, params, body, auth_request
                )
            except ExpiredTokenError:
                if not refreshed:
                    # Refresh tokens and try again
                    self.refresh_tokens()
                    refreshed = True
                    continue
                else:
                    # Send the exception up the stack otherwise
                    raise
            except InvalidTokenError:
                raise

            # Success, fall out of the loop
            break

        return response

    def _request(
        self,
        method: str,
        endpoint: str,
        log_msg_action: str,
        params: dict = None,
        body: dict = None,
        auth_request: bool = False,
    ) -> Optional[str]:
        """Makes a request to the ecobee API."""
        url = f"{ECOBEE_BASE_URL}/{endpoint}"
        headers = dict()

        if not auth_request:
            url = f"{ECOBEE_BASE_URL}/{ECOBEE_API_VERSION}/{endpoint}"
            headers = {
                "Content-Type": "application/json;charset=UTF-8",
                "Authorization": f"Bearer {self.access_token}",
            }

        _LOGGER.debug(
            f"Making request to {endpoint} endpoint to {log_msg_action}: "
            f"url: {url}, headers: {headers}, params: {params}, body: {body}"
        )

        try:
            response = requests.request(
                method, url, headers=headers, params=params, json=body, timeout=ECOBEE_DEFAULT_TIMEOUT
            )

            try:
                log_msg = response.json()
            except:
                log_msg = response.text
            _LOGGER.debug(
                f"Request response: {response.status_code}: {log_msg}"
            )

            response.raise_for_status()
            return response.json()
        except HTTPError:
            json_payload = {}
            try:
                json_payload = response.json()
            except json.decoder.JSONDecodeError:
                _LOGGER.debug("Invalid JSON payload received")

            if auth_request:
                if (
                    response.status_code == 400
                    and json_payload.get("error") == "invalid_grant"
                ):
                    raise InvalidTokenError(
                        "ecobee tokens invalid; re-authentication required"
                    )
                else:
                    _LOGGER.error(
                        f"Error requesting authorization from ecobee: "
                        f"{response.status_code}: {json_payload}"
                    )
            elif response.status_code == 500:
                code = json_payload.get("status", {}).get("code")
                if code in [1, 16]:
                    raise InvalidTokenError(
                        "ecobee tokens invalid; re-authentication required"
                    )
                elif code == 14:
                    raise ExpiredTokenError(
                        "ecobee access token expired; token refresh required"
                    )
                else:
                    _LOGGER.error(
                        f"Error from ecobee while attempting to {log_msg_action}: "
                        f"{code}: {json_payload.get('status', {}).get('message', 'Unknown error')}"
                    )
            else:
                _LOGGER.error(
                    f"Error from ecobee while attempting to {log_msg_action}: "
                    f"{response.status_code}: {json_payload}"
                )
        except Timeout:
            _LOGGER.error(
                f"Connection to ecobee timed out while attempting to {log_msg_action}. "
                f"Possible connectivity outage."
            )
        except json.decoder.JSONDecodeError:
            _LOGGER.error(
                f"Error decoding response from ecobee while attempting to {log_msg_action}. "
            )
        except RequestException as err:
            _LOGGER.error(
                f"Error connecting to ecobee while attempting to {log_msg_action}. "
                f"Possible connectivity outage.\n"
                f"{err}"
            )
        return None
