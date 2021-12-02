"""A sensor for the current Rointe radiator temperature."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    DEVICE_CLASS_TEMPERATURE,
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .api.device_manager import RointeDeviceManager
from .api.rointe_device import RointeDevice
from .const import DOMAIN, ROINTE_DEVICE_MANAGER
from .coordinator import RointeDataUpdateCoordinator
from .rointe_entity import RointeRadiatorEntity

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up lookin sensors from the config entry."""
    device_manager: RointeDeviceManager = hass.data[DOMAIN][entry.entry_id][
        ROINTE_DEVICE_MANAGER
    ]
    coordinator: RointeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "ROINTE_COORDINATOR"
    ]

    entities = []

    await coordinator.async_config_entry_first_refresh()

    sensor_description = SensorEntityDescription(
        key="current_temperature",
        name="Current Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
    )

    for device_id in device_manager.rointe_devices:
        device = device_manager.rointe_devices[device_id]

        entities.append(
            RointeHaSensor(
                description=sensor_description,
                radiator=device,
                coordinator=coordinator,
            )
        )

    async_add_entities(entities, True)


class RointeHaSensor(RointeRadiatorEntity, SensorEntity):
    """Sensor for the radiator current temperature."""

    def __init__(
        self,
        description: SensorEntityDescription,
        radiator: RointeDevice,
        coordinator: RointeDataUpdateCoordinator,
    ) -> None:
        """Init the sensor entity."""

        # Set the name and ID of this sensor to be the radiator name/id and a prefix.
        super().__init__(
            coordinator,
            radiator,
            name=f"{radiator.name} {description.name}",
            unique_id=f"{radiator.id}-{description.key}",
        )

        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the current sensor value (Probe value)."""
        return self._radiator.temp_probe
