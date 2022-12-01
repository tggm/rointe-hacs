"""Constants for the Rointe Heaters integration."""

DOMAIN = "rointe"
DEVICE_DOMAIN = "climate"
ATTRIBUTION = "Data provided by rointeconnect.com"
PLATFORMS: list[str] = ["climate", "sensor", "update"]

CONF_USERNAME = "rointe_username"
CONF_PASSWORD = "rointe_password"
CONF_INSTALLATION = "rointe_installation"
CONF_LOCAL_ID = "rointe_local_id"

ROINTE_MANUFACTURER = "Rointe"
ROINTE_API_MANAGER = "rointe_api_manager"
ROINTE_DEVICE_MANAGER = "rointe_device_manager"
ROINTE_COORDINATOR = "rointe_coordinator"
ROINTE_HA_ROINTE_MAP = "rointe_ha_rointe_map"
ROINTE_HA_DEVICES = "rointe_ha_devices"
ROINTE_HA_SIGNAL_UPDATE_ENTITY = "rointe_entry_update"
ROINTE_API_REFRESH_SECONDS = 60
SCAN_INTERVAL_SECONDS = 30
ROINTE_SUPPORTED_DEVICES = ["radiator", "towel", "therm"]

CMD_SET_TEMP = "cmd_set_temp"
CMD_SET_PRESET = "cmd_set_preset"
CMD_HVAC_OFF = "cmd_turn_off"
CMD_SET_HVAC_MODE = "cmd_set_hvac_mode"

RADIATOR_DEFAULT_TEMPERATURE = 20

PRESET_ROINTE_ICE = "Anti-frost"
