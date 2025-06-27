"""Platform for sensor integration."""

from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BacnetSensorConfigEntry
from .api import BACnetAPI  # noqa: F401
from .const import DOMAIN

# def setup_platform(
#     hass: HomeAssistant,
#     config: ConfigType,
#     add_entities: AddEntitiesCallback,
#     discovery_info: DiscoveryInfoType | None = None,
# ) -> None:
#     """Set up the sensor platform."""
#     add_entities([BeamerMediaPlayer()])


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BacnetSensorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Beamer from a config entry."""
    entities = []
    entities.append(BacnetClimate(config_entry.runtime_data))
    async_add_entities(entities, update_before_add=True)


class BacnetClimate(ClimateEntity):
    """Representation of an Epson Beamer media player."""

    _attr_name = "Beamer"

    def __init__(self, runtime_data) -> None:
        """Initialize the media player entity."""
        print("BacnetClimate init")
        print(runtime_data)
        print("BacnetClimate init done")
        self._attr_state = None
        self._attr_unique_id = "oifurifufriufbriufb"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_mode = HVACMode.HEAT
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
        ]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": self._attr_name,
            "manufacturer": "Epson",
            # "model": api.get_model_name(),
            # "sw_version": api.get_firmware_version(),
        }
        self._attr_current_temperature = 20.0
        self._attr_target_temperature = 22.0

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added to Home Assistant."""
        await self.async_update()

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Flag media player features that are supported."""
        return (
            ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TARGET_TEMPERATURE
        )

    async def async_update(self) -> None:
        """Update the state of the climate entity."""
        self._attr_current_temperature = self._attr_current_temperature + 1.0
        self._attr_target_temperature = self._attr_target_temperature + 1.0

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        self._attr_hvac_mode = hvac_mode
        #TODO: Implement actual logic to set the HVAC mode

    async def async_turn_on(self):
        """Turn the entity on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        """Turn the entity on."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if "temperature" in kwargs:
            self._attr_target_temperature = kwargs["temperature"]
            if kwargs["temperature"] < self._attr_current_temperature:
                self._attr_hvac_mode = HVACMode.OFF
            else:
                self._attr_hvac_mode = HVACMode.HEAT
        #TODO: Implement actual logic to set the target temperature