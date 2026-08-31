"""Sensors for the Oukitel (Wonderfree) integration.

The set is exactly what the P2001E Plus exposes in its TSL, so the Lovelace
cards, Grafana panels and helpers that fed off the old EcoFlow can be repointed
onto these entities. Cloud values arrive as strings and are coerced to float.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import WonderfreeCoordinator
from .entity import WonderfreeEntity


@dataclass(frozen=True, kw_only=True)
class WonderfreeSensorDescription(SensorEntityDescription):
    """Describes one sensor."""


def _power(key: str, name: str) -> WonderfreeSensorDescription:
    return WonderfreeSensorDescription(
        key=key, translation_key=key, name=name,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )


SENSORS: tuple[WonderfreeSensorDescription, ...] = (
    WonderfreeSensorDescription(
        key="soc", translation_key="soc", name="Battery Level",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    _power("power_in_total", "Total In Power"),
    _power("power_out_total", "Total Out Power"),
    _power("ac_in_power", "AC In Power"),
    _power("dc_in_power", "DC In Power"),
    WonderfreeSensorDescription(
        key="device_temp", translation_key="device_temp", name="Device Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WonderfreeSensorDescription(
        key="discharge_remain_min", translation_key="discharge_remain_min",
        name="Discharge Remaining Time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
    ),
    WonderfreeSensorDescription(
        key="charge_remain_min", translation_key="charge_remain_min",
        name="Charge Remaining Time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
    ),
    WonderfreeSensorDescription(
        key="ac_charge_limit", translation_key="ac_charge_limit",
        name="AC Charging Limit",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WonderfreeCoordinator = entry.runtime_data
    async_add_entities(WonderfreeSensor(coordinator, d) for d in SENSORS)


class WonderfreeSensor(WonderfreeEntity, SensorEntity):
    """One reading from the station."""

    entity_description: WonderfreeSensorDescription

    def __init__(
        self, coordinator: WonderfreeCoordinator, description: WonderfreeSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        value = self._value
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
