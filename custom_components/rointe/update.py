"""Update entity platform for Rointe devices."""
from __future__ import annotations

import logging

from rointesdk.device import RointeDevice

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ROINTE_COORDINATOR
from .coordinator import RointeDataUpdateCoordinator
from .rointe_entity import RointeRadiatorEntity

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the radiator sensors from the config entry."""
    coordinator: RointeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        ROINTE_COORDINATOR
    ]

    # Hook a callback for discovered entities for the update entity.
    coordinator.add_entities_for_seen_keys(
        async_add_entities,
        [RointeUpdateEntity],
        "update",
    )


class RointeUpdateEntity(RointeRadiatorEntity, UpdateEntity):
    """Update entity."""

    def __init__(
        self,
        radiator: RointeDevice,
        coordinator: RointeDataUpdateCoordinator,
    ) -> None:
        """Init the update entity."""
        description = UpdateEntityDescription(
            key="fw_update_available",
            name="Update Available",
            device_class=UpdateDeviceClass.FIRMWARE,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

        # Set the name and ID of this entity to be the radiator name/id and a prefix.
        super().__init__(
            coordinator,
            radiator,
            name=f"{radiator.name} {description.name}",
            unique_id=f"{radiator.id}-{description.key}",
        )

    @property
    def installed_version(self) -> str | None:
        """Version installed and in use."""
        return self._radiator.firmware_version

    @property
    def latest_version(self) -> str | None:
        """Latest version available for install."""
        return self._radiator.latest_firmware_version
