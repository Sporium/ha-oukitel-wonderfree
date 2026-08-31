#!/usr/bin/env python3
"""Log in to the Wonderfree cloud and dump everything the account can see.

Run this once with real credentials to produce the last missing piece — the
station's property codes, which become FIELD_MAP in api.py.

    python3 tools/dump.py --email you@example.com --region eu

The password is read from a prompt (never a shell argument, so it stays out of
your shell history). Responses are written to ./wonderfree-dump/ .

Needs `requests` and `cryptography`.
"""

from __future__ import annotations

import argparse
import getpass
import json
import pathlib
import sys

import importlib.util  # noqa: E402

import requests  # noqa: E402

# Load protocol.py by path: importing the package would pull in Home Assistant.
_PROTOCOL = (
    pathlib.Path(__file__).resolve().parents[1]
    / "custom_components" / "oukitel_wonderfree" / "protocol.py"
)
_spec = importlib.util.spec_from_file_location("wf_protocol", _PROTOCOL)
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)

PATH_DEVICE_LIST = protocol.PATH_DEVICE_LIST
PATH_LOGIN = protocol.PATH_LOGIN
PATH_PROPERTY_DATA = protocol.PATH_PROPERTY_DATA
REGIONS = protocol.REGIONS
build_login_payload = protocol.build_login_payload

OUT = pathlib.Path("wonderfree-dump")


def save(name: str, payload: object) -> None:
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  saved {path}")


def post(base: str, path: str, body: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json", "X-Q-Language": "en-US"}
    if token:
        headers["Authorization"] = token
    response = requests.post(f"{base}{path}", json=body, headers=headers, timeout=30)
    print(f"  HTTP {response.status_code}  {path}")
    try:
        return response.json()
    except ValueError:
        print(f"  non-JSON response: {response.text[:400]}")
        raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--region", default="eu", choices=sorted(REGIONS))
    args = parser.parse_args()

    base = REGIONS[args.region]["api"]
    password = getpass.getpass("Wonderfree password: ")

    print(f"\n[1/3] login -> {base}")
    body = post(base, PATH_LOGIN, build_login_payload(args.email, password, args.region))
    if body.get("code") not in (0, 200):
        print(f"  LOGIN REJECTED: code={body.get('code')} msg={body.get('msg')}")
        save("login-error", body)
        return 1
    data = body.get("data") or {}
    token = data.get("token") or data.get("accessToken")
    print(f"  token: {'yes' if token else 'MISSING'}")
    save("login", {**body, "data": {**data, "token": "<redacted>",
                                    "refreshToken": "<redacted>"}})

    print("\n[2/3] device list")
    devices = post(base, PATH_DEVICE_LIST, {"pageNum": 1, "pageSize": 100}, token)
    save("devices", devices)
    items = devices.get("data")
    if isinstance(items, dict):
        items = items.get("list") or []
    for item in items or []:
        print(f"  - {item.get('deviceName')}  dk={item.get('deviceKey')}  "
              f"pk={item.get('productKey')}  model={item.get('productName')}")

    print("\n[3/3] properties per device")
    for item in items or []:
        dk = item.get("deviceKey") or item.get("dk")
        pk = item.get("productKey") or item.get("pk")
        if not dk:
            continue
        props = post(base, PATH_PROPERTY_DATA, {"dk": dk, "pk": pk}, token)
        save(f"properties-{dk}", props)

    print("\nDone. Send me the files in ./wonderfree-dump/ (tokens are redacted).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
