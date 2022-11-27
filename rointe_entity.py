"""Rointe HA base entity."""
from __future__ import annotations

from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    DOMAIN,
    ROINTE_HA_SIGNAL_UPDATE_ENTITY,
    ROINTE_MANUFACTURER,
)
from .coordinator import RointeDataUpdateCoordinator
from .device_manager import RointeDevice, RointeDeviceManager


class RointeHAEntity(CoordinatorEntity):
    """Rointe entity base class."""

    def __init__(self, coordinator: RointeDataUpdateCoordinator, name, unique_id):
        """Initialize the entity."""
        super().__init__(coordinator)
        self._unique_id = f"rointe-{unique_id}"
        self._name = name

    def get_device_manager(self) -> RointeDeviceManager:
        """Get the device manager."""
        return self.coordinator.device_manager

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def extra_state_attributes(self):
        """Return the device specific state attributes."""
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }


class RointeRadiatorEntity(RointeHAEntity):
    """Base class for Rointe entities (climate and sensors)."""

    def __init__(
        self,
        coordinator: RointeDataUpdateCoordinator,
        radiator: RointeDevice,
        name: str,
        unique_id: str,
    ) -> None:
        """Initialize the entity."""

        super().__init__(coordinator, name, unique_id)
        self._radiator = radiator
        self._signal_update = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return a device description for device registry."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._radiator.id}")},
            manufacturer=ROINTE_MANUFACTURER,
            name=self._radiator.name,
            model=f"{self._radiator.type} {self._radiator.product_version}",
            sw_version=self._radiator.firmware_version,
        )

    async def async_added_to_hass(self):
        """Listen for signals for services."""

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{ROINTE_HA_SIGNAL_UPDATE_ENTITY}_{self._radiator.id}",
                self.on_remove_handler,
            )
        )

        await super().async_added_to_hass()

    @callback
    def on_entity_update_handler(self) -> None:
        """Handle entity updated."""
        self.async_schedule_update_ha_state(force_refresh=True)

    @callback
    def on_remove_handler(self) -> None:
        """Handle entity removed."""
        self.async_write_ha_state()
