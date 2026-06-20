"""Vacuum platform for Shark Vacuum Local."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import HomeAssistantError

from sharklocal import SharklocalError
from sharklocal.models import VacuumMode

from .client import fan_speed_debug_info
from .const import CONF_NAME, DOMAIN
from .coordinator import SharkCoordinator
from .entity import SharkBaseEntity

_LOGGER = logging.getLogger(__name__)


# sharklocal.VacuumMode → HA VacuumActivity
MODE_TO_ACTIVITY: dict[VacuumMode, VacuumActivity] = {
    VacuumMode.CLEANING: VacuumActivity.CLEANING,
    VacuumMode.RETURNING_TO_DOCK: VacuumActivity.RETURNING,
    VacuumMode.DOCKING: VacuumActivity.RETURNING,
    VacuumMode.DOCKED: VacuumActivity.DOCKED,
    VacuumMode.IDLE: VacuumActivity.IDLE,
    VacuumMode.EXPLORING: VacuumActivity.CLEANING,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Shark vacuum entity."""
    coordinator: SharkCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SharkVacuum(
                coordinator,
                entry.data[CONF_NAME],
            )
        ]
    )


class SharkVacuum(SharkBaseEntity, StateVacuumEntity):
    """Representation of a Shark IQ vacuum."""

    _attr_name = None  # uses device name
    _attr_supported_features = (
        VacuumEntityFeature.STATE
        | VacuumEntityFeature.START
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.RETURN_HOME
    )

    def __init__(
        self,
        coordinator: SharkCoordinator,
        entry_title: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry_title)
        self._attr_unique_id = f"{coordinator.unique_id}_vacuum"

    @property
    def activity(self) -> VacuumActivity | None:
        """Return the current activity per the VacuumActivity enum."""
        if self.coordinator.data is None:
            return None
        status = self.coordinator.data.status
        return MODE_TO_ACTIVITY.get(status.mode, VacuumActivity.IDLE)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose useful info that doesn't fit the standard properties."""
        if self.coordinator.data is None:
            return {}
        status = self.coordinator.data.status
        attributes = {
            "shark_mode": status.mode.value if status.mode else None,
            "charging": status.charging,
            "battery_level": status.battery_level,
            "vacuum_level": self.coordinator.vacuum_level,
        }
        attributes.update(fan_speed_debug_info(self.coordinator.client))
        return attributes

    async def async_start(self) -> None:
        """Start or resume cleaning with the selected vacuum level."""
        try:
            await self.coordinator.mqtt_control.set_level(
                self.coordinator.vacuum_level
            )
        except HomeAssistantError as err:
            _LOGGER.error(
                "Could not start %s at vacuum level %s: %s",
                self.coordinator.host,
                self.coordinator.vacuum_level,
                err,
            )
            return
        await self.coordinator.async_request_refresh()

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop cleaning."""
        try:
            await self.coordinator.client.stop()
        except SharklocalError as err:
            _LOGGER.error("stop failed for %s: %s", self.coordinator.host, err)
            return
        await self.coordinator.async_request_refresh()

    async def async_pause(self) -> None:
        """Pause — Shark exposes 'stop' which functions as pause."""
        try:
            await self.coordinator.client.stop()
        except SharklocalError as err:
            _LOGGER.error("pause failed for %s: %s", self.coordinator.host, err)
            return
        await self.coordinator.async_request_refresh()

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Return to dock."""
        try:
            await self.coordinator.client.go_home()
        except SharklocalError as err:
            _LOGGER.error("go_home failed for %s: %s", self.coordinator.host, err)
            return
        await self.coordinator.async_request_refresh()
