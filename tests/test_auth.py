"""Tests for the ecobee Auth0 web login flow (auth code + PKCE + MFA).

Each test uses ``requests_mock`` to stand in for Auth0. The shapes mocked here
match what was captured against the live ecobee Auth0 tenant in
``NOTES_auth_flow.md`` (see the repo root, not committed).
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

import pytest
import requests_mock as rm_module

from pyecobee import (
    Ecobee,
    MfaChallenge,
    _generate_pkce_pair,
)
from pyecobee.const import (
    ECOBEE_PASSWORD,
    ECOBEE_USERNAME,
    ECOBEE_WEB_CLIENT_ID,
)
from pyecobee.errors import (
    EcobeeAuthFailedError,
    EcobeeAuthMfaRequiredError,
    EcobeeAuthUnknownError,
)


AUTH_BASE = "https://auth.ecobee.com"
TOKEN_URL = f"{AUTH_BASE}/oauth/token"
CALLBACK_URL = "https://www.ecobee.com/home/authCallback"


def _make_ecobee() -> Ecobee:
    """Build an Ecobee instance with username/password set, no tokens."""
    return Ecobee(
        config={
            ECOBEE_USERNAME: "user@example.com",
            ECOBEE_PASSWORD: "hunter2",
        }
    )


def _register_initial_get(m: rm_module.Mocker, state: str = "STATE_1") -> None:
    """Wire up the GET /authorize → 302 → /u/login/identifier hop.

    Mimics Auth0 by setting the ``auth0`` session cookie on the landed page
    (the library refuses to continue without it). requests_mock's ``cookies=``
    populates the session cookie jar through ``extract_cookies_to_jar``.
    """
    m.get(
        f"{AUTH_BASE}/authorize",
        status_code=302,
        headers={"Location": f"{AUTH_BASE}/u/login/identifier?state={state}"},
    )
    m.get(
        f"{AUTH_BASE}/u/login/identifier",
        status_code=200,
        text="<html>identifier form</html>",
        cookies={"auth0": "sess-cookie"},
    )


def _register_identifier_post(
    m: rm_module.Mocker, state: str = "STATE_1"
) -> None:
    """Wire up POST /u/login/identifier → 302 → /u/login/password."""
    m.post(
        f"{AUTH_BASE}/u/login/identifier",
        status_code=302,
        headers={"Location": f"{AUTH_BASE}/u/login/password?state={state}"},
    )
    m.get(
        f"{AUTH_BASE}/u/login/password",
        status_code=200,
        text="<html>password form</html>",
    )


def test_pkce_pair_shape() -> None:
    """PKCE verifier length must be within RFC 7636 bounds; challenge derives from it."""
    import base64
    import hashlib

    verifier, challenge = _generate_pkce_pair()
    assert 43 <= len(verifier) <= 128
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    assert challenge == expected


def test_request_tokens_web_uses_auth_code_flow_params(
    requests_mock: rm_module.Mocker,
) -> None:
    """The initial /authorize call must request code flow + PKCE + offline_access."""
    _register_initial_get(requests_mock)
    _register_identifier_post(requests_mock)
    # Password POST lands at the callback with an auth code (no MFA path).
    requests_mock.post(
        f"{AUTH_BASE}/u/login/password",
        status_code=302,
        headers={"Location": f"{CALLBACK_URL}?code=AUTH_CODE_XYZ"},
    )
    requests_mock.post(
        TOKEN_URL,
        status_code=200,
        json={
            "access_token": "AT-1",
            "refresh_token": "RT-1",
            "expires_in": 3600,
            "token_type": "Bearer",
        },
    )

    ecobee = _make_ecobee()
    assert ecobee.request_tokens_web() is True
    assert ecobee.access_token == "AT-1"
    assert ecobee.refresh_token == "RT-1"

    # Inspect the first call (the /authorize GET) for required OAuth2 params.
    authorize_call = requests_mock.request_history[0]
    qs = parse_qs(urlparse(authorize_call.url).query)
    assert qs["response_type"] == ["code"]
    assert qs["client_id"] == [ECOBEE_WEB_CLIENT_ID]
    assert "offline_access" in qs["scope"][0]
    assert qs["code_challenge_method"] == ["S256"]
    assert qs["code_challenge"][0]  # non-empty challenge present


def test_request_tokens_web_exchanges_code_with_verifier(
    requests_mock: rm_module.Mocker,
) -> None:
    """The /oauth/token POST must include the original PKCE verifier and the code."""
    _register_initial_get(requests_mock)
    _register_identifier_post(requests_mock)
    requests_mock.post(
        f"{AUTH_BASE}/u/login/password",
        status_code=302,
        headers={"Location": f"{CALLBACK_URL}?code=AUTHCODE_42"},
    )
    requests_mock.post(
        TOKEN_URL,
        status_code=200,
        json={
            "access_token": "AT-token",
            "refresh_token": "RT-token",
            "expires_in": 3600,
        },
    )

    ecobee = _make_ecobee()
    ecobee.request_tokens_web()

    token_call = next(
        c for c in requests_mock.request_history if c.url == TOKEN_URL
    )
    body = parse_qs(token_call.text)
    assert body["grant_type"] == ["authorization_code"]
    assert body["code"] == ["AUTHCODE_42"]
    assert body["client_id"] == [ECOBEE_WEB_CLIENT_ID]
    assert body["code_verifier"][0]  # the PKCE verifier round-trips


def test_request_tokens_web_wrong_password_raises_failed(
    requests_mock: rm_module.Mocker,
) -> None:
    """When Auth0 rejects the password it re-renders the password page; map to AuthFailed."""
    _register_initial_get(requests_mock)
    _register_identifier_post(requests_mock)
    # Auth0 behavior on bad password: redirect back to /u/login/password.
    requests_mock.post(
        f"{AUTH_BASE}/u/login/password",
        status_code=302,
        headers={"Location": f"{AUTH_BASE}/u/login/password?state=STATE_1&error=1"},
    )

    ecobee = _make_ecobee()
    with pytest.raises(EcobeeAuthFailedError):
        ecobee.request_tokens_web()


def test_request_tokens_web_mfa_required_raises_with_challenge(
    requests_mock: rm_module.Mocker,
) -> None:
    """MFA-enabled accounts get a typed exception carrying the resumption state."""
    _register_initial_get(requests_mock)
    _register_identifier_post(requests_mock)
    # Auth0 with MFA: password POST 302s into the OTP challenge.
    requests_mock.post(
        f"{AUTH_BASE}/u/login/password",
        status_code=302,
        headers={
            "Location": f"{AUTH_BASE}/u/mfa-otp-challenge?state=MFA_STATE_9"
        },
    )
    requests_mock.get(
        f"{AUTH_BASE}/u/mfa-otp-challenge",
        status_code=200,
        text="<html>OTP form</html>",
    )

    ecobee = _make_ecobee()
    with pytest.raises(EcobeeAuthMfaRequiredError) as exc_info:
        ecobee.request_tokens_web()
    challenge = exc_info.value.args[0]
    assert isinstance(challenge, MfaChallenge)
    assert challenge.mfa_type == "otp"
    assert challenge.state == "MFA_STATE_9"
    assert "mfa-otp-challenge" in challenge.challenge_url
    assert challenge.code_verifier  # PKCE verifier preserved for resumption


def test_request_tokens_web_unsupported_mfa_type_raises_unknown(
    requests_mock: rm_module.Mocker,
) -> None:
    """SMS/push/email challenge URLs aren't supported in v1; surface clearly."""
    _register_initial_get(requests_mock)
    _register_identifier_post(requests_mock)
    requests_mock.post(
        f"{AUTH_BASE}/u/login/password",
        status_code=302,
        headers={
            "Location": f"{AUTH_BASE}/u/mfa-sms-challenge?state=SMS_STATE"
        },
    )
    requests_mock.get(
        f"{AUTH_BASE}/u/mfa-sms-challenge",
        status_code=200,
        text="<html>SMS form</html>",
    )

    ecobee = _make_ecobee()
    with pytest.raises(EcobeeAuthUnknownError, match="not yet supported"):
        ecobee.request_tokens_web()


