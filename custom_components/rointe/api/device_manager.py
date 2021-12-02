"""Rointe app data model."""

from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
)
from homeassistant.core import HomeAssistant

from ..const import CMD_SET_PRESET, CMD_SET_TEMP, ROINTE_SUPPORTED_DEVICES
from .api_wrapper import (
    get_device,
    get_installation_by_id,
    login_user,
    set_device_preset,
    set_device_temp,
)
from .rointe_device import RointeDevice, ScheduleMode

_LOGGER = logging.getLogger(__name__)


class RointeDeviceManager:
    """Device Manager."""

    rointe_devices: dict[str, RointeDevice] = {}

    def __init__(
        self,
        username: str,
        password: str,
        local_id: str,
        installation_id: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the device manager."""
        self.username = username
        self.password = password
        self.local_id = local_id
        self.installation_id = installation_id

        self.hass = hass
        self.auth_token = None
        self.auth_token_expire_date: datetime | None = None

    async def _ensure_valid_auth(self) -> None:
        """Ensure there is a valid authentication token present."""

        now = datetime.now()

        if not self.auth_token or (
            self.auth_token_expire_date and self.auth_token_expire_date < now
        ):
            try:
                login_data = await self.hass.async_add_executor_job(
                    login_user, self.username, self.password
                )

                self.auth_token = login_data["auth_token"]
                self.auth_token_expire_date = login_data["expires"]
            except Exception:  # pylint: disable=broad-except
                _LOGGER.error("Unable to authenticate with RointeConnect")

    async def update(self) -> bool:
        """Retrieve the devices from the users installation."""
        await self._ensure_valid_auth()

        installation = await self.hass.async_add_executor_job(
            get_installation_by_id, self.installation_id, self.local_id, self.auth_token
        )

        if not installation:
            _LOGGER.error("Installation %s not found", self.installation_id)
            return False

        for zone_key in installation["zones"]:
            zone = installation["zones"][zone_key]

            if "devices" not in zone:
                continue

            devices = zone["devices"]

            for device_id in devices:
                if not devices[device_id]:
                    continue

                device_data = await self.hass.async_add_executor_job(
                    get_device, device_id, self.auth_token
                )

                if device_data:
                    self._add_or_update_device(device_data, device_id)

        return True

    def _add_or_update_device(self, device_data, device_id: str) -> None:
        """Process a device from the API and add or update it."""

        device_data_data = device_data.get("data", None)

        if not device_data_data:
            _LOGGER.error("Device ID %s has no valid data. Ignoring", device_id)
            return

        _LOGGER.info(
            "Processing device %s [%s] - %s",
            device_data_data.get("name", "N/A"),
            device_data_data.get("type", "N/A"),
            device_data_data.get("product_version", "N/A"),
        )

        if device_id in self.rointe_devices:
            # Existing device, update it.
            self.rointe_devices[device_id].update_data(device_data)

            # Debug
            tmp_device = self.rointe_devices[device_id]

            _LOGGER.info(
                "Updating [%s] - %s => Power: %s, Status: %s, Mode: %s",
                device_id,
                device_data_data.get("name", "N/A"),
                tmp_device.power,
                tmp_device.preset,
                tmp_device.mode,
            )
        else:
            # New device.
            try:
                device_type = device_data["data"]["type"]

                if device_type not in ROINTE_SUPPORTED_DEVICES:
                    _LOGGER.warning("Ignoring Rointe device type %s", device_type)
                    return

                self.rointe_devices[device_id] = RointeDevice(
                    device_info=device_data, device_id=device_id
                )

                # debug
                _LOGGER.info(
                    "Creating new device [%s] - %s",
                    device_id,
                    device_data_data.get("name", "N/A"),
                )

            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.error("Unable to process device %s. Error: %s", device_id, ex)

            _LOGGER.info("Detected new device %s", device_data["data"]["name"])

    async def send_command(self, device: RointeDevice, command: str, arg) -> bool:
        """Send command to the device."""

        if command == CMD_SET_TEMP:
            result = await self._set_device_temp(device, arg)
        elif command == CMD_SET_PRESET:
            result = await self._set_device_preset(device, arg)
        else:
            _LOGGER.warning("Ignoring unsupported command: %s", command)
            return False

        return result

    async def _set_device_temp(self, device: RointeDevice, new_temp: float) -> bool:
        """Set device temperature."""
        await self._ensure_valid_auth()

        result = await self.hass.async_add_executor_job(
            set_device_temp, device, self.auth_token, new_temp
        )

        if not result:
            _LOGGER.error("Unable to set device temperature for %s", device.name)
            return False

        # Update the device internal status
        device.temp = new_temp
        device.mode = "manual"

        return True

    async def _set_device_preset(self, device: RointeDevice, preset: str) -> bool:
        """Set device preset mode."""
        await self._ensure_valid_auth()

        result = await self.hass.async_add_executor_job(
            set_device_preset, device, self.auth_token, preset
        )

        if not result:
            _LOGGER.error("Unable to set device preset for %s", device.name)
            return False

        # Update the device internal status
        if preset == HVAC_MODE_OFF:
            device.power = False
            device.mode = "manual"
            device.preset = "none"
        elif preset == HVAC_MODE_HEAT:
            device.power = True
            device.mode = "manual"
            device.preset = "none"
        elif preset == HVAC_MODE_AUTO:
            current_mode: ScheduleMode = device.get_current_schedule_mode()

            if current_mode == ScheduleMode.COMFORT:
                temp = device.comfort_temp
                preset = "comfort"
            elif current_mode == ScheduleMode.ECO:
                temp = device.eco_temp
                preset = "eco"
            elif device.ice_mode:
                temp = device.ice_temp
                preset = "ice"
            else:
                temp = 20.0
                preset = "off"

            device.temp = temp
            device.preset = preset
            device.power = True
            device.mode = "auto"

        return True
