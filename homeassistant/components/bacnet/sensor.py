"""Platform for sensor integration."""

from __future__ import annotations

from typing import Any

from bacpypes3.object import EngineeringUnits, AnalogValueObject, DeviceObject

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
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
    """Set up the Sensor from a config entry."""
    print(f"config_entry_data: {config_entry.data}")
    entities = []
    if config_entry.data["entities"].get("sensor") is not None:
        print(
            f"Found sensor objects in config entry data: {config_entry.data['entities']['sensor']}"
        )
        for entity in config_entry.data["entities"]["sensor"]:
            api = BACnetAPI(config_entry.data["own_ip"])
            entity["unit"] = await api.getProperty(
                config_entry.data["device"]["device_address"],
                config_entry.runtime_data.vendorIdentifier,
                entity["native_value"],
                "units",
            )

            entities.append(
                BacnetSensor(
                    config_entry.data["own_ip"],
                    config_entry.data["device"]["device_address"],
                    config_entry.runtime_data,
                    entity,
                )
            )
        async_add_entities(entities, update_before_add=True)
    else:
        print("No sensor objects found in config entry data.")


class BacnetSensor(SensorEntity):
    """Representation of an Sensor."""

    def __init__(
        self,
        own_ip: str,
        device_address: str,
        device: DeviceObject,
        runtime_data: dict[str, str],
    ) -> None:
        """Initialize the Binary Sensor entity."""
        print(f"Initializing BacnetSensor with id: {id}")
        print(f"entity_data : {runtime_data}")
        self.own_ip = own_ip
        self.device_address = device_address
        self.device = device
        self.value_id = runtime_data["native_value"]

        self._attr_native_value = None

        print(str(runtime_data["unit"]) == "degrees-celsius")
        if str(runtime_data["unit"]) == "degrees-celsius":
            self._attr_native_unit_of_measurement = "°C"
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        elif str(runtime_data["unit"]) == "degrees-kelvin":
            self._attr_native_unit_of_measurement = "K"
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        elif str(runtime_data["unit"]) == "percent":
            self._attr_native_unit_of_measurement = "%"
            self._attr_device_class = None
        elif str(runtime_data["unit"]) == "hours":
            self._attr_native_unit_of_measurement = "h"
            self._attr_device_class = SensorDeviceClass.DURATION
        elif str(runtime_data["unit"]) == "degrees-kelvin-per-hour":
            self._attr_native_unit_of_measurement = "K/h"
            self._attr_device_class = None
        elif str(runtime_data["unit"]) == "pascals":
            self._attr_native_unit_of_measurement = "Pa"
            self._attr_device_class = SensorDeviceClass.PRESSURE
        else:
            self._attr_native_unit_of_measurement = None
            self._attr_device_class = None

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
        self._attr_native_value = await api.getProperty(
            self.device_address,
            self.device.vendorIdentifier,
            self.value_id,
        )
