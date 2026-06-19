"""Config flow for Shark Vacuum Local."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from sharklocal import ConnectError, SharklocalError

from .client import create_vacuum_client

from .const import (
    CONF_MAPPING,
    CONF_FAN_SPEED_PATH,
    CONF_SCAN_INTERVAL,
    CONF_USE_MQTT,
    DEFAULT_MAPPING,
    DEFAULT_FAN_SPEED_PATH,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_MQTT,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_NAME): str,
        vol.Optional(CONF_MAPPING, default=DEFAULT_MAPPING): str,
        vol.Optional(CONF_USE_MQTT, default=DEFAULT_USE_MQTT): bool,
    }
)


async def _probe(host: str, mapping: str, use_mqtt: bool) -> str | None:
    """Try to talk to the vacuum. Returns the MAC address as a unique ID, or None."""
    client = create_vacuum_client(host, mapping, use_mqtt)
    try:
        async with client:
            await client.probe()
            # Confirm we can read status — this is the cheapest call.
            await client.get_status()
            # Try to get the MAC for a stable unique ID. Best-effort.
            try:
                wifi = await client.get_wifi_status()
                if wifi and wifi.mac_address:
                    return wifi.mac_address
            except SharklocalError:
                pass
    except ConnectError:
        raise
    except SharklocalError:
        raise
    return None


def _normalized_identifier(value: str | None) -> str | None:
    """Normalize MAC-style unique IDs for reliable comparison."""
    if value is None:
        return None
    return "".join(character for character in value.casefold() if character.isalnum())


class SharkVacuumLocalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Shark Vacuum Local."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Tell HA we have an options flow (the 'Configure' button).

        config_entry param is required by HA's signature but unused here —
        HA assigns it to the flow instance automatically.
        """
        return SharkVacuumLocalOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step (manual entry)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            mapping = user_input.get(CONF_MAPPING, DEFAULT_MAPPING)
            use_mqtt = user_input.get(CONF_USE_MQTT, DEFAULT_USE_MQTT)

            # Make host the fallback unique ID; replaced by MAC if we can read it.
            unique_id = host
            try:
                mac = await _probe(host, mapping, use_mqtt)
                if mac:
                    unique_id = mac
            except ConnectError:
                errors["base"] = "cannot_connect"
            except SharklocalError:
                errors["base"] = "unknown"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error probing %s", host)
                errors["base"] = "unknown"

            if not errors:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_HOST: host,
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_MAPPING: mapping,
                        CONF_USE_MQTT: use_mqtt,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow the vacuum IP address to be changed after setup."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            mapping = entry.data.get(CONF_MAPPING, DEFAULT_MAPPING)
            use_mqtt = entry.data.get(CONF_USE_MQTT, DEFAULT_USE_MQTT)

            try:
                mac = await _probe(host, mapping, use_mqtt)
            except ConnectError:
                errors["base"] = "cannot_connect"
            except SharklocalError:
                errors["base"] = "unknown"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error probing %s", host)
                errors["base"] = "unknown"
            else:
                old_host = entry.data[CONF_HOST]
                unique_id = entry.unique_id
                unique_id_was_host = unique_id is None or unique_id == old_host

                if (
                    mac
                    and not unique_id_was_host
                    and _normalized_identifier(mac)
                    != _normalized_identifier(unique_id)
                ):
                    errors["base"] = "wrong_device"
                else:
                    new_unique_id = mac if mac and unique_id_was_host else unique_id
                    duplicate = next(
                        (
                            candidate
                            for candidate in self.hass.config_entries.async_entries(
                                DOMAIN
                            )
                            if candidate.entry_id != entry.entry_id
                            and _normalized_identifier(candidate.unique_id)
                            == _normalized_identifier(new_unique_id)
                        ),
                        None,
                    )
                    if new_unique_id and duplicate:
                        errors["base"] = "already_configured"
                    else:
                        return self.async_update_reload_and_abort(
                            entry,
                            unique_id=new_unique_id,
                            data_updates={CONF_HOST: host},
                        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=entry.data[CONF_HOST]
                    ): str
                }
            ),
            description_placeholders={"name": entry.title},
            errors=errors,
        )


class SharkVacuumLocalOptionsFlow(OptionsFlow):
    """Options flow — backs the 'Configure' button on the integration card.

    Note: in modern HA (2024.11+) we do NOT set self.config_entry in __init__.
    HA assigns it automatically and direct assignment is deprecated.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and save the options form."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        fan_speed_path = self.config_entry.options.get(
            CONF_FAN_SPEED_PATH, DEFAULT_FAN_SPEED_PATH
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    cv.positive_int,
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
                vol.Required(
                    CONF_FAN_SPEED_PATH, default=fan_speed_path
                ): vol.All(str, vol.Match(r"^/(?!/).+")),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
