"""Support for Rointe Climate."""

from __future__ import annotations

from abc import ABC

from rointesdk.device import RointeDevice

from homeassistant.components.climate import (
    PRESET_COMFORT,
    PRESET_ECO,
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_SET_HVAC_MODE,
    CMD_SET_PRESET,
    CMD_SET_TEMP,
    DOMAIN,
    LOGGER,
    PRESET_ROINTE_ICE,
    RADIATOR_MODE_AUTO,
    RADIATOR_MODE_MANUAL,
    RADIATOR_PRESET_COMFORT,
    RADIATOR_PRESET_ECO,
    RADIATOR_PRESET_ICE,
    RADIATOR_TEMP_MAX,
    RADIATOR_TEMP_MIN,
    RADIATOR_TEMP_STEP,
)
from .coordinator import RointeDataUpdateCoordinator
from .rointe_entity import RointeRadiatorEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the radiator climate entity from the config entry."""
    coordinator: RointeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Register the Entity classes and platform on the coordinator.
    coordinator.add_entities_for_seen_keys(
        async_add_entities, [RointeHaClimate], "climate"
    )


class RointeHaClimate(RointeRadiatorEntity, ClimateEntity, ABC):
    """Climate entity."""

    def __init__(
        self,
        radiator: RointeDevice,
        coordinator: RointeDataUpdateCoordinator,
    ) -> None:
        """Init the Climate entity."""

        super().__init__(
            coordinator, radiator, name=radiator.name, unique_id=radiator.id
        )

        self.entity_description = ClimateEntityDescription(
            key="radiator",
            name=radiator.name,
        )

    @property
    def icon(self) -> str | None:
        """Icon of the entity."""
        return "mdi:radiator"

    @property
    def temperature_unit(self) -> str:
        """Temperature unit."""
        return TEMP_CELSIUS

    @property
    def target_temperature(self) -> float:
        """Return the current temperature."""
        if self._radiator.mode == RADIATOR_MODE_MANUAL:
            if self._radiator.preset == RADIATOR_PRESET_ECO:
                return self._radiator.eco_temp
            if self._radiator.preset == RADIATOR_PRESET_COMFORT:
                return self._radiator.comfort_temp
            if self._radiator.preset == RADIATOR_PRESET_ICE:
                return self._radiator.ice_temp

        return self._radiator.temp

    @property
    def current_temperature(self) -> float:
        """Get current temperature (Probe)."""
        return self._radiator.temp_probe

    @property
    def max_temp(self) -> float:
        """Max selectable temperature."""
        if self._radiator.user_mode_supported and self._radiator.user_mode:
            return self._radiator.um_max_temp

        return RADIATOR_TEMP_MAX

    @property
    def min_temp(self) -> float:
        """Minimum selectable temperature."""
        if self._radiator.user_mode_supported and self._radiator.user_mode:
            return self._radiator.um_min_temp

        return RADIATOR_TEMP_MIN

    @property
    def target_temperature_high(self) -> float:
        """Max selectable target temperature."""
        if self._radiator.user_mode_supported and self._radiator.user_mode:
            return self._radiator.um_max_temp

        return RADIATOR_TEMP_MAX

    @property
    def target_temperature_low(self) -> float:
        """Minimum selectable target temperature."""
        if self._radiator.user_mode_supported and self._radiator.user_mode:
            return self._radiator.um_min_temp

        return RADIATOR_TEMP_MIN

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Flag supported features."""
        return (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        )

    @property
    def target_temperature_step(self) -> float | None:
        """Temperature step."""
        return RADIATOR_TEMP_STEP

    @property
    def hvac_modes(self) -> list[str]:
        """Return hvac modes available."""
        return [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]

    @property
    def preset_modes(self) -> list[str]:
        """Return the available preset modes."""
        return [PRESET_COMFORT, PRESET_ECO, PRESET_ROINTE_ICE]

    @property
    def hvac_mode(self) -> str:
        """Return the current HVAC mode."""
        if not self._radiator.power:
            return HVACMode.OFF

        if self._radiator.mode == RADIATOR_MODE_AUTO:
            return HVACMode.AUTO

        return HVACMode.HEAT

    @property
    def hvac_action(self) -> str:
        """Return the current HVAC action."""

        # Special mode for AUTO mode and waiting for schedule to activate.
        if (
            self._radiator.mode == RADIATOR_MODE_AUTO
            and self._radiator.preset == HVACMode.OFF
        ):
            return HVACAction.IDLE

        # Forced to off, either on Manual or Auto mode.
        if not self._radiator.power:
            return HVACAction.OFF

        # Otherwise, it's heating.
        return HVACAction.HEATING

    @property
    def preset_mode(self) -> str | None:
        """Convert the device's preset to HA preset modes."""

        if self._radiator.preset == RADIATOR_PRESET_ECO:
            return PRESET_ECO
        if self._radiator.preset == RADIATOR_PRESET_COMFORT:
            return PRESET_COMFORT
        if self._radiator.preset == RADIATOR_PRESET_ICE:
            return PRESET_ROINTE_ICE

        # Also captures "none" (man mode, temperature outside presets)
        return None

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        target_temperature = float(kwargs["temperature"])

        if not await self.device_manager.send_command(
            self._radiator, CMD_SET_TEMP, target_temperature
        ):
            LOGGER.error(
                "Failed to set Temperature [%s] for [%s]",
                target_temperature,
                self._radiator.name,
            )

            raise HomeAssistantError(
                f"Failed to set HVAC mode for {self._radiator.name}"
            )

        await self._signal_thermostat_update()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""

        LOGGER.debug("Setting HVAC mode to %s", hvac_mode)

        if not await self.device_manager.send_command(
            self._radiator, CMD_SET_HVAC_MODE, hvac_mode
        ):
            LOGGER.error(
                "Failed to set HVAC mode [%s] for [%s]", hvac_mode, self._radiator.name
            )

            raise HomeAssistantError(
                f"Failed to set HVAC mode for {self._radiator.name}"
            )

        await self._signal_thermostat_update()

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        LOGGER.debug("Setting preset mode: %s", preset_mode)

        if not await self.device_manager.send_command(
            self._radiator, CMD_SET_PRESET, preset_mode
        ):
            LOGGER.error(
                "Failed to set preset mode [%s] for [%s]",
                preset_mode,
                self._radiator.name,
            )

            raise HomeAssistantError(
                f"Failed to set HVAC mode for {self._radiator.name}"
            )

        await self._signal_thermostat_update()

    async def _signal_thermostat_update(self):
        """Signal a radiator change."""

        # Update the data
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
