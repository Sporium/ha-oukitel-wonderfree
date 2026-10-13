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

# Sensors go unavailable when the station's newest report is older than this.
# While it is reachable it reports every ~30 s, so 10 min means it is gone.
STALE_AFTER: Final = timedelta(minutes=10)

MANUFACTURER: Final = "Oukitel"
