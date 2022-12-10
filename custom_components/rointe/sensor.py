"""A sensor for the current Rointe radiator temperature."""
from __future__ import annotations

from datetime import datetime

from rointesdk.device import RointeDevice

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .coordinator import RointeDataUpdateCoordinator
from .rointe_entity import RointeRadiatorEntity
from .sensor_descriptions import SENSOR_DESCRIPTIONS, RointeSensorEntityDescription


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the radiator sensors from the config entry."""
    coordinator: RointeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    coordinator.add_sensor_entities_for_seen_keys(
        async_add_entities, SENSOR_DESCRIPTIONS, RointeGenericSensor
    )


class RointeGenericSensor(RointeRadiatorEntity, SensorEntity):
    """Generic radiator sensor."""

    entity_description: RointeSensorEntityDescription

    def __init__(
        self,
        radiator: RointeDevice,
        coordinator: RointeDataUpdateCoordinator,
        description: RointeSensorEntityDescription,
    ) -> None:
        """Initialize a generic sensor."""
        super().__init__(
            coordinator,
            radiator,
            name=f"{radiator.name} {description.name}",
            unique_id=f"{radiator.id}-{description.key}",
        )

        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the sensor value."""
        return self.entity_description.value_fn(self._radiator)

    @property
    def last_reset(self) -> datetime | None:
        """Return the last time the sensor was initialized, if relevant."""
        return self.entity_description.last_reset_fn(self._radiator)
