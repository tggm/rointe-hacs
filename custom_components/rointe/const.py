"""Constants for the Rointe Heaters integration."""

import logging

from homeassistant.const import Platform

LOGGER = logging.getLogger(__package__)

DOMAIN = "rointe"
DEVICE_DOMAIN = "climate"
PLATFORMS: list[str] = [Platform.CLIMATE, Platform.SENSOR, Platform.UPDATE]
CONF_USERNAME = "rointe_username"
CONF_PASSWORD = "rointe_password"
CONF_INSTALLATION = "rointe_installation"

ROINTE_MANUFACTURER = "Rointe"

ROINTE_SUPPORTED_DEVICES = ["radiator", "towel", "therm", "radiatorb"]

CMD_SET_TEMP = "cmd_set_temp"
CMD_SET_PRESET = "cmd_set_preset"
CMD_HVAC_OFF = "cmd_turn_off"
CMD_SET_HVAC_MODE = "cmd_set_hvac_mode"

RADIATOR_DEFAULT_TEMPERATURE = 20

PRESET_ROINTE_ICE = "Anti-frost"

RADIATOR_TEMP_STEP = 0.5
RADIATOR_TEMP_MIN = 7.0
RADIATOR_TEMP_MAX = 30.0

RADIATOR_PRESET_ECO = "eco"
RADIATOR_PRESET_COMFORT = "comfort"
RADIATOR_PRESET_ICE = "ice"
RADIATOR_PRESET_NONE = "none"

RADIATOR_MODE_AUTO = "auto"
RADIATOR_MODE_MANUAL = "manual"
