"""Provides the Rointe DataUpdateCoordinator."""
from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import logging
from typing import Any

from rointesdk.device import RointeDevice

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, PLATFORMS, ROINTE_API_REFRESH_SECONDS
from .device_manager import RointeDeviceManager

_LOGGER = logging.getLogger(__name__)


class RointeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, RointeDevice]]):
    """Rointe data coordinator."""

    def __init__(
        self, hass: HomeAssistant, device_manager: RointeDeviceManager
    ) -> None:
        """Initialize Rointe data updater."""
        self.device_manager = device_manager
        self.unregistered_keys: dict[str, dict[str, RointeDevice]] = {}
        self.cleanup_callbacks: list[Callable[[], None]] = []

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=ROINTE_API_REFRESH_SECONDS),
        )

        for platform in PLATFORMS:
            self.unregistered_keys[platform] = {}

    async def _async_update_data(self) -> dict[str, RointeDevice]:
        """Fetch data from API."""

        devices = await self.device_manager.update()

        for device_id, device in devices.items():
            for platform in PLATFORMS:
                # We need to keep two lists. One for each platform.
                if device_id not in self.unregistered_keys[platform]:
                    self.unregistered_keys[platform][device_id] = device

        return devices

    @callback
    def add_entities_for_seen_keys(
        self,
        async_add_entities: AddEntitiesCallback,
        entity_constructor_list: list[Any],
        platform: str,
    ) -> None:
        """Add entities for new devices."""

        @callback
        def _add_entities_for_unregistered_keys() -> None:
            """Add entities for keys seen for the first time."""
            new_entities: list = []
            discovered_devices: dict[str, RointeDevice] = self.data

            if discovered_devices:
                for device_id, device in discovered_devices.items():
                    if device_id in self.unregistered_keys[platform]:
                        for constructor in entity_constructor_list:
                            new_entities.append(constructor(device, self))

                        self.unregistered_keys[platform].pop(device_id)

            if new_entities:
                async_add_entities(new_entities)

        # End callback.

        _add_entities_for_unregistered_keys()

        # The inner callback is called by the coordinator after update.
        self.cleanup_callbacks.append(
            self.async_add_listener(_add_entities_for_unregistered_keys)
        )
