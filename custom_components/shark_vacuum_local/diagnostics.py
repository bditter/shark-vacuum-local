"""Diagnostics support for Shark Vacuum Local."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .client import fan_speed_debug_info
from .const import CONF_HOST, DOMAIN
from .coordinator import SharkCoordinator


TO_REDACT = {
    CONF_HOST,
    "ip_address",
    "mac_address",
    "ssid",
}


def _json_safe(value: Any) -> Any:
    """Convert schema-free protobuf bytes and integer keys for diagnostics."""
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return redacted transport and raw local-interface diagnostics."""
    coordinator: SharkCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data

    diagnostics: dict[str, Any] = {
        "entry": {
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "transport": fan_speed_debug_info(coordinator.client),
    }
    if data is not None:
        diagnostics["status"] = {
            "mode": data.status.mode.value,
            "battery_level": data.status.battery_level,
            "charging": data.status.charging,
            "raw": _json_safe(data.status.raw),
        }
        diagnostics["device_info_raw"] = (
            _json_safe(data.device_info.raw) if data.device_info else None
        )
        diagnostics["wifi_raw"] = _json_safe(data.wifi.raw) if data.wifi else None

    return async_redact_data(diagnostics, TO_REDACT)
