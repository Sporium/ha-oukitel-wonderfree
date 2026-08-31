"""Client for the Wonderfree (Quectel) cloud.

The station has no local interface (a full port scan of a responsive unit came
back empty; no discovery broadcasts; BLE stops advertising on Wi-Fi), so this
talks to the Quectel cloud the Wonderfree app uses. The whole protocol was
reconstructed from the app and verified against the live EU endpoint:

* login is form-encoded, password AES-encrypted (see `protocol.py`);
* authenticated calls need the app's header set (Authorization + X-Q-Language +
  quec-random-url + app-info) — without the latter two the gateway answers
  "please enter token";
* live values come from the datastorage history endpoint: one GET per property
  code, newest row first, so `list[0].propertyValue` is the current value. The
  history store also means a sleeping station still returns its last value.

FIELD_MAP is filled from the device's TSL (thing model); values arrive as
strings and are coerced per entity.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from aiohttp import ClientError, ClientSession

from .protocol import (
    DEFAULT_REGION,
    PATH_DEVICE_LIST,
    PATH_LOGIN,
    PATH_PROPERTY_DATA,
    REGIONS,
    build_login_payload,
)

_LOGGER = logging.getLogger(__name__)

# Canonical key -> the station's TSL property code (Oukitel P2001E Plus).
FIELD_MAP: dict[str, str] = {
    "soc": "battery_percentage",
    "power_in_total": "total_input_power",
    "power_out_total": "total_output_power",
    "ac_in_power": "ac_input",
    "dc_in_power": "dc_input",
    "device_temp": "temp",
    "discharge_remain_min": "remain_time",
    "charge_remain_min": "remain_charging_time",
    "ac_charge_limit": "ac_charging_limit",
}

# Canonical switch key -> TSL code (BOOL, value "true"/"false").
SWITCH_MAP: dict[str, str] = {
    "ac_output": "ac_switch",
    "usb_output": "usb_switch",
    "dc_output": "dc_switch",
}


# App header set that authenticated calls require.
_APP_INFO = "[24090RA29G][Xiaomi][malachite][34]"


class WonderfreeError(Exception):
    """Base error for the Wonderfree cloud."""


class WonderfreeAuthError(WonderfreeError):
    """Credentials were rejected or the session is gone."""


@dataclass
class WonderfreeDevice:
    """A station as the cloud describes it."""

    device_id: str
    name: str
    model: str | None = None
    serial: str | None = None
    product_key: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class WonderfreeClient:
    """Async client for the Wonderfree cloud."""

    def __init__(
        self,
        session: ClientSession,
        username: str,
        password: str,
        region: str = DEFAULT_REGION,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._region = region
        self._base = REGIONS[region]["api"]
        self._token: str | None = None

    def _headers(self, auth: bool = True) -> dict[str, str]:
        headers = {
            "X-Q-Language": "en-US",
            "quec-random-url": str(uuid.uuid4()),
            "app-info": _APP_INFO,
        }
        if auth and self._token:
            headers["Authorization"] = self._token
        return headers

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            async with self._session.get(
                f"{self._base}{path}", params=params, headers=self._headers()
            ) as response:
                response.raise_for_status()
                body = await response.json(content_type=None)
        except ClientError as err:
            raise WonderfreeError(f"{path} failed: {err}") from err
        code = body.get("code")
        if code in (5032, 5106):
            raise WonderfreeAuthError(f"{path}: code {code} — session expired")
        if code not in (0, 200):
            raise WonderfreeError(f"{path}: code {code} — {body.get('msg')}")
        return body

    async def async_login(self) -> None:
        """Authenticate and remember the access token."""
        payload = build_login_payload(self._username, self._password, self._region)
        try:
            async with self._session.post(
                f"{self._base}{PATH_LOGIN}", data=payload, headers=self._headers(auth=False)
            ) as response:
                body = await response.json(content_type=None)
        except ClientError as err:
            raise WonderfreeError(f"login failed: {err}") from err
        if body.get("code") not in (0, 200):
            raise WonderfreeAuthError(
                f"login rejected: {body.get('msg')} ({body.get('code')})"
            )
        access = (body.get("data") or {}).get("accessToken") or {}
        self._token = access.get("token")
        if not self._token:
            raise WonderfreeAuthError(f"no token in the login response: {body}")

    async def async_get_devices(self) -> list[WonderfreeDevice]:
        """List the stations owned by or shared with this account."""
        devices: dict[str, WonderfreeDevice] = {}
        for assoc in ("false", "true"):
            body = await self._get(
                PATH_DEVICE_LIST,
                {"page": 1, "pageSize": 100, "isAssociation": assoc},
            )
            data = body.get("data")
            items = data.get("list") if isinstance(data, dict) else data
            for item in items or []:
                if not isinstance(item, dict):
                    continue
                dk = item.get("deviceKey") or item.get("dk")
                if not dk:
                    continue
                devices[dk] = WonderfreeDevice(
                    device_id=dk,
                    name=str(item.get("deviceName") or "Oukitel"),
                    model=item.get("productName"),
                    serial=item.get("sn"),
                    product_key=item.get("productKey") or item.get("pk"),
                    raw=item,
                )
        return list(devices.values())

    async def _latest(self, device: WonderfreeDevice, code: str) -> Any:
        """Newest stored value for one property code, or None."""
        now = int(time.time() * 1000)
        body = await self._get(
            PATH_PROPERTY_DATA,
            {
                "pk": device.product_key,
                "dk": device.device_id,
                "attributeCode": code,
                "page": 1,
                "pageSize": 1,
                # 30-day window: switch states change rarely and are stored only
                # on change, so a short window can miss the last known state.
                "startTimestamp": now - 30 * 86_400_000,
                "endTimestamp": now,
            },
        )
        data = body.get("data") or {}
        rows = data.get("list") if isinstance(data, dict) else data
        return rows[0].get("propertyValue") if rows else None

    async def async_get_status(self, device: WonderfreeDevice) -> dict[str, Any]:
        """Fetch the mapped properties as canonical keys (raw string values).

        Only codes that return a value are included, so an entity whose source
        is absent reads as unavailable rather than as a wrong zero.
        """
        status: dict[str, Any] = {}
        for index, (key, code) in enumerate({**FIELD_MAP, **SWITCH_MAP}.items()):
            if index:
                # The cloud rate-limits a long burst of reads and drops the
                # tail, so space the per-code queries out.
                await asyncio.sleep(0.25)
            value = await self._latest_retry(device, key, code)
            if value is not None:
                status[key] = value
        return status

    async def _latest_retry(self, device, key: str, code: str) -> Any:
        """One property read with a single backoff retry on rate-limit."""
        for attempt in (1, 2):
            try:
                return await self._latest(device, code)
            except WonderfreeError as err:
                if attempt == 1:
                    await asyncio.sleep(0.6)
                    continue
                _LOGGER.debug("reading %s (%s) failed: %s", key, code, err)
                return None

    async def async_send_command(
        self, device: WonderfreeDevice, key: str, value: Any
    ) -> None:
        """Write one property to the station via batchControlDevice.

        Verified against the live cloud: the body is
        ``{"data": "[{\"<id>\": <value>}]", "deviceList": [{pk, dk}], "type": 2}``
        where the key is the property CODE (e.g. "ac_switch") and booleans are JSON
        true/false.
        """
        code = SWITCH_MAP.get(key) or FIELD_MAP.get(key)
        if code is None:
            raise WonderfreeError(f"no property code mapped for {key!r}")
        payload = {
            "data": json.dumps([{code: value}]),
            "deviceList": [
                {"productKey": device.product_key, "deviceKey": device.device_id}
            ],
            "type": 2,
        }
        try:
            async with self._session.post(
                f"{self._base}/v2/binding/enduserapi/batchControlDevice",
                json=payload,
                headers=self._headers(),
            ) as response:
                response.raise_for_status()
                body = await response.json(content_type=None)
        except ClientError as err:
            raise WonderfreeError(f"control failed: {err}") from err
        if body.get("code") not in (0, 200):
            raise WonderfreeError(
                f"control rejected: {body.get('msg')} ({body.get('code')})"
            )
