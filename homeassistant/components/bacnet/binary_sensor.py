"""Platform for binary sensor integration."""

from __future__ import annotations

from typing import Literal

from bacpypes3.object import DeviceObject

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import STATE_OFF, STATE_ON
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
    if config_entry.data["entities"].get("binary_sensor") is not None:
        print(
            f"Found binary sensor objects in config entry data: {config_entry.data['entities']['binary_sensor']}"
        )
        for entity in config_entry.data["entities"]["binary_sensor"]:
            entities.append(
                BacnetBinary(
                    config_entry.data["own_ip"],
                    config_entry.data["device"]["device_address"],
                    config_entry.runtime_data["device_obj"],
                    entity,
                    config_entry.runtime_data["api_coordinator"],
                )
            )
        async_add_entities(entities, update_before_add=True)
    else:
        print("No binary sensor objects found in config entry data.")


class BacnetBinary(CoordinatorEntity, BinarySensorEntity):
    """Representation of an Binary Sensor."""

    def __init__(
        self,
        own_ip: str,
        device_address: str,
        device: DeviceObject,
        runtime_data: dict[str, str],
        apiCoordinator: APICoordinator,
    ) -> None:
        """Initialize the Binary Sensor entity."""
        print(f"Initializing BacnetBinary with id: {id}")
        print(f"entity_data : {runtime_data}")
        self.own_ip = own_ip
        self.device_address = device_address
        self.device = device
        self.state_id = runtime_data["is_on"]

        context = {
            "device_address": device_address,
            "vendor_id": device.vendorIdentifier,
            "value_id": runtime_data["is_on"],
            "entity_id": runtime_data["name"],  # Add a unique identifier
        }
        super().__init__(apiCoordinator, context=context)

        self._attr_is_on = None
        self._attr_device_class = BinarySensorDeviceClass[
            runtime_data["device_class"]
        ]  # BinarySensorDeviceClass.LIGHT

        self._attr_name = f"{runtime_data['name']}"
        self._attr_unique_id = str(self.device.objectIdentifier) + "-" + self._attr_name

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

    async def async_update(self) -> None:
        """Update the state of the sensor entity."""
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data and self._attr_name in self.coordinator.data:
            print(
                f"Updating sensor {self._attr_name} with value: {self.coordinator.data[self._attr_name]}"
            )
            self._attr_is_on = str(self.coordinator.data[self._attr_name]) == "active"
            self.async_write_ha_state()
        else:
            print(f"No data found for sensor {self._attr_name} in coordinator update.")

    @property
    def state(self) -> Literal["on", "off"] | None:
        """Return the state of the binary sensor."""
        if (is_on := self.is_on) is None:
            return None
        return STATE_ON if is_on else STATE_OFF
