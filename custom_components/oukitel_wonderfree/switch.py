"""Switches for the Oukitel (Wonderfree) integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import WonderfreeCoordinator
from .entity import WonderfreeEntity

SWITCHES: tuple[SwitchEntityDescription, ...] = (
    SwitchEntityDescription(key="ac_output", translation_key="ac_output",
                            name="AC Output", device_class=SwitchDeviceClass.OUTLET),
    SwitchEntityDescription(key="dc_output", translation_key="dc_output",
                            name="DC Output", device_class=SwitchDeviceClass.OUTLET),
    SwitchEntityDescription(key="usb_output", translation_key="usb_output",
                            name="USB Output", device_class=SwitchDeviceClass.OUTLET),
)

_TRUE = {"true", "1", "on", "yes"}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WonderfreeCoordinator = entry.runtime_data
    async_add_entities(WonderfreeSwitch(coordinator, d) for d in SWITCHES)


class WonderfreeSwitch(WonderfreeEntity, SwitchEntity):
    """A writable output on the station."""

    entity_description: SwitchEntityDescription

    def __init__(
        self, coordinator: WonderfreeCoordinator, description: SwitchEntityDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        value = self._value
        if value is None:
            return None
        return str(value).strip().lower() in _TRUE

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    async def _set(self, on: bool) -> None:
        await self.coordinator.client.async_send_command(
            self.coordinator.device, self.entity_description.key, on
        )
        await self.coordinator.async_request_refresh()
