"""Platform for climate integration."""

from __future__ import annotations

from typing import Any

from bacpypes3.object import DeviceObject

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BACnetConfigEntry
from .const import DOMAIN
from .coordinator import APICoordinator

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
                    config_entry.data["own_ip"],
                    config_entry.data["device"]["device_address"],
                    config_entry.runtime_data["device_obj"],
                    entity,
                    config_entry.runtime_data["api_coordinator"],
                )
            )
        async_add_entities(entities, update_before_add=True)
    elif config_entry.data["entities"].get("climate_c") is not None:
        print(
            f"Found cooling objects in config entry data: {config_entry.data['entities']['climate_c']}"
        )
    else:
        print("No heating objects found in config entry data.")


class BacnetClimate(CoordinatorEntity, ClimateEntity):
    """Representation of an Epson Beamer media player."""

    def __init__(
        self,
        own_ip: str,
        device_address: str,
        device: DeviceObject,
        runtime_data: dict[str, str],
        apiCoordinator: APICoordinator,
    ) -> None:
        """Initialize the media player entity."""
        print("Initializing BacnetClimate")
        print(
            f"entity_data : {runtime_data}"
        )  # {'name': 'f', 'current_temperature': 'binary-value,2796206', 'target_temperature': 'binary-value,2796206'}
        # print(get_set_properties(device))
        self.own_ip = own_ip
        self.device_address = device_address
        self.device = device
        self.current_temperature_id = runtime_data["current_temperature"]
        self.target_temperature_id = runtime_data["target_temperature"]

        context = [
            {
                "device_address": device_address,
                "vendor_id": device.vendorIdentifier,
                "value_id": runtime_data["target_temperature"],
                "entity_id": (
                    runtime_data["name"] + "target_temperature"
                ),  # Add a unique identifier
            },
            {
                "device_address": device_address,
                "vendor_id": device.vendorIdentifier,
                "value_id": runtime_data["current_temperature"],
                "entity_id": (
                    runtime_data["name"] + "current_temperature"
                ),  # Add a unique identifier
            },
        ]
        super().__init__(apiCoordinator, context=context)

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
        await super().async_added_to_hass()
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
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (
            self.coordinator.data
            and (self._attr_name + "current_temperature") in self.coordinator.data
        ):
            print(
                f"Updating sensor {self._attr_name + ' current_temperature'} with value: {self.coordinator.data[self._attr_name + 'current_temperature']}"
            )
            print(
                f"Updating sensor {self._attr_name + ' target_temperature'} with value: {self.coordinator.data[self._attr_name + 'target_temperature']}"
            )
            self._attr_current_temperature = self.coordinator.data[
                self._attr_name + "current_temperature"
            ]
            self._attr_target_temperature = self.coordinator.data[
                self._attr_name + "target_temperature"
            ]
            self.async_write_ha_state()
        else:
            print(f"No data found for sensor {self._attr_name} in coordinator update.")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        self._attr_hvac_mode = hvac_mode
        # TODO: Implement actual logic to set the HVAC mode

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        """Turn the entity on."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if "temperature" in kwargs:
            self._attr_target_temperature = kwargs["temperature"]
            if kwargs["temperature"] < self._attr_current_temperature:
                self._attr_hvac_mode = HVACMode.OFF
            else:
                self._attr_hvac_mode = HVACMode.HEAT
