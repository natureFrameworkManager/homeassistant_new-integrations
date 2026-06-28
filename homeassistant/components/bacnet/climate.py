"""Platform for sensor integration."""

from __future__ import annotations

from typing import Any

from bacpypes3.object import BinaryPV, BinaryValueObject, DeviceObject

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BACnetConfigEntry
from .api import BACnetAPI
from .const import DOMAIN

# def setup_platform(
#     hass: HomeAssistant,
#     config: ConfigType,
#     add_entities: AddEntitiesCallback,
#     discovery_info: DiscoveryInfoType | None = None,
# ) -> None:
#     """Set up the sensor platform."""
#     add_entities([BeamerMediaPlayer()])


def get_set_properties(obj: object) -> dict[str, object]:
    """Return a dict of all set (non-None) properties for a BACnet object."""
    # BACpypes3 objects have _elements with property names
    return {
        attr: getattr(obj, attr)
        for attr in obj._elements.keys()
        if getattr(obj, attr, None) is not None
    }


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BACnetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Beamer from a config entry."""
    print(f"config_entry_data: {config_entry.data}")
    entities = []
    if config_entry.data["entities"].get("climate_h") is not None:
        print(
            f"Found heating objects in config entry data: {config_entry.data['entities']['climate_h']}"
        )
        for entity in config_entry.data["entities"]["climate_h"]:
            entities.append(
                BacnetClimate(
                    config_entry.data["device"]["device_address"],
                    config_entry.runtime_data,
                    entity,
                )
            )
        async_add_entities(entities, update_before_add=True)
    elif config_entry.data["entities"].get("climate_c") is not None:
        print(
            f"Found cooling objects in config entry data: {config_entry.data['entities']['climate_c']}"
        )
    else:
        print("No heating objects found in config entry data.")


class BacnetClimate(ClimateEntity):
    """Representation of an Epson Beamer media player."""

    def __init__(
        self,
        device_address: str,
        device: DeviceObject,
        runtime_data: dict[str, str],
    ) -> None:
        """Initialize the media player entity."""
        print(f"Initializing BacnetClimate")
        print(
            f"entity_data : {runtime_data}"
        )  # {'name': 'f', 'current_temperature': 'binary-value,2796206', 'target_temperature': 'binary-value,2796206'}
        # print(get_set_properties(device))
        self.device_address = device_address
        self.device = device
        self.current_temperature_id = runtime_data["current_temperature"]
        self.target_temperature_id = runtime_data["target_temperature"]

        self._attr_state = None
        self._attr_name = f"{runtime_data['name']}"
        self._attr_unique_id = str(self.device.objectIdentifier) + "-" + self._attr_name
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
        ]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device.objectIdentifier))},
            "name": device.description or device.objectName,
            "manufacturer": device.vendorName,
            "model": device.modelName,
            "sw_version": device.applicationSoftwareVersion,
        }

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
        api = BACnetAPI()
        self._attr_current_temperature = await api.getProperty(
            self.device_address,
            self.device.vendorIdentifier,
            self.current_temperature_id,
        )
        self._attr_target_temperature = await api.getProperty(
            self.device_address,
            self.device.vendorIdentifier,
            self.target_temperature_id,
        )

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        self._attr_hvac_mode = hvac_mode
        # TODO: Implement actual logic to set the HVAC mode

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
