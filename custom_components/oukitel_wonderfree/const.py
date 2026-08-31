"""Constants for the Oukitel (Wonderfree) integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "oukitel_wonderfree"

CONF_DEVICE_ID: Final = "device_id"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=30)
MIN_SCAN_INTERVAL: Final = 10
MAX_SCAN_INTERVAL: Final = 600

MANUFACTURER: Final = "Oukitel"
