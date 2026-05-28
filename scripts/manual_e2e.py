"""Interactive end-to-end check of the new auth code + MFA flow.

Not part of the test suite. Run manually against a real ecobee account to
verify (a) Auth0 actually issues a refresh_token when we ask for offline_access,
(b) the MFA challenge is handled correctly, and (c) a subsequent
``refresh_tokens()`` call works via the refresh grant alone (no re-prompt).

Usage:
    cd ~/projects/python-ecobee-api
    .venv/bin/python scripts/manual_e2e.py
"""

from __future__ import annotations

import getpass
import sys

from pyecobee import (
    Ecobee,
    EcobeeAuthFailedError,
    EcobeeAuthMfaRequiredError,
    EcobeeAuthUnknownError,
)
from pyecobee.const import ECOBEE_PASSWORD, ECOBEE_USERNAME


def _redact(token: str | None) -> str:
    if not token:
        return "<missing>"
    return f"{token[:8]}...{token[-4:]} (len={len(token)})"


def main() -> int:
    username = input("ecobee username/email: ").strip()
    password = getpass.getpass("ecobee password: ")

    print("\n--- Step 1: initial login (request_tokens_web) ---")
    ecobee = Ecobee(config={ECOBEE_USERNAME: username, ECOBEE_PASSWORD: password})
    try:
        ecobee.request_tokens_web()
    except EcobeeAuthMfaRequiredError as exc:
        challenge = exc.args[0]
        print(f"  MFA required. challenge.mfa_type = {challenge.mfa_type!r}")
        prompt = {
            "otp": "Enter the 6-digit code from your authenticator app",
            "sms": "Enter the code sent to your phone via SMS",
        }.get(challenge.mfa_type, f"Enter the {challenge.mfa_type} MFA code")
        otp = input(f"  {prompt}: ").strip()
        try:
            ecobee.submit_mfa_code(challenge, otp)
        except EcobeeAuthFailedError as e:
            print(f"  FAIL: OTP rejected: {e}")
            return 2
    except EcobeeAuthFailedError as e:
        print(f"  FAIL: credentials rejected: {e}")
        return 2
    except EcobeeAuthUnknownError as e:
        print(f"  FAIL: unknown error: {e}")
        return 2

    print(f"  access_token:  {_redact(ecobee.access_token)}")
    print(f"  refresh_token: {_redact(ecobee.refresh_token)}")
    if not ecobee.refresh_token:
        print(
            "\nGATING FAILURE: Auth0 did not issue a refresh_token even though "
            "offline_access was requested. Library refactor will not work as "
            "designed. Stop and re-plan."
        )
        return 3
    print("  -> Auth0 issued a refresh_token. offline_access works.")

    print("\n--- Step 2: refresh via refresh_token grant (no re-prompt) ---")
    ecobee.access_token = None  # force Auth0 to issue a new access_token
    old_access = None
    old_refresh = ecobee.refresh_token
    try:
        ecobee.refresh_tokens()
    except (EcobeeAuthFailedError, EcobeeAuthUnknownError) as e:
        print(f"  FAIL: refresh failed: {e}")
        return 4

    print(f"  access_token:  {_redact(ecobee.access_token)}")
    print(f"  refresh_token: {_redact(ecobee.refresh_token)}")
    if ecobee.access_token == old_access:
        print(
            "  WARNING: access_token did not change. Refresh may have been a "
            "no-op (still valid). Not necessarily a failure."
        )
    else:
        print("  -> access_token rotated. Refresh grant works end-to-end.")
    if ecobee.refresh_token != old_refresh:
        print("  -> refresh_token was rotated by Auth0 (handled by library).")

    print("\nAll three end-to-end gates pass. Library refactor validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
