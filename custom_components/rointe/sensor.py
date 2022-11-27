"""A sensor for the current Rointe radiator temperature."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

from rointesdk.device import RointeDevice

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ENERGY_KILO_WATT_HOUR, POWER_WATT, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, ROINTE_COORDINATOR, SCAN_INTERVAL_SECONDS
from .coordinator import RointeDataUpdateCoordinator
from .rointe_entity import RointeRadiatorEntity

LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(SCAN_INTERVAL_SECONDS)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the radiator sensors from the config entry."""
    coordinator: RointeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        ROINTE_COORDINATOR
    ]

    # Hook a callback for discovered entities for the sensor entities.
    coordinator.add_entities_for_seen_keys(
        async_add_entities,
        [RointeHaSensor, RointeEnergySensor, RointePowerSensor],
        "sensor",
    )


class RointeHaSensor(RointeRadiatorEntity, SensorEntity):
    """Sensor for the radiator current temperature."""

    def __init__(
        self,
        radiator: RointeDevice,
        coordinator: RointeDataUpdateCoordinator,
    ) -> None:
        """Init the sensor entity."""

        description = SensorEntityDescription(
            key="current_temperature",
            name="Current Temperature",
            native_unit_of_measurement=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

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

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._radiator and self._radiator.hass_available


class RointeEnergySensor(RointeRadiatorEntity, SensorEntity):
    """Sensor for the radiator energy usage in Kw/h."""

    def __init__(
        self,
        radiator: RointeDevice,
        coordinator: RointeDataUpdateCoordinator,
    ) -> None:
        """Init the sensor entity."""

        description = SensorEntityDescription(
            key="energy",
            name="Energy Consumption",
            native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

        # Set the name and ID of this sensor to be the radiator name/id and a prefix.
        super().__init__(
            coordinator,
            radiator,
            name=f"{radiator.name} {description.name}",
            unique_id=f"{radiator.id}-{description.key}",
        )

        self.entity_description = description

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._radiator and self._radiator.energy_data

    @property
    def native_value(self) -> StateType:
        """Return the current sensor value (KW/h)."""
        if self._radiator.energy_data:
            return self._radiator.energy_data.kwh

        return None

    @property
    def last_reset(self) -> datetime | None:
        """Return the last time the sensor was initialized."""
        if self._radiator.energy_data:
            return self._radiator.energy_data.start

        return None


class RointePowerSensor(RointeRadiatorEntity, SensorEntity):
    """Sensor for the radiator effective power usage in W."""

    def __init__(
        self,
        radiator: RointeDevice,
        coordinator: RointeDataUpdateCoordinator,
    ) -> None:
        """Init the sensor entity."""

        description = SensorEntityDescription(
            key="power",
            name="Effective Power",
            native_unit_of_measurement=POWER_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

        # Set the name and ID of this sensor to be the radiator name/id and a prefix.
        super().__init__(
            coordinator,
            radiator,
            name=f"{radiator.name} {description.name}",
            unique_id=f"{radiator.id}-{description.key}",
        )

        self.entity_description = description

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._radiator and self._radiator.energy_data

    @property
    def native_value(self) -> StateType:
        """Return the current sensor value (W)."""
        if self._radiator.energy_data:
            return self._radiator.energy_data.effective_power

        return None
