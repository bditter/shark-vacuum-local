"""Client construction and confirmed local MQTT controls."""
from __future__ import annotations

import base64
from typing import Any

import aiomqtt

from homeassistant.exceptions import HomeAssistantError

from sharklocal import VacuumClient

from .const import MQTT_COMMAND_TOPIC, VACUUM_LEVEL_VALUES


def create_vacuum_client(host: str, mapping: str, use_mqtt: bool) -> VacuumClient:
    """Create a client using the Reference integration's transport contract."""
    return VacuumClient(
        host=host,
        rest_mappings=mapping,
        mqtt_mappings=mapping if use_mqtt else None,
    )


def _varint(value: int) -> bytes:
    """Encode a non-negative protobuf varint."""
    encoded = bytearray()
    while value > 0x7F:
        encoded.append((value & 0x7F) | 0x80)
        value >>= 7
    encoded.append(value)
    return bytes(encoded)


def setting_payload(field: int, value: int) -> str:
    """Build the captured field-7 settings command envelope."""
    nested = _varint(field << 3) + _varint(value)
    raw = b"\x3a" + _varint(len(nested)) + nested
    return base64.b64encode(raw).decode()


def vacuum_level_payload(level: str) -> str:
    """Build the captured start/level command."""
    if level not in VACUUM_LEVEL_VALUES:
        raise HomeAssistantError(f"Unsupported vacuum level: {level}")
    nested = b"\x0a\x02\x10" + _varint(VACUUM_LEVEL_VALUES[level])
    raw = b"\x3a" + _varint(len(nested)) + nested + b"\x80\x01\x09"
    return base64.b64encode(raw).decode()


class LocalMqttControlClient:
    """Publish commands directly to the vacuum's unauthenticated MQTT broker."""

    def __init__(self, host: str) -> None:
        self._host = host

    async def publish(self, payload: str) -> None:
        """Publish one base64-wrapped protobuf command."""
        try:
            async with aiomqtt.Client(self._host, port=1883) as client:
                await client.publish(MQTT_COMMAND_TOPIC, payload=payload)
        except Exception as err:
            raise HomeAssistantError(
                f"Could not send local MQTT command to {self._host}: {err}"
            ) from err

    async def set_level(self, level: str) -> None:
        """Start or resume cleaning at Eco, Normal, or Max."""
        await self.publish(vacuum_level_payload(level))

    async def set_setting(self, field: int, value: int) -> None:
        """Set a captured local preference field."""
        await self.publish(setting_payload(field, value))


def fan_speed_debug_info(client: VacuumClient) -> dict[str, Any]:
    """Return non-sensitive transport details for diagnostics and logs."""
    return {
        "active_rest_mapping": client.active_rest_mapping,
        "active_mqtt_mapping": client.active_mqtt_mapping,
        "supported_actions": client.supported_actions(),
    }
