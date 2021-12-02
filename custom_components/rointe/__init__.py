"""The Rointe Heaters integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api.device_manager import RointeDeviceManager
from .const import (
    CONF_INSTALLATION,
    CONF_LOCAL_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    ROINTE_DEVICE_MANAGER,
    ROINTE_HA_DEVICES,
    ROINTE_HA_ROINTE_MAP,
)
from .coordinator import RointeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["climate", "sensor"]


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

    return bool(success)


async def init_device_manager(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialize the device manager and coordinator."""
    device_manager = RointeDeviceManager(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        installation_id=entry.data[CONF_INSTALLATION],
        local_id=entry.data[CONF_LOCAL_ID],
        hass=hass,
    )

    hass.data[DOMAIN][entry.entry_id][ROINTE_DEVICE_MANAGER] = device_manager

    coordinator = RointeDataUpdateCoordinator(hass, device_manager)
    hass.data[DOMAIN][entry.entry_id]["ROINTE_COORDINATOR"] = coordinator

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
