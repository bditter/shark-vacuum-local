"""Optimistic preference switches for Shark Vacuum Local."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_NAME,
    DOMAIN,
    SETTING_EVACUATE_RESUME,
    SETTING_RECHARGE_RESUME,
    SETTING_SAVE_POWER_LEVEL,
)
from .coordinator import SharkCoordinator
from .entity import SharkBaseEntity


@dataclass(frozen=True)
class SharkSwitchDescription:
    """Describe one captured preference switch."""

    key: str
    field: int
    values: dict[bool, int]


SWITCHES = (
    SharkSwitchDescription("recharge_and_resume", *SETTING_RECHARGE_RESUME),
    SharkSwitchDescription("evacuate_and_resume", *SETTING_EVACUATE_RESUME),
    SharkSwitchDescription("save_power_level", *SETTING_SAVE_POWER_LEVEL),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up locally captured preference switches."""
    coordinator: SharkCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SharkPreferenceSwitch(coordinator, entry.data[CONF_NAME], description)
        for description in SWITCHES
    )


class SharkPreferenceSwitch(SharkBaseEntity, SwitchEntity):
    """Represent a write-only local Shark preference."""

    def __init__(
        self,
        coordinator: SharkCoordinator,
        entry_title: str,
        description: SharkSwitchDescription,
    ) -> None:
        super().__init__(coordinator, entry_title)
        self._description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{coordinator.unique_id}_{description.key}"
        self._suggest_object_id(description.key)

    @property
    def is_on(self) -> bool:
        """Return the optimistic setting."""
        return self.coordinator.settings[self._description.key]

    async def _set(self, enabled: bool) -> None:
        await self.coordinator.mqtt_control.set_setting(
            self._description.field, self._description.values[enabled]
        )
        self.coordinator.settings[self._description.key] = enabled
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable the preference."""
        await self._set(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable the preference."""
        await self._set(False)
