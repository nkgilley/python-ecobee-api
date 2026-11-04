"""Tests for the humidity alert and equipment reminder setters."""

import copy

import pytest
import requests_mock as rm_module

from pyecobee import Ecobee
from pyecobee.const import (
    ECOBEE_ACCESS_TOKEN,
    ECOBEE_API_VERSION,
    ECOBEE_BASE_URL,
    ECOBEE_ENDPOINT_THERMOSTAT,
)

URL = f"{ECOBEE_BASE_URL}/{ECOBEE_API_VERSION}/{ECOBEE_ENDPOINT_THERMOSTAT}"


@pytest.fixture
def ecobee(requests_mock: rm_module.Mocker) -> Ecobee:
    """Return an Ecobee with one cached thermostat."""
    requests_mock.post(URL, json={"status": {"code": 0}})
    client = Ecobee(config={ECOBEE_ACCESS_TOKEN: "test-token"})
    client.thermostats = [
        {
            "identifier": "1234",
            "notificationSettings": {
                "equipment": [
                    {
                        "filterLastChanged": "2014-01-03",
                        "filterLife": 3,
                        "filterLifeUnits": "month",
                        "remindMeDate": "2014-04-03",
                        "enabled": False,
                        "type": "humidifierFilter",
                        "remindTechnician": False,
                    },
                    {
                        "filterLastChanged": "2014-01-03",
                        "filterLife": 12,
                        "filterLifeUnits": "month",
                        "remindMeDate": "2015-01-03",
                        "enabled": True,
                        "type": "uvLamp",
                        "remindTechnician": False,
                    },
                ]
            },
        }
    ]
    return client


@pytest.mark.parametrize(
    "method, value, key",
    [
        ("set_humidity_high_alert", 60, "humidityHighAlert"),
        ("set_humidity_low_alert", -1, "humidityLowAlert"),
        ("set_humidity_alert_notify", True, "humidityAlertNotify"),
        ("set_humidity_alert_notify_technician", False, "humidityAlertNotifyTechnician"),
    ],
)
def test_humidity_alert_setters(
    ecobee: Ecobee,
    requests_mock: rm_module.Mocker,
    method: str,
    value: object,
    key: str,
) -> None:
    """Each setter posts its one setting to the selected thermostat."""
    getattr(ecobee, method)(0, value)

    assert requests_mock.last_request.json() == {
        "selection": {"selectionType": "thermostats", "selectionMatch": "1234"},
        "thermostat": {"settings": {key: value}},
    }


def test_equipment_notification_changes_only_that_type(
    ecobee: Ecobee, requests_mock: rm_module.Mocker
) -> None:
    """Other types are sent unchanged and remindMeDate is never sent."""
    ecobee.set_equipment_notification(
        0, "humidifierFilter", filter_last_changed="2026-11-03", enabled=True
    )

    assert requests_mock.last_request.json()["thermostat"] == {
        "notificationSettings": {
            "equipment": [
                {
                    "filterLastChanged": "2026-11-03",
                    "filterLife": 3,
                    "filterLifeUnits": "month",
                    "enabled": True,
                    "type": "humidifierFilter",
                    "remindTechnician": False,
                },
                {
                    "filterLastChanged": "2014-01-03",
                    "filterLife": 12,
                    "filterLifeUnits": "month",
                    "enabled": True,
                    "type": "uvLamp",
                    "remindTechnician": False,
                },
            ]
        }
    }


def test_equipment_notification_keeps_false_values(
    ecobee: Ecobee, requests_mock: rm_module.Mocker
) -> None:
    """A False value is a change, not a missing argument."""
    ecobee.thermostats[0]["notificationSettings"]["equipment"][0]["enabled"] = True

    ecobee.set_equipment_notification(0, "humidifierFilter", enabled=False)

    equipment = requests_mock.last_request.json()["thermostat"]["notificationSettings"][
        "equipment"
    ]
    assert equipment[0]["enabled"] is False


def test_equipment_notification_does_not_change_the_cache(ecobee: Ecobee) -> None:
    """The cached thermostat data stays as the API last reported it."""
    before = copy.deepcopy(ecobee.thermostats)

    ecobee.set_equipment_notification(0, "humidifierFilter", filter_life=6)

    assert ecobee.thermostats == before


def test_equipment_notification_unknown_type(
    ecobee: Ecobee, requests_mock: rm_module.Mocker
) -> None:
    """An unknown type raises without posting anything."""
    with pytest.raises(ValueError):
        ecobee.set_equipment_notification(0, "notAType", enabled=True)

    assert requests_mock.call_count == 0
