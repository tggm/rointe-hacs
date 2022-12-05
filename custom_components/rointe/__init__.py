"""The Rointe Heaters integration."""
from __future__ import annotations

import logging

from rointesdk.rointe_api import ApiResponse, RointeAPI

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_INSTALLATION,
    CONF_LOCAL_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    PLATFORMS,
    ROINTE_API_MANAGER,
    ROINTE_COORDINATOR,
    ROINTE_DEVICE_MANAGER,
    ROINTE_HA_DEVICES,
    ROINTE_HA_ROINTE_MAP,
)
from .coordinator import RointeDataUpdateCoordinator
from .device_manager import RointeDeviceManager

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Rointe Heaters from a config entry."""

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        ROINTE_HA_ROINTE_MAP: {},
        ROINTE_HA_DEVICES: set(),
    }

    success = await init_device_manager(hass, entry)

    if not success:
        hass.data[DOMAIN].pop(entry.entry_id)

        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

        _LOGGER.error("Config entry not ready in async_setup_entry")
        raise ConfigEntryNotReady("Unable to connect to Rointe API.")

    return bool(success)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and removes event handlers."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: RointeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
            ROINTE_COORDINATOR
        ]

        while coordinator.cleanup_callbacks:
            coordinator.cleanup_callbacks.pop()()

    return unload_ok


async def init_device_manager(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialize the device manager and coordinator."""

    api = await hass.async_add_executor_job(
        RointeAPI, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )

    _LOGGER.debug("Device manager: Initializing auth")

    # Login to the Rointe API.
    login_result: ApiResponse = await hass.async_add_executor_job(
        api.initialize_authentication
    )

    if not login_result.success:
        _LOGGER.error(
            "Unable to authenticate to Rointe API: %s", login_result.error_message
        )
        return False

    rointe_device_manager = RointeDeviceManager(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        installation_id=entry.data[CONF_INSTALLATION],
        local_id=entry.data[CONF_LOCAL_ID],
        hass=hass,
        rointe_api=api,
    )

    hass.data[DOMAIN][entry.entry_id][ROINTE_DEVICE_MANAGER] = rointe_device_manager
    hass.data[DOMAIN][entry.entry_id][ROINTE_API_MANAGER] = api

    _LOGGER.debug("Device manager: Initializing Data Coordinator")

    rointe_coordinator = RointeDataUpdateCoordinator(hass, rointe_device_manager)
    hass.data[DOMAIN][entry.entry_id][ROINTE_COORDINATOR] = rointe_coordinator

    _LOGGER.debug("Device manager: First Refresh")
    await rointe_coordinator.async_config_entry_first_refresh()

    _LOGGER.debug("Device manager: Setup platforms")
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True
