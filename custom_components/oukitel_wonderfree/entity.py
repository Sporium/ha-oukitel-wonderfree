"""Shared entity base for the Oukitel (Wonderfree) integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import WonderfreeCoordinator


class WonderfreeEntity(CoordinatorEntity[WonderfreeCoordinator]):
    """Base entity bound to one station."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WonderfreeCoordinator, key: str) -> None:
        super().__init__(coordinator)
        device = coordinator.device
        self._key = key
        self._attr_unique_id = f"{device.device_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.device_id)},
            name=device.name,
            manufacturer=MANUFACTURER,
            model=device.model,
            serial_number=device.serial,
        )

    @property
    def available(self) -> bool:
        return super().available and self._key in (self.coordinator.data or {})

    @property
    def _value(self):
        return (self.coordinator.data or {}).get(self._key)
