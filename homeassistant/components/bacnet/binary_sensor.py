"""Platform for binary sensor integration."""

from __future__ import annotations

from typing import Any, Literal

from bacpypes3.object import BinaryPV, BinaryValueObject, DeviceObject

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import STATE_OFF, STATE_ON, UnitOfTemperature
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
    if config_entry.data["entities"].get("binary_sensor") is not None:
        print(
            f"Found binary sensor objects in config entry data: {config_entry.data['entities']['binary_sensor']}"
        )
        for entity in config_entry.data["entities"]["binary_sensor"]:
            entities.append(
                BacnetBinary(
                    config_entry.data["own_ip"],
                    config_entry.data["device"]["device_address"],
                    config_entry.runtime_data,
                    entity,
                )
            )
        async_add_entities(entities, update_before_add=True)
    else:
        print("No binary sensor objects found in config entry data.")


class BacnetBinary(BinarySensorEntity):
    """Representation of an Binary Sensor."""

    def __init__(
        self,
        own_ip: str,
        device_address: str,
        device: DeviceObject,
        runtime_data: dict[str, str],
    ) -> None:
        """Initialize the Binary Sensor entity."""
        print(f"Initializing BacnetBinary with id: {id}")
        print(f"entity_data : {runtime_data}")
        self.own_ip = own_ip
        self.device_address = device_address
        self.device = device
        self.state_id = runtime_data["is_on"]

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
        await self.async_update()

    async def async_update(self) -> None:
        """Update the state of the sensor entity."""
        api = BACnetAPI(self.own_ip)
        state = BinaryPV(
            await api.getProperty(
                self.device_address,
                self.device.vendorIdentifier,
                self.state_id,
            )
        )
        self._attr_is_on = str(state) == "active"

    @property
    def state(self) -> Literal["on", "off"] | None:
        """Return the state of the binary sensor."""
        if (is_on := self.is_on) is None:
            return None
        return STATE_ON if is_on else STATE_OFF
