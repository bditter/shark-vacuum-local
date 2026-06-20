"""The Shark Vacuum Local integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import area_registry as ar, device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from sharklocal import SharklocalError

from .client import create_vacuum_client

from .const import (
    CONF_HOST,
    CONF_MAPPING,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_USE_MQTT,
    DEFAULT_MAPPING,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_MQTT,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SharkCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Shark Vacuum Local from a config entry."""
    host: str = entry.data[CONF_HOST]
    mapping: str = entry.data.get(CONF_MAPPING, DEFAULT_MAPPING)
    use_mqtt: bool = entry.data.get(CONF_USE_MQTT, DEFAULT_USE_MQTT)
    # scan_interval lives in options (editable post-setup), not data.
    scan_interval: int = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    client = create_vacuum_client(host, mapping, use_mqtt)

    # VacuumClient supports async-context-manager use; we manage it manually
    # because we want it to live for the lifetime of the config entry.
    try:
        await client.__aenter__()
    except SharklocalError as err:
        raise ConfigEntryNotReady(f"Could not connect to {host}: {err}") from err

    coordinator = SharkCoordinator(hass, client, entry.entry_id, host, scan_interval)

    try:
        await coordinator.async_setup()
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        # If first refresh failed, close the client we just opened.
        await client.close()
        raise

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    _async_remove_generated_area_prefixes(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Apply options changes (e.g. new scan interval) live, no restart needed.
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


def _async_remove_generated_area_prefixes(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Remove an area prefix from integration-generated entity IDs."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)
    vacuum_slug = slugify(entry.data[CONF_NAME])

    for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        device = (
            device_registry.async_get(entity.device_id) if entity.device_id else None
        )
        area_id = entity.area_id or (device.area_id if device else None)
        area = area_registry.async_get_area(area_id) if area_id else None
        if area is None:
            continue

        area_prefix = f"{slugify(area.name)}_"
        entity_domain, object_id = entity.entity_id.split(".", 1)
        generated_prefix = f"{area_prefix}{vacuum_slug}"
        if object_id != generated_prefix and not object_id.startswith(
            f"{generated_prefix}_"
        ):
            continue

        object_id_without_area = object_id[len(area_prefix) :]
        new_entity_id = entity_registry.async_get_available_entity_id(
            entity_domain,
            object_id_without_area,
            current_entity_id=entity.entity_id,
        )
        entity_registry.async_update_entity(
            entity.entity_id, new_entity_id=new_entity_id
        )


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload so polling options apply immediately."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: SharkCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.client.close()
    return unload_ok
