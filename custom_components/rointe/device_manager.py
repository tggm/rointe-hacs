"""Rointe app data model."""

from __future__ import annotations

from datetime import datetime
import logging

from rointesdk.device import RointeDevice, ScheduleMode
from rointesdk.dto import EnergyConsumptionData
from rointesdk.rointe_api import ApiResponse, RointeAPI
from rointesdk.utils import get_product_by_type_version

from homeassistant.components.climate import PRESET_COMFORT, PRESET_ECO
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


def determine_latest_firmware(device_data, fw_map) -> str | None:
    """Determine the latest FW available for a device."""

    if not device_data or "data" not in device_data:
        return None

    product_type = device_data["data"].get("type", None)
    version = device_data["data"].get("product_version", None)
    current_firmware = device_data["firmware"].get("firmware_version_device", None)

    if not product_type or not version or not current_firmware:
        _LOGGER.warning(
            "Unable to determine latest FW for [%s][%s] at v[%s]",
            product_type,
            version,
            current_firmware,
        )
        return None

    product = get_product_by_type_version(product_type, version)

    if not product:
        _LOGGER.warning(
            "Product not found: [%s][%s] at v[%s]",
            product_type,
            version,
            current_firmware,
        )
        return None

    if product in fw_map and version in fw_map[product]:
        return fw_map[product][version]

    # If no update path available return the current firmware string.
    return current_firmware


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

    def _fail_all_devices(self):
        """Set all devices as unavailable."""

        if self.rointe_devices:
            for device in self.rointe_devices.values():
                device.hass_available = False

    async def update(self) -> dict[str, list[RointeDevice]]:
        """Retrieve the devices from the user's installation."""

        _LOGGER.debug("Device manager updating")

        installation_response: ApiResponse = await self.hass.async_add_executor_job(
            self.rointe_api.get_installation_by_id, self.installation_id, self.local_id
        )

        if not installation_response.success:
            _LOGGER.error(
                "Unable to get Rointe Installations. Error: %s",
                installation_response.error_message,
            )
            self._fail_all_devices()
            return {}

        installation = installation_response.data
        discovered_devices: dict[str, list[RointeDevice]] = {}
        firmware_map = await self._get_firmware_map()

        _LOGGER.debug("Processing zones")

        for zone_key in installation["zones"]:
            _LOGGER.debug("Processing zone: %s", zone_key)

            zone = installation["zones"][zone_key]

            if "devices" not in zone:
                _LOGGER.debug("No devices info found for zone")
                continue

            devices = zone["devices"]

            for device_id in devices:
                _LOGGER.debug("Processing device ID: %s", device_id)

                if not devices[device_id]:
                    _LOGGER.debug("Device ID: %s has no data", device_id)

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

                    latest_fw = None

                    if firmware_map:
                        latest_fw = determine_latest_firmware(
                            device_data_response.data, firmware_map
                        )

                    new_devices = self._add_or_update_device(
                        device_data_response.data, energy_data, device_id, latest_fw
                    )

                    if new_devices:
                        for new_device in new_devices:
                            discovered_devices[new_device.id] = new_device

                else:
                    _LOGGER.warning(
                        "Failed getting device status for %s. Error: %s",
                        device_id,
                        device_data_response.error_message,
                    )

                    devices[device_id].hass_available = False

        return discovered_devices

    async def _get_firmware_map(self) -> dict[str, str] | None:
        """Retrieve the latest firmware map for all rointe products."""
        firmware_map_response: ApiResponse = await self.hass.async_add_executor_job(
            self.rointe_api.get_latest_firmware
        )

        if firmware_map_response and firmware_map_response.success:
            return firmware_map_response.data

        _LOGGER.error(
            "Unable to fetch Rointe firmware update map: %s",
            firmware_map_response.error_message,
        )
        return None

    def _add_or_update_device(
        self,
        device_data,
        energy_stats: EnergyConsumptionData,
        device_id: str,
        latest_fw: str | None,
    ) -> list[RointeDevice] | None:
        """Process a device from the API and add or update it.

        Return a list of newly discovered devices.
        """

        device_data_data = device_data.get("data", None)
        new_devices = []

        if not device_data_data:
            _LOGGER.error("Device ID %s has no valid data. Ignoring", device_id)
            return None

        if device_id in self.rointe_devices:
            # Existing device, update it.
            target_device = self.rointe_devices[device_id]

            if not target_device.hass_available:
                _LOGGER.debug("Restoring device %s", target_device.name)

            target_device.update_data(device_data, energy_stats, latest_fw)

            _LOGGER.debug(
                "Updating [%s] => Power: %s, Status: %s, Mode: %s, Temp: %s",
                device_data_data.get("name", "N/A"),
                target_device.power,
                target_device.preset,
                target_device.mode,
                target_device.temp,
            )
        else:
            # New device.
            try:
                device_type = device_data["data"]["type"]

                if device_type not in ROINTE_SUPPORTED_DEVICES:
                    _LOGGER.warning("Ignoring Rointe device of type %s", device_type)
                    return None

                _LOGGER.debug(
                    "Found new device %s [%s] - %s",
                    device_data_data.get("name", "N/A"),
                    device_data_data.get("type", "N/A"),
                    device_data_data.get("product_version", "N/A"),
                )

                rointe_device = RointeDevice(
                    device_info=device_data,
                    device_id=device_id,
                    energy_data=energy_stats,
                    latest_fw=latest_fw,
                )

                new_devices.append(rointe_device)
                self.rointe_devices[device_id] = rointe_device

            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.error("Unable to process device %s. Error: %s", device_id, ex)

        return new_devices

    async def send_command(self, device: RointeDevice, command: str, arg) -> bool:
        """Send command to the device."""

        _LOGGER.debug("Sending command [%s] to device ID [%s]", command, device.id)

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

        result: ApiResponse = await self.hass.async_add_executor_job(
            self.rointe_api.set_device_temp, device, new_temp
        )

        if not result.success:
            # Set the device as unavailable.
            device.hass_available = False

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
            # Set the device as unavailable.
            device.hass_available = False

            return False

        # Update the device's internal status
        if hvac_mode == "off":
            if device.mode == "manual":
                device.temp = RADIATOR_DEFAULT_TEMPERATURE

            device.power = False
            device.preset = "off"

        elif hvac_mode == "heat":
            device.temp = device.comfort_temp
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
            # Set the device as unavailable.
            device.hass_available = False
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
