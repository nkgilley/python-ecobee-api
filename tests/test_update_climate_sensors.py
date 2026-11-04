"""Tests that update_climate_sensors keeps currentClimateRef in the cached data."""

from collections.abc import Iterator
from typing import Optional

import pytest
import requests
import requests_mock as rm_module

from pyecobee import Ecobee
from pyecobee.const import (
    ECOBEE_ACCESS_TOKEN,
    ECOBEE_API_VERSION,
    ECOBEE_BASE_URL,
    ECOBEE_ENDPOINT_THERMOSTAT,
)
from pyecobee.errors import InvalidSensorError, InvalidTokenError

URL = f"{ECOBEE_BASE_URL}/{ECOBEE_API_VERSION}/{ECOBEE_ENDPOINT_THERMOSTAT}"
LIVING_ROOM = {"id": "rs:100:1", "name": "Living Room"}
BEDROOM = {"id": "rs:101:1", "name": "Bedroom"}


def thermostat() -> dict:
    """Return a new copy of the thermostat as ecobee reports it."""
    return {
        "identifier": "123456789012",
        "program": {
            "schedule": [["home", "sleep"]],
            "climates": [
                {"name": "Home", "climateRef": "home", "sensors": [dict(LIVING_ROOM)]},
                {"name": "Sleep", "climateRef": "sleep", "sensors": [dict(LIVING_ROOM)]},
            ],
            "currentClimateRef": "home",
        },
        "remoteSensors": [
            {"id": "rs:100", "name": "Living Room"},
            {"id": "rs:101", "name": "Bedroom"},
        ],
    }


@pytest.fixture
def ecobee() -> Iterator[Ecobee]:
    """Return an Ecobee instance with one cached thermostat."""
    instance = Ecobee(config={ECOBEE_ACCESS_TOKEN: "test-token"})
    instance.thermostats = [thermostat()]
    yield instance
    instance._session.close()


def test_successful_call_keeps_current_climate_ref(
    ecobee: Ecobee, requests_mock: rm_module.Mocker
) -> None:
    """A successful POST leaves currentClimateRef in the cache."""
    requests_mock.post(URL, json={"status": {"code": 0}})

    ecobee.update_climate_sensors(0, "Home", sensor_names=["Bedroom"])

    assert requests_mock.call_count == 1
    assert ecobee.thermostats[0]["program"]["currentClimateRef"] == "home"


def test_calls_before_a_refresh_build_on_each_other(
    ecobee: Ecobee, requests_mock: rm_module.Mocker
) -> None:
    """A second call before a refresh still carries the first call's sensors."""
    requests_mock.post(URL, json={"status": {"code": 0}})

    ecobee.update_climate_sensors(0, "Home", sensor_names=["Bedroom"])
    ecobee.update_climate_sensors(0, "Sleep", sensor_names=["Bedroom"])

    climates = requests_mock.last_request.json()["thermostat"]["program"]["climates"]
    assert [climate["sensors"] for climate in climates] == [[BEDROOM], [BEDROOM]]


@pytest.mark.parametrize(
    "response, expected_error",
    [
        ({"status_code": 500, "json": {"status": {"code": 3}}}, None),
        ({"status_code": 503, "text": "unavailable"}, None),
        ({"exc": requests.exceptions.ConnectTimeout}, None),
        ({"exc": requests.exceptions.ConnectionError}, None),
        ({"status_code": 500, "json": {"status": {"code": 16}}}, InvalidTokenError),
    ],
    ids=["api-error", "http-error", "timeout", "connection-error", "invalid-token"],
)
def test_failed_post_keeps_current_climate_ref(
    ecobee: Ecobee,
    requests_mock: rm_module.Mocker,
    response: dict,
    expected_error: Optional[type[Exception]],
) -> None:
    """A failed POST leaves currentClimateRef in the cache."""
    requests_mock.post(URL, **response)

    if expected_error is None:
        ecobee.update_climate_sensors(0, "Home", sensor_names=["Bedroom"])
    else:
        with pytest.raises(expected_error):
            ecobee.update_climate_sensors(0, "Home", sensor_names=["Bedroom"])

    assert requests_mock.call_count == 1
    assert ecobee.thermostats[0]["program"]["currentClimateRef"] == "home"


@pytest.mark.parametrize(
    "kwargs",
    [{"sensor_names": ["Bedroom"]}, {"sensor_ids": ["rs:101"]}],
    ids=["sensor_names", "sensor_ids"],
)
def test_post_body_omits_current_climate_ref(
    ecobee: Ecobee, requests_mock: rm_module.Mocker, kwargs: dict
) -> None:
    """The POST body is the program with the new sensors and no currentClimateRef."""
    requests_mock.post(URL, json={"status": {"code": 0}})

    ecobee.update_climate_sensors(0, "Home", **kwargs)

    body = requests_mock.last_request.json()
    assert "currentClimateRef" not in body["thermostat"]["program"]
    assert body == {
        "selection": {
            "selectionType": "thermostats",
            "selectionMatch": "123456789012",
        },
        "thermostat": {
            "program": {
                "schedule": [["home", "sleep"]],
                "climates": [
                    {"name": "Home", "climateRef": "home", "sensors": [BEDROOM]},
                    {"name": "Sleep", "climateRef": "sleep", "sensors": [LIVING_ROOM]},
                ],
            }
        },
    }


def test_unknown_climate_keeps_cache(
    ecobee: Ecobee, requests_mock: rm_module.Mocker
) -> None:
    """An unknown climate name sends nothing and leaves the cache alone."""
    ecobee.update_climate_sensors(0, "Vacation", sensor_names=["Bedroom"])

    assert requests_mock.call_count == 0
    assert ecobee.thermostats == [thermostat()]


def test_unknown_sensor_keeps_cache(
    ecobee: Ecobee, requests_mock: rm_module.Mocker
) -> None:
    """An unknown sensor raises, sends nothing and leaves the cache alone."""
    with pytest.raises(InvalidSensorError):
        ecobee.update_climate_sensors(0, "Home", sensor_names=["Garage"])

    assert requests_mock.call_count == 0
    assert ecobee.thermostats == [thermostat()]
