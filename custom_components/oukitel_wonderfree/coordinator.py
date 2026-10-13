"""Polling coordinator for the Wonderfree cloud."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WonderfreeAuthError, WonderfreeClient, WonderfreeDevice, WonderfreeError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class WonderfreeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Keeps one station's telemetry fresh.

    A poll that fails or comes back empty keeps the previous values instead of
    blanking every entity: the datastorage endpoint already returns the last
    stored row for a sleeping station, so this is a transient hiccup. Real
    outages surface through the sensors' staleness check on Last Report.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: WonderfreeClient,
        device: WonderfreeDevice,
        scan_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:{device.device_id}",
            update_interval=scan_interval,
            config_entry=entry,
        )
        self.client = client
        self.device = device

    async def _async_update_data(self) -> dict[str, Any]:
        # The station only uploads around a command, so nudge it every poll;
        # what it reports now is picked up by this read or the next one.
        try:
            await self.client.async_request_report(self.device)
        except WonderfreeAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except WonderfreeError as err:
            _LOGGER.debug("report request failed: %s", err)
        try:
            data = await self.client.async_get_status(self.device)
        except WonderfreeAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except WonderfreeError as err:
            # One failed read (e.g. the station's Wi-Fi blinking when it
            # switches between grid and battery) should not blank every
            # entity; sensors still go unavailable once the data gets stale.
            if self.data:
                _LOGGER.debug("status read failed, keeping last data: %s", err)
                return self.data
            raise UpdateFailed(str(err)) from err
        if not data and self.data:
            return self.data
        return data
