"""Notification-volume control for Shark Vacuum Local."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_NAME, DOMAIN
from .coordinator import SharkCoordinator
from .entity import SharkBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up notification volume."""
    coordinator: SharkCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SharkNotificationVolume(coordinator, entry.data[CONF_NAME])])


class SharkNotificationVolume(SharkBaseEntity, NumberEntity):
    """Represent the vacuum's write-only notification volume."""

    _attr_translation_key = "notification_volume"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:volume-high"

    def __init__(self, coordinator: SharkCoordinator, entry_title: str) -> None:
        super().__init__(coordinator, entry_title)
        self._attr_unique_id = f"{coordinator.unique_id}_notification_volume"
        self._suggest_object_id("notification_volume")

    @property
    def native_value(self) -> float:
        """Return the optimistic volume."""
        return self.coordinator.notification_volume

    async def async_set_native_value(self, value: float) -> None:
        """Set notification volume through captured MQTT field 2."""
        volume = round(value)
        await self.coordinator.mqtt_control.set_setting(2, volume)
        self.coordinator.notification_volume = volume
        self.async_write_ha_state()
