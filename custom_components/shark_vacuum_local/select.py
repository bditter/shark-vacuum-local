"""Select platform for Shark Vacuum Local."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_NAME, DOMAIN, VACUUM_LEVEL_VALUES
from .coordinator import SharkCoordinator
from .entity import SharkBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the optimistic vacuum-level selector."""
    coordinator: SharkCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SharkVacuumLevelSelect(coordinator, entry.data[CONF_NAME])])


class SharkVacuumLevelSelect(SharkBaseEntity, SelectEntity):
    """Store the level that will be applied before the next cleaning run."""

    _attr_translation_key = "vacuum_level"
    _attr_options = list(VACUUM_LEVEL_VALUES)

    def __init__(self, coordinator: SharkCoordinator, entry_title: str) -> None:
        """Initialize the selector."""
        super().__init__(coordinator, entry_title)
        self._attr_unique_id = f"{coordinator.unique_id}_vacuum_level"
        self._suggest_object_id("vacuum_level")

    @property
    def current_option(self) -> str:
        """Return the optimistic vacuum level."""
        return self.coordinator.vacuum_level

    async def async_select_option(self, option: str) -> None:
        """Store the level and apply it immediately while cleaning."""
        if option not in VACUUM_LEVEL_VALUES:
            raise ValueError(f"Unsupported vacuum level: {option}")
        previous = self.coordinator.vacuum_level
        self.coordinator.vacuum_level = option
        self.async_write_ha_state()
        mode = self.coordinator.data.status.mode if self.coordinator.data else None
        if mode and mode.value == "cleaning":
            try:
                await self.coordinator.mqtt_control.set_level(option)
            except HomeAssistantError:
                self.coordinator.vacuum_level = previous
                self.async_write_ha_state()
                raise