def test_request_tokens_web_unexpected_initial_landing_raises_unknown(
    requests_mock: rm_module.Mocker,
) -> None:
    """If /authorize redirects somewhere other than /u/login/identifier, fail clearly."""
    requests_mock.get(
        f"{AUTH_BASE}/authorize",
        status_code=302,
        headers={"Location": f"{AUTH_BASE}/some/other/path"},
    )
    requests_mock.get(
        f"{AUTH_BASE}/some/other/path",
        status_code=200,
        text="<html></html>",
    )

    ecobee = _make_ecobee()
    with pytest.raises(EcobeeAuthUnknownError, match="did not redirect"):
        ecobee.request_tokens_web()


def test_token_exchange_missing_refresh_token_raises_unknown(
    requests_mock: rm_module.Mocker,
) -> None:
    """If Auth0 issues an access_token but no refresh_token, fail fast."""
    _register_initial_get(requests_mock)
    _register_identifier_post(requests_mock)
    requests_mock.post(
        f"{AUTH_BASE}/u/login/password",
        status_code=302,
        headers={"Location": f"{CALLBACK_URL}?code=CODE_X"},
    )
    requests_mock.post(
        TOKEN_URL,
        status_code=200,
        json={"access_token": "AT-1", "expires_in": 3600},  # no refresh_token
    )

    ecobee = _make_ecobee()
    with pytest.raises(EcobeeAuthUnknownError, match="refresh_token"):
        ecobee.request_tokens_web()


