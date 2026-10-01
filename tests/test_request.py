"""Tests for the session used by ecobee API requests."""

import pytest
import requests
import requests_mock as rm_module

from pyecobee import Ecobee
from pyecobee.const import (
    ECOBEE_ACCESS_TOKEN,
    ECOBEE_API_VERSION,
    ECOBEE_BASE_URL,
    ECOBEE_DEFAULT_TIMEOUT,
    ECOBEE_ENDPOINT_THERMOSTAT,
)


@pytest.mark.parametrize(
    "args, kwargs",
    [
        ((), {}),
        (("ecobee.conf",), {}),
        ((None, {}), {}),
        ((), {"config_filename": "ecobee.conf"}),
        ((), {"config": {}}),
        ((), {"config": {}, "session": None}),
    ],
)
def test_default_session_is_per_instance(args: tuple, kwargs: dict) -> None:
    """Existing constructor forms each get their own session, even without config."""
    first = Ecobee(*args, **kwargs)
    second = Ecobee(*args, **kwargs)
    try:
        assert isinstance(first._session, requests.Session)
        assert first._session is not second._session
    finally:
        first._session.close()
        second._session.close()


def test_request_reuses_injected_session(requests_mock: rm_module.Mocker) -> None:
    """Repeated API calls use the injected session and preserve request arguments."""
    url = f"{ECOBEE_BASE_URL}/{ECOBEE_API_VERSION}/{ECOBEE_ENDPOINT_THERMOSTAT}"
    payload = {"status": {"code": 0}}
    requests_mock.post(url, json=payload)
    params = {"format": "json"}
    body = {"selection": {"selectionType": "registered"}}

    with requests.Session() as session:
        session.headers["X-Test-Session"] = "injected"
        ecobee = Ecobee(config={ECOBEE_ACCESS_TOKEN: "test-token"}, session=session)
        for _ in range(2):
            assert ecobee._request(
                "POST", ECOBEE_ENDPOINT_THERMOSTAT, "test request", params, body
            ) == payload

        assert ecobee._session is session

    assert requests_mock.call_count == 2
    for request in requests_mock.request_history:
        assert request.headers["X-Test-Session"] == "injected"
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.headers["Content-Type"] == "application/json;charset=UTF-8"
        assert request.qs == {"format": ["json"]}
        assert request.json() == body
        assert request.timeout == ECOBEE_DEFAULT_TIMEOUT
