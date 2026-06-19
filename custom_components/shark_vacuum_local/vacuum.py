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

from .client import LocalFanSpeedClient, fan_speed_debug_info
from .const import (
    CONF_FAN_SPEED_PATH,
    CONF_NAME,
    DEFAULT_FAN_SPEED_PATH,
    DOMAIN,
    FAN_SPEED_VALUES,
)
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
                LocalFanSpeedClient(
                    hass,
                    coordinator.client,
                    coordinator.host,
                    entry.options.get(
                        CONF_FAN_SPEED_PATH, DEFAULT_FAN_SPEED_PATH
                    ),
                ),
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
        | VacuumEntityFeature.FAN_SPEED
    )
    _attr_fan_speed_list = list(FAN_SPEED_VALUES)

    def __init__(
        self,
        coordinator: SharkCoordinator,
        entry_title: str,
        fan_client: LocalFanSpeedClient,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry_title)
        self._attr_unique_id = f"{coordinator.unique_id}_vacuum"
        self._fan_client = fan_client
        # The local status response does not expose Power_Mode. Retain the last
        # successfully commanded value so HA can give useful optimistic state.
        self._attr_fan_speed = None

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
        }
        attributes.update(fan_speed_debug_info(self.coordinator.client))
        return attributes

    async def async_set_fan_speed(
        self, fan_speed: str, **kwargs: Any
    ) -> None:
        """Set the local Power_Mode value; the vacuum cannot report it back."""
        try:
            await self._fan_client.set_speed(fan_speed)
        except HomeAssistantError:
            _LOGGER.exception(
                "Setting fan speed %s failed for %s",
                fan_speed,
                self.coordinator.host,
            )
            raise
        self._attr_fan_speed = fan_speed
        self.async_write_ha_state()

    async def async_start(self) -> None:
        """Start cleaning."""
        try:
            await self.coordinator.client.start_cleaning()
        except SharklocalError as err:
            _LOGGER.error("start_cleaning failed for %s: %s", self.coordinator.host, err)
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
