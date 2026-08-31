"""The Oukitel (Wonderfree) integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    WonderfreeAuthError,
    WonderfreeClient,
    WonderfreeDevice,
    WonderfreeError,
)
from .const import CONF_DEVICE_ID, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .coordinator import WonderfreeCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

type WonderfreeConfigEntry = ConfigEntry[WonderfreeCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: WonderfreeConfigEntry
) -> bool:
    """Set up one station from a config entry."""
    client = WonderfreeClient(
        async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    try:
        await client.async_login()
        devices = await client.async_get_devices()
    except WonderfreeAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except WonderfreeError as err:
        raise ConfigEntryNotReady(str(err)) from err

    device_id = entry.data[CONF_DEVICE_ID]
    device = next((d for d in devices if d.device_id == device_id), None)
    if device is None:
        # Keep the entry loaded with what we know rather than failing outright:
        # a shared device can drop off the list while the share is re-issued.
        device = WonderfreeDevice(device_id=device_id, name=entry.title)

    seconds = entry.options.get(CONF_SCAN_INTERVAL)
    interval = timedelta(seconds=seconds) if seconds else DEFAULT_SCAN_INTERVAL

    coordinator = WonderfreeCoordinator(hass, entry, client, device, interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: WonderfreeConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(
    hass: HomeAssistant, entry: WonderfreeConfigEntry
) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
