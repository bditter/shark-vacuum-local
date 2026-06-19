"""Client construction and experimental local vacuum-level control."""
from __future__ import annotations

from typing import Any

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from sharklocal import VacuumClient

from .const import VACUUM_LEVEL_VALUES


def create_vacuum_client(host: str, mapping: str, use_mqtt: bool) -> VacuumClient:
    """Create a client using the Reference integration's transport contract."""
    return VacuumClient(
        host=host,
        rest_mappings=mapping,
        mqtt_mappings=mapping if use_mqtt else None,
    )


class LocalVacuumLevelClient:
    """Send the undocumented Power_Mode value to a configurable local route."""

    def __init__(
        self,
        hass: HomeAssistant,
        vacuum: VacuumClient,
        host: str,
        path_template: str,
    ) -> None:
        self._session = async_get_clientsession(hass, verify_ssl=False)
        self._vacuum = vacuum
        self._host = host
        self._path_template = path_template

    async def set_level(self, level: str) -> None:
        """Set Eco, Normal, or Max using the configured local REST path."""
        if level not in VACUUM_LEVEL_VALUES:
            raise HomeAssistantError(f"Unsupported vacuum level: {level}")

        try:
            path = self._path_template.format(
                value=VACUUM_LEVEL_VALUES[level], speed=level.lower()
            )
        except (KeyError, ValueError) as err:
            raise HomeAssistantError(
                "Vacuum level path may only use {value} and {speed} placeholders"
            ) from err
        if not path.startswith("/") or path.startswith("//"):
            raise HomeAssistantError("Vacuum level path must begin with one slash")

        mapping = self._vacuum.active_rest_mapping
        if mapping == "sharkiq_v2":
            base_url = f"http://{self._host}:8080"
        elif mapping == "sharkiq_v1":
            base_url = f"https://{self._host}:443"
        else:
            raise HomeAssistantError(
                "Vacuum level requires a reachable local REST interface"
            )

        try:
            async with self._session.get(f"{base_url}{path}") as response:
                body = await response.text()
                if response.status >= 400:
                    raise HomeAssistantError(
                        f"Vacuum level command returned HTTP {response.status} "
                        f"from {path}: {body[:200]}"
                    )
        except ClientError as err:
            raise HomeAssistantError(
                f"Could not send vacuum level to {self._host}: {err}"
            ) from err


def fan_speed_debug_info(client: VacuumClient) -> dict[str, Any]:
    """Return non-sensitive transport details for diagnostics and logs."""
    return {
        "active_rest_mapping": client.active_rest_mapping,
        "active_mqtt_mapping": client.active_mqtt_mapping,
        "supported_actions": client.supported_actions(),
    }
