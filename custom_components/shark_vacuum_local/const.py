"""Constants for the Shark Vacuum Local integration."""
from __future__ import annotations

DOMAIN = "shark_vacuum_local"

# Config entry keys (initial setup)
CONF_HOST = "host"
CONF_NAME = "name"
CONF_MAPPING = "mapping"
CONF_USE_MQTT = "use_mqtt"

# Options keys (editable after setup via "Configure")
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_MAPPING = "sharkiq_v1"
DEFAULT_USE_MQTT = True
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_VACUUM_LEVEL = "Normal"
DEFAULT_NOTIFICATION_VOLUME = 50

# Values captured from the local MQTT interface. These are fan percentages
# inside the same command envelope the vacuum uses to start cleaning.
VACUUM_LEVEL_VALUES = {"Eco": 50, "Normal": 75, "Max": 100}
MQTT_COMMAND_TOPIC = "/qfeel/PbInput"

# Captured preference fields and their boolean encodings.
SETTING_RECHARGE_RESUME = (8, {False: 2, True: 1})
SETTING_SAVE_POWER_LEVEL = (7, {False: 1, True: 2})
SETTING_EVACUATE_RESUME = (13, {False: 2, True: 1})

# Sanity bounds for the polling interval. 5s lower bound prevents users from
# accidentally setting something pathological; 600s upper is "you basically
# turned polling off but didn't want to disable the entity".
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 600

# Platforms provided by this integration
PLATFORMS = ["vacuum", "sensor", "select", "switch", "number"]

# Event names fired on the HA bus
EVENT_DUSTBIN_REMOVED = f"{DOMAIN}_dustbin_removed"
EVENT_VACUUM_EVENT = f"{DOMAIN}_event"
