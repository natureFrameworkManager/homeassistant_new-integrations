"""Platform for sensor integration."""

from __future__ import annotations

from typing import Any

from bacpypes3.object import BinaryPV, BinaryValueObject, DeviceObject

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BACnetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Beamer from a config entry."""
    print(f"config_entry_data: {config_entry.data}")
    entities = []
    if config_entry.data["entities"].get("binary") is not None:
        print(
            f"Found binary objects in config entry data: {config_entry.data['entities']['binary']}"
        )
    else:
        print("No binary objects found in config entry data.")


class BacnetBinary(BinarySensorEntity):
    """Representation of an Binary Sensor."""

    def __init__(
        self,
        device: DeviceObject,
        id: str,
        runtime_data: dict[str, float | BinaryPV | Any],
    ) -> None:
        """Initialize the Binary Sensor entity."""
        print(f"Initializing BacnetBinary with id: {id}")
        print(f"entity_data : {runtime_data}")
        self.is_on = False
        self.device_class = BinarySensorDeviceClass.LIGHT

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added to Home Assistant."""
        await self.async_update()

    async def async_update(self) -> None:
        """Update the state of the binary entity."""
        self._attr_is_on = True
