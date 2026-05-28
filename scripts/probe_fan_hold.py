"""Probe ecobee's setHold-with-fan behavior against the real thermostat.

Phase 1 of the fan-hold investigation. Runs five setHold variants back-to-back,
prints the raw HTTP response from ecobee for each, polls thermostat state ~10s
after each call, and summarizes which variants actually created a hold whose
``fan`` field is honored.

Designed to be safe to re-run: on first run, prompts for username/password/OTP
and writes the refresh_token to ``ECOBEE_CONF`` (default
``./.ecobee.local.conf`` next to this script's repo). On subsequent runs, only
refreshes via the stored token — no MFA prompt.

Usage::

    cd ~/projects/python-ecobee-api
    uv run scripts/probe_fan_hold.py            # uses .ecobee.local.conf
    uv run scripts/probe_fan_hold.py --conf /path/to/ecobee.conf
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

import requests

from pyecobee import (
    Ecobee,
    EcobeeAuthFailedError,
    EcobeeAuthMfaRequiredError,
    EcobeeAuthUnknownError,
)
from pyecobee.const import (
    ECOBEE_API_VERSION,
    ECOBEE_BASE_URL,
    ECOBEE_ENDPOINT_THERMOSTAT,
    ECOBEE_PASSWORD,
    ECOBEE_REFRESH_TOKEN,
    ECOBEE_USERNAME,
)

DEFAULT_CONF = Path(__file__).resolve().parent.parent / ".ecobee.local.conf"
SETTLE_SECONDS = 12  # ecobee runtime polls the thermostat every ~3-5min, but
# events[] in the cloud reflects the API setHold call almost immediately. 12s
# is enough for the cloud to register; the thermostat itself may take longer
# to actually start the fan, which is what we're trying to learn here.


def _redact(token: Optional[str]) -> str:
    if not token:
        return "<missing>"
    return f"{token[:8]}...{token[-4:]} (len={len(token)})"


def _load_conf(conf_path: Path) -> dict:
    if not conf_path.exists():
        return {}
    try:
        return json.loads(conf_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[warn] Could not read {conf_path}: {exc}", file=sys.stderr)
        return {}


def _save_conf(conf_path: Path, ecobee: Ecobee) -> None:
    payload = {
        ECOBEE_USERNAME: ecobee.username,
        ECOBEE_PASSWORD: ecobee.password,
        ECOBEE_REFRESH_TOKEN: ecobee.refresh_token,
    }
    conf_path.write_text(json.dumps(payload))
    os.chmod(conf_path, 0o600)


def _login_or_refresh(conf_path: Path) -> Ecobee:
    """Return an authenticated Ecobee. Reuses refresh_token if conf_path exists."""
    saved = _load_conf(conf_path)
    if saved.get(ECOBEE_REFRESH_TOKEN):
        print(f"[info] Reusing refresh_token from {conf_path}")
        ecobee = Ecobee(config=dict(saved))
        try:
            ecobee.refresh_tokens()
        except (EcobeeAuthFailedError, EcobeeAuthUnknownError) as exc:
            print(f"[warn] Refresh failed ({exc}); falling back to fresh login.")
        else:
            print(f"  access_token:  {_redact(ecobee.access_token)}")
            print(f"  refresh_token: {_redact(ecobee.refresh_token)}")
            _save_conf(conf_path, ecobee)
            return ecobee

    print("[info] No usable refresh_token; doing interactive login.")
    username = saved.get(ECOBEE_USERNAME) or input("ecobee username/email: ").strip()
    password = saved.get(ECOBEE_PASSWORD) or getpass.getpass("ecobee password: ")
    ecobee = Ecobee(config={ECOBEE_USERNAME: username, ECOBEE_PASSWORD: password})
    try:
        ecobee.request_tokens_web()
    except EcobeeAuthMfaRequiredError as exc:
        challenge = exc.args[0]
        otp = input("Enter the 6-digit OTP from your authenticator app: ").strip()
        ecobee.submit_mfa_code(challenge, otp)

    print(f"  access_token:  {_redact(ecobee.access_token)}")
    print(f"  refresh_token: {_redact(ecobee.refresh_token)}")
    _save_conf(conf_path, ecobee)
    return ecobee


def _post_setHold_raw(
    ecobee: Ecobee, identifier: str, params: dict, label: str
) -> dict:
    """Issue a raw setHold POST and return ecobee's full parsed response body.

    Bypasses ``Ecobee._request_with_refresh`` so we can see the response shape
    (which the library currently discards on non-2xx). Refreshes the token on
    HTTP 401/500-code-14 just like the library would.
    """
    url = f"{ECOBEE_BASE_URL}/{ECOBEE_API_VERSION}/{ECOBEE_ENDPOINT_THERMOSTAT}"
    body = {
        "selection": {"selectionType": "thermostats", "selectionMatch": identifier},
        "functions": [{"type": "setHold", "params": params}],
    }
    for attempt in (1, 2):
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Authorization": f"Bearer {ecobee.access_token}",
        }
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        try:
            parsed = resp.json()
        except ValueError:
            parsed = {"_raw_text": resp.text}
        if resp.status_code == 500 and parsed.get("status", {}).get("code") == 14:
            print(f"  [auth] access_token expired during '{label}', refreshing & retrying")
            ecobee.refresh_tokens()
            continue
        return {"http_status": resp.status_code, "body": parsed, "request_body": body}
    return {"http_status": resp.status_code, "body": parsed, "request_body": body}


def _summarize_state(ecobee: Ecobee, index: int) -> dict:
    """Pull the current cloud-side state we care about into a compact dict."""
    t = ecobee.thermostats[index]
    runtime = t.get("runtime", {}) or {}
    settings = t.get("settings", {}) or {}
    events = t.get("events", []) or []
    program = t.get("program", {}) or {}
    return {
        "currentClimateRef": program.get("currentClimateRef"),
        "actualFanRunRate": runtime.get("actualFanRunRate"),
        "fanMinOnTime": settings.get("fanMinOnTime"),
        "desiredCool": runtime.get("desiredCool"),
        "desiredHeat": runtime.get("desiredHeat"),
        "desiredFanMode": runtime.get("desiredFanMode"),
        "actualTemperature": runtime.get("actualTemperature"),
        "equipmentStatus": t.get("equipmentStatus"),
        "events": [
            {
                "type": ev.get("type"),
                "fan": ev.get("fan"),
                "holdClimateRef": ev.get("holdClimateRef"),
                "running": ev.get("running"),
                "startDate": ev.get("startDate"),
                "startTime": ev.get("startTime"),
                "endDate": ev.get("endDate"),
                "endTime": ev.get("endTime"),
                "coolHoldTemp": ev.get("coolHoldTemp"),
                "heatHoldTemp": ev.get("heatHoldTemp"),
                "isOptional": ev.get("isOptional"),
                "name": ev.get("name"),
            }
            for ev in events
        ],
    }


def _dump_state(state: dict) -> None:
    print(json.dumps(state, indent=2, default=str))


def _hold_event_after_call(state: dict) -> Optional[dict]:
    """Return the most recent running 'hold' event, if any."""
    for ev in state.get("events", []):
        if ev.get("type") == "hold" and ev.get("running"):
            return ev
    return None


def _resume_baseline(ecobee: Ecobee, index: int) -> None:
    print("\n[reset] resumeProgram(resume_all=True)")
    ecobee.resume_program(index, resume_all=True)
    time.sleep(3)
    ecobee.update()


def _run_variant(
    ecobee: Ecobee,
    index: int,
    label: str,
    do_call,
    raw_post: Optional[dict] = None,
) -> dict:
    """Run one variant: clean state, call, wait, read, summarize.

    Returns a row for the final table.
    """
    print(f"\n{'='*72}\nVARIANT: {label}\n{'='*72}")
    _resume_baseline(ecobee, index)
    identifier = ecobee.thermostats[index]["identifier"]

    if raw_post is not None:
        resp = _post_setHold_raw(ecobee, identifier, raw_post, label)
        print(f"[req]  POST setHold params: {json.dumps(raw_post)}")
        print(f"[resp] HTTP {resp['http_status']} body: {json.dumps(resp['body'])}")
    else:
        try:
            do_call()
            print(f"[call] {label} returned without raising")
        except Exception as exc:
            print(f"[call] {label} RAISED: {exc!r}")

    print(f"[wait] sleeping {SETTLE_SECONDS}s for ecobee cloud to register…")
    time.sleep(SETTLE_SECONDS)
    ecobee.update()
    state = _summarize_state(ecobee, index)
    _dump_state(state)

    hold = _hold_event_after_call(state)
    return {
        "variant": label,
        "hold_created": hold is not None,
        "hold_fan": (hold or {}).get("fan"),
        "actualFanRunRate": state.get("actualFanRunRate"),
        "desiredFanMode": state.get("desiredFanMode"),
        "fanMinOnTime": state.get("fanMinOnTime"),
        "event_endTime": f"{(hold or {}).get('endDate','-')} {(hold or {}).get('endTime','-')}",
        "event_coolHold": (hold or {}).get("coolHoldTemp"),
        "event_heatHold": (hold or {}).get("heatHoldTemp"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf", type=Path, default=DEFAULT_CONF)
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument(
        "--skip",
        nargs="*",
        default=[],
        help="Variant labels to skip (a, b, c, d, e)",
    )
    args = parser.parse_args()

    ecobee = _login_or_refresh(args.conf)

    print("\n[info] Fetching thermostat list…")
    if not ecobee.update():
        print("[fail] get_thermostats returned False; check refresh_token / network.")
        return 2

    index = args.index
    t = ecobee.thermostats[index]
    print(f"[info] Thermostat: name={t.get('name')!r} id={t.get('identifier')!r}")

    baseline = _summarize_state(ecobee, index)
    print("\n[baseline] state BEFORE any probe call:")
    _dump_state(baseline)

    # Capture current cool/heat setpoints so variant (c) / (e) can reuse them.
    cool_setpoint_tenths = baseline["desiredCool"]
    heat_setpoint_tenths = baseline["desiredHeat"]
    if cool_setpoint_tenths is None or heat_setpoint_tenths is None:
        print("[fail] runtime.desiredCool/desiredHeat missing; can't continue.")
        return 3
    cool_f = cool_setpoint_tenths / 10.0
    heat_f = heat_setpoint_tenths / 10.0
    print(f"[info] Using current setpoints: cool={cool_f}F heat={heat_f}F")

    rows: list[dict] = []

    if "a" not in args.skip:
        rows.append(
            _run_variant(
                ecobee,
                index,
                "a) set_fan_mode(on, nextTransition) — what HA does today",
                lambda: ecobee.set_fan_mode(index, "on", "nextTransition"),
            )
        )

    if "b" not in args.skip:
        rows.append(
            _run_variant(
                ecobee,
                index,
                "b) set_fan_mode(on, holdHours, holdHours=2)",
                lambda: ecobee.set_fan_mode(
                    index, "on", "holdHours", holdHours=2
                ),
            )
        )

    if "c" not in args.skip:
        rows.append(
            _run_variant(
                ecobee,
                index,
                "c) set_fan_mode(on, holdHours=2, coolHoldTemp=cur, heatHoldTemp=cur)",
                lambda: ecobee.set_fan_mode(
                    index,
                    "on",
                    "holdHours",
                    holdHours=2,
                    coolHoldTemp=cool_f,
                    heatHoldTemp=heat_f,
                ),
            )
        )

    if "d" not in args.skip:
        rows.append(
            _run_variant(
                ecobee,
                index,
                "d) set_fan_mode(on, indefinite)",
                lambda: ecobee.set_fan_mode(index, "on", "indefinite"),
            )
        )

    if "e" not in args.skip:
        # Raw setHold matching the ecobee developer-portal example shape.
        rows.append(
            _run_variant(
                ecobee,
                index,
                "e) raw setHold w/ holdHours+coolHoldTemp+heatHoldTemp+fan=on (full devportal shape)",
                lambda: None,
                raw_post={
                    "holdType": "holdHours",
                    "holdHours": 2,
                    "fan": "on",
                    "coolHoldTemp": int(cool_setpoint_tenths),
                    "heatHoldTemp": int(heat_setpoint_tenths),
                    "isTemperatureAbsolute": True,
                    "isTemperatureRelative": False,
                },
            )
        )

    print("\n[reset] final resumeProgram to leave thermostat in baseline state")
    ecobee.resume_program(index, resume_all=True)

    # --------------------------------------------------------------------- table
    print("\n" + "=" * 96)
    print("SUMMARY TABLE")
    print("=" * 96)
    header = (
        f"{'variant':<70} {'hold?':<6} {'event.fan':<10} "
        f"{'desFan':<8} {'fanMin':<7} {'fanRate':<8}"
    )
    print(header)
    print("-" * 96)
    for row in rows:
        print(
            f"{row['variant'][:70]:<70} "
            f"{'YES' if row['hold_created'] else 'no':<6} "
            f"{str(row['hold_fan']):<10} "
            f"{str(row['desiredFanMode']):<8} "
            f"{str(row['fanMinOnTime']):<7} "
            f"{str(row['actualFanRunRate']):<8}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