def test_submit_mfa_code_success(requests_mock: rm_module.Mocker) -> None:
    """Submitting a valid OTP completes the login and stores both tokens."""
    challenge_url = f"{AUTH_BASE}/u/mfa-otp-challenge?state=MFA_STATE"
    # OTP POST: 302 to the callback with an auth code.
    requests_mock.post(
        challenge_url,
        status_code=302,
        headers={"Location": f"{CALLBACK_URL}?code=POST_MFA_CODE"},
    )
    requests_mock.post(
        TOKEN_URL,
        status_code=200,
        json={
            "access_token": "AT-mfa",
            "refresh_token": "RT-mfa",
            "expires_in": 3600,
        },
    )

    challenge = MfaChallenge(
        challenge_url=challenge_url,
        state="MFA_STATE",
        mfa_type="otp",
        cookies={"auth0": "sess"},
        code_verifier="VERIFIER_VALUE",
    )
    ecobee = _make_ecobee()
    assert ecobee.submit_mfa_code(challenge, "123456") is True
    assert ecobee.access_token == "AT-mfa"
    assert ecobee.refresh_token == "RT-mfa"

    # Confirm the OTP POST sent state + code, and the token exchange reused
    # the stored verifier (not a fresh one).
    otp_call = next(
        c
        for c in requests_mock.request_history
        if "mfa-otp-challenge" in c.url and c.method == "POST"
    )
    body = parse_qs(otp_call.text)
    assert body["state"] == ["MFA_STATE"]
    assert body["code"] == ["123456"]

    token_call = next(c for c in requests_mock.request_history if c.url == TOKEN_URL)
    token_body = parse_qs(token_call.text)
    assert token_body["code_verifier"] == ["VERIFIER_VALUE"]


def test_submit_mfa_code_wrong_code_raises_failed(
    requests_mock: rm_module.Mocker,
) -> None:
    """Auth0 re-renders the challenge page on a bad OTP; map to AuthFailed."""
    challenge_url = f"{AUTH_BASE}/u/mfa-otp-challenge?state=MFA_STATE"
    requests_mock.post(
        challenge_url,
        status_code=302,
        headers={
            "Location": f"{AUTH_BASE}/u/mfa-otp-challenge?state=MFA_STATE&error=1"
        },
    )
    requests_mock.get(
        f"{AUTH_BASE}/u/mfa-otp-challenge",
        status_code=200,
        text="<html>retry</html>",
    )

    challenge = MfaChallenge(
        challenge_url=challenge_url,
        state="MFA_STATE",
        mfa_type="otp",
        code_verifier="V",
    )
    ecobee = _make_ecobee()
    with pytest.raises(EcobeeAuthFailedError, match="not accepted"):
        ecobee.submit_mfa_code(challenge, "000000")


def test_refresh_tokens_prefers_refresh_grant_when_token_present(
    requests_mock: rm_module.Mocker,
) -> None:
    """With a refresh_token set, refresh_tokens must not re-do the web login."""
    requests_mock.post(
        TOKEN_URL,
        status_code=200,
        json={"access_token": "AT-2", "refresh_token": "RT-2", "expires_in": 3600},
    )

    ecobee = _make_ecobee()
    ecobee.refresh_token = "RT-1"  # pretend we have one from a prior login
    assert ecobee.refresh_tokens() is True
    assert ecobee.access_token == "AT-2"
    assert ecobee.refresh_token == "RT-2"

    # Only one HTTP call: the refresh grant POST. No /authorize GET, no
    # /u/login/* hops.
    assert len(requests_mock.request_history) == 1
    only_call = requests_mock.request_history[0]
    assert only_call.url == TOKEN_URL
    body = parse_qs(only_call.text)
    assert body["grant_type"] == ["refresh_token"]
    assert body["refresh_token"] == ["RT-1"]


def test_refresh_tokens_keeps_old_refresh_token_when_not_rotated(
    requests_mock: rm_module.Mocker,
) -> None:
    """Auth0 may omit refresh_token from the refresh response (no rotation)."""
    requests_mock.post(
        TOKEN_URL,
        status_code=200,
        json={"access_token": "AT-new", "expires_in": 3600},  # no refresh_token
    )

    ecobee = _make_ecobee()
    ecobee.refresh_token = "RT-original"
    assert ecobee.refresh_tokens() is True
    assert ecobee.access_token == "AT-new"
    assert ecobee.refresh_token == "RT-original"


def test_refresh_tokens_no_credentials_raises(
    requests_mock: rm_module.Mocker,
) -> None:
    """An Ecobee with no refresh_token, no credentials, no api_key has nothing to do."""
    ecobee = Ecobee(config={})
    with pytest.raises(EcobeeAuthUnknownError, match="No refresh_token"):
        ecobee.refresh_tokens()


def test_refresh_tokens_falls_back_to_web_login_for_legacy_entries(
    requests_mock: rm_module.Mocker,
) -> None:
    """A legacy entry with username+password but no refresh_token re-logs in.

    This is the migration path: the first refresh after upgrading does a fresh
    web login (which now uses auth code flow and obtains a refresh_token).
    """
    _register_initial_get(requests_mock)
    _register_identifier_post(requests_mock)
    requests_mock.post(
        f"{AUTH_BASE}/u/login/password",
        status_code=302,
        headers={"Location": f"{CALLBACK_URL}?code=MIGRATION_CODE"},
    )
    requests_mock.post(
        TOKEN_URL,
        status_code=200,
        json={"access_token": "AT-m", "refresh_token": "RT-m", "expires_in": 3600},
    )

    ecobee = _make_ecobee()  # no refresh_token
    assert ecobee.refresh_tokens() is True
    assert ecobee.refresh_token == "RT-m"
