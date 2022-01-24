"""Rointe app data model."""

from __future__ import annotations

from datetime import datetime
import logging

from rointesdk.device import RointeDevice, ScheduleMode
from rointesdk.dto import EnergyConsumptionData
from rointesdk.rointe_api import ApiResponse, RointeAPI

from homeassistant.components.climate.const import PRESET_COMFORT, PRESET_ECO
from homeassistant.core import HomeAssistant

from .const import (
    CMD_SET_HVAC_MODE,
    CMD_SET_PRESET,
    CMD_SET_TEMP,
    PRESET_ROINTE_ICE,
    RADIATOR_DEFAULT_TEMPERATURE,
    ROINTE_SUPPORTED_DEVICES,
)

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
        rointe_api: RointeAPI,
    ) -> None:
        """Initialize the device manager."""
        self.username = username
        self.password = password
        self.local_id = local_id
        self.installation_id = installation_id
        self.rointe_api = rointe_api

        self.hass = hass
        self.auth_token = None
        self.auth_token_expire_date: datetime | None = None

    async def update(self) -> bool:
        """Retrieve the devices from the users installation."""

        installation_response: ApiResponse = await self.hass.async_add_executor_job(
            self.rointe_api.get_installation_by_id, self.installation_id, self.local_id
        )

        if not installation_response.success:
            _LOGGER.error("Installation %s not found", self.installation_id)
            return False

        installation = installation_response.data

        for zone_key in installation["zones"]:
            zone = installation["zones"][zone_key]

            if "devices" not in zone:
                continue

            devices = zone["devices"]

            for device_id in devices:
                if not devices[device_id]:
                    continue

                device_data_response: ApiResponse = (
                    await self.hass.async_add_executor_job(
                        self.rointe_api.get_device, device_id
                    )
                )

                if device_data_response.success:
                    # Retrieve energy stats.
                    energy_stats_response: ApiResponse = (
                        await self.hass.async_add_executor_job(
                            self.rointe_api.get_latest_energy_stats, device_id
                        )
                    )

                    if energy_stats_response.success:
                        energy_data = energy_stats_response.data
                    else:
                        energy_data = None

                    self._add_or_update_device(
                        device_data_response.data, energy_data, device_id
                    )
                else:
                    _LOGGER.warning(
                        "Failed getting device status for %s. Error: %s",
                        device_id,
                        device_data_response.error_message,
                    )

        return True

    def _add_or_update_device(
        self, device_data, energy_stats: EnergyConsumptionData, device_id: str
    ) -> None:
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
            self.rointe_devices[device_id].update_data(device_data, energy_stats)

            # Debug
            tmp_device = self.rointe_devices[device_id]

            _LOGGER.info(
                "Updating [%s] - %s => Power: %s, Status: %s, Mode: %s, Temp: %s",
                device_id,
                device_data_data.get("name", "N/A"),
                tmp_device.power,
                tmp_device.preset,
                tmp_device.mode,
                tmp_device.temp,
            )
        else:
            # New device.
            try:
                device_type = device_data["data"]["type"]

                if device_type not in ROINTE_SUPPORTED_DEVICES:
                    _LOGGER.warning("Ignoring Rointe device type %s", device_type)
                    return

                self.rointe_devices[device_id] = RointeDevice(
                    device_info=device_data,
                    device_id=device_id,
                    energy_data=energy_stats,
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
            return await self._set_device_temp(device, arg)

        if command == CMD_SET_PRESET:
            return await self._set_device_preset(device, arg)

        if command == CMD_SET_HVAC_MODE:
            return await self._set_device_mode(device, arg)

        _LOGGER.warning("Ignoring unsupported command: %s", command)
        return False

    async def _set_device_temp(self, device: RointeDevice, new_temp: float) -> bool:
        """Set device temperature."""

        result = await self.hass.async_add_executor_job(
            self.rointe_api.set_device_temp, device, new_temp
        )

        if not result.success:
            _LOGGER.error("Unable to set device temperature for %s", device.name)
            return False

        # Update the device internal status
        device.temp = new_temp
        device.mode = "manual"
        device.power = True

        if new_temp == device.comfort_temp:
            device.preset = "comfort"
        elif new_temp == device.eco_temp:
            device.preset = "eco"
        elif new_temp == device.ice_temp:
            device.preset = "ice"
        else:
            device.preset = "none"

        return True

    async def _set_device_mode(self, device: RointeDevice, hvac_mode: str) -> bool:
        """Set the device hvac mode."""

        result = await self.hass.async_add_executor_job(
            self.rointe_api.set_device_mode, device, hvac_mode
        )

        if not result.success:
            _LOGGER.error("Unable to set device HVAC Mode for %s", device.name)
            return False

        # Update the device's internal status
        if hvac_mode == "off":
            # TODO: In auto mode should the temp be set?
            if device.mode == "manual":
                device.temp = RADIATOR_DEFAULT_TEMPERATURE

            device.power = False
            device.preset = "off"

        elif hvac_mode == "heat":
            device.temp = RADIATOR_DEFAULT_TEMPERATURE
            device.power = True
            device.mode = "manual"
            device.preset = "none"

        elif hvac_mode == "auto":
            current_mode: ScheduleMode = device.get_current_schedule_mode()

            # Set the appropriate temperature and preset according to the schedule.
            if current_mode == ScheduleMode.COMFORT:
                device.temp = device.comfort_temp
                device.preset = "comfort"
            elif current_mode == ScheduleMode.ECO:
                device.temp = device.eco_temp
                device.preset = "eco"
            elif device.ice_mode:
                device.temp = device.ice_temp
                device.preset = "ice"
            else:
                device.temp = RADIATOR_DEFAULT_TEMPERATURE

            device.power = True
            device.mode = "auto"

        return True

    async def _set_device_preset(self, device: RointeDevice, preset: str) -> bool:
        """Set device preset mode."""

        result = await self.hass.async_add_executor_job(
            self.rointe_api.set_device_preset, device, preset
        )

        if not result.success:
            _LOGGER.error(
                "Unable to set device preset for %s. Error: %s",
                device.name,
                result.error_message,
            )
            return False

        # Update the device internal status
        if preset == PRESET_COMFORT:
            device.power = True
            device.mode = "manual"
            device.preset = "comfort"
        elif preset == PRESET_ECO:
            device.power = True
            device.mode = "manual"
            device.preset = "eco"
        elif preset == PRESET_ROINTE_ICE:
            device.power = True
            device.mode = "manual"
            device.preset = "ice"

        return True
