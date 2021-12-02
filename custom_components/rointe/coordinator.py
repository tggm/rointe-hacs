"""Provides the Rointe DataUpdateCoordinator."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api.device_manager import RointeDeviceManager
from .const import DOMAIN, ROINTE_API_REFRESH_SECONDS

_LOGGER = logging.getLogger(__name__)


class RointeDataUpdateCoordinator(DataUpdateCoordinator):
    """Rointe data coordinator."""

    def __init__(
        self, hass: HomeAssistant, device_manager: RointeDeviceManager
    ) -> None:
        """Initialize Rointe data updater."""
        self.device_manager = device_manager

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=self.device_manager.update,
            update_interval=timedelta(seconds=ROINTE_API_REFRESH_SECONDS),
        )
