"""API for interacting with BACnet devices in Home Assistant."""

from argparse import Namespace
import asyncio
import logging
import re
import sys
from typing import Any

from bacpypes3.apdu import AbortPDU, AbortReason, ErrorRejectAbortNack
from bacpypes3.app import Application
from bacpypes3.object import AnalogValueObject, BinaryValueObject, DeviceObject
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier, PropertyIdentifier
from bacpypes3.vendor import get_vendor_info

from homeassistant.exceptions import ConfigEntryNotReady

_LOGGER = logging.getLogger(__name__)


class BACnetAPI:
    """API for interacting with BACnet devices."""

    def get_set_properties(self, obj: object) -> dict[str, object]:
        """Return a dict of all set (non-None) properties for a BACnet object."""
        # BACpypes3 objects have _elements with property names
        return {
            attr: getattr(obj, attr)
            for attr in obj._elements.keys()
            if getattr(obj, attr, None) is not None
        }

    async def object_identifiers(
        self, app: Application, device_address: Address, device_identifier: ObjectIdentifier
    ) -> list[ObjectIdentifier]:
        """Read the entire object list from a device at once, or if that fails, read the object identifiers one at a time."""

        # try reading the whole thing at once, but it might be too big and
        # segmentation isn't supported
        try:
            object_list = await app.read_property(
                device_address, device_identifier, "object-list"
            )
            return object_list
        except AbortPDU as err:
            if err.apduAbortRejectReason != AbortReason.segmentationNotSupported:
                sys.stderr.write(f"{device_identifier} object-list abort: {err}\n")
                return []
        except ErrorRejectAbortNack as err:
            sys.stderr.write(f"{device_identifier} object-list error/reject: {err}\n")
            return []

        # fall back to reading the length and each element one at a time
        object_list = []
        try:
            # read the length
            object_list_length = await app.read_property(
                device_address,
                device_identifier,
                "object-list",
                array_index=0,
            )

            # read each element individually
            for i in range(object_list_length):
                object_identifier = await app.read_property(
                    device_address,
                    device_identifier,
                    "object-list",
                    array_index=i + 1,
                )
                object_list.append(object_identifier)
        except ErrorRejectAbortNack as err:
            sys.stderr.write(
                f"{device_identifier} object-list length error/reject: {err}\n"
            )

        return object_list

    def create_bacnet_object_from_properties(
        self,
        object_class: type,
        property_list: list[tuple],
    ) -> object:
        """Create a BACnet object instance of the given class from a property list."""
        valid_attrs = set(object_class._elements.keys())
        props = {}

        for _, property_identifier, _, value in property_list:
            # BACnet property identifiers have an 'attr' property for the Python attribute name
            attr_name = getattr(property_identifier, "attr", None)
            if not attr_name:
                attr_name = "".join(
                    word.capitalize() if i else word
                    for i, word in enumerate(str(property_identifier).split("-"))
                )
            if attr_name in valid_attrs:
                expected_type = object_class._elements[attr_name]
                try:
                    if value is not None:
                        value = expected_type.cast(value)
                    props[attr_name] = value
                except Exception as err:
                    sys.stderr.write(
                        f"Warning: Could not cast {attr_name}={value!r} to {expected_type}: {err}"
                    )

        return object_class(**props)

    def parseObjects(
        self,
        objects: dict[str, Any],
    ) -> Any:
        """Parse the BACnet objects and return a structured dictionary."""
        return_data = {
            "could_not_parse": {},
            "not_supported": {},
        }
        for (identifier, object_) in objects.items():
            if isinstance(object_, (BinaryValueObject, AnalogValueObject)):
                split_name = re.split(r'\/+', object_.objectName)
                if len(split_name) > 1 and split_name[4] == "S337.01":
                    if return_data.get("heating") is None:
                        return_data["heating"] = {}
                    if return_data["heating"].get(int(split_name[2])) is None:
                        return_data["heating"][int(split_name[2])] = {
                            "current_temp": Any,
                            "current_target_temp": Any,
                            "day_target_temp": Any,
                            "night_target_temp": Any,
                            "night_target_temp_active": Any,
                            "day_control_active": Any,
                            "hand_control_request": Any,
                            "hand_control_influence": Any,
                        }
                    if split_name[5] == "5100":
                        return_data["heating"][int(split_name[2])]["day_target_temp"] = object_.presentValue
                    if split_name[5] == "5101":
                        return_data["heating"][int(split_name[2])]["current_target_temp"] = object_.presentValue
                    if split_name[5] == "5102":
                        return_data["heating"][int(split_name[2])]["current_temp"] = object_.presentValue
                    if split_name[5] == "5107":
                        return_data["heating"][int(split_name[2])]["night_target_temp"] = object_.presentValue
                    if split_name[5] == "5108":
                        return_data["heating"][int(split_name[2])]["night_target_temp_active"] = object_.presentValue
                    if split_name[5] == "5110":
                        return_data["heating"][int(split_name[2])]["hand_control_request"] = object_.presentValue
                    if split_name[5] == "5178":
                        return_data["heating"][int(split_name[2])]["day_control_active"] = object_.presentValue
                    if split_name[5] == "5328":
                        return_data["heating"][int(split_name[2])]["hand_control_influence"] = object_.presentValue
                else:
                    return_data["could_not_parse"][identifier] = object_
            if isinstance(object_, DeviceObject):
                return_data["device"] = object_
            else:
                return_data["not_supported"][identifier] = object_
        return return_data

    async def discoverDevices(
        self, address_with_mask: str = "192.168.1.104/24"
    ) -> list:
        """Discover BACnet devices on the network."""
        app = None
        try:
            # Simulate argparse.Namespace as used in CLI
            args = Namespace(
                address=address_with_mask,
                loggers=False,
                debug=None,
                color=None,
                route_aware=None,
                name="Excelsior",
                instance=999,
                network=0,
                vendoridentifier=999,
                foreign=None,
                ttl=30,
                bbmd=None,
            )
            app = Application.from_args(args)
            devices = []
            # run the query
            i_ams = await app.who_is(0, 1000)
            for i_am in i_ams:
                # print(vars(i_am)) # bacpypes3.apdu.IAmRequest(UnconfirmedRequestPDU) // {'pduSource': <IPv4Address 192.168.1.113>, 'pduDestination': <GlobalBroadcast *:*>, 'pduExpectingReply': False, 'pduNetworkPriority': 0, 'pduUserData': None, 'pduData': bytearray(b''), 'apduType': 1, 'apduService': 0, 'segmentationSupported': <Segmentation: segmented-both>, 'vendorID': 39, 'iAmDeviceIdentifier': (<ObjectType: device>, 13), 'maxAPDULengthAccepted': 480}
                device_address: Address = i_am.pduSource
                device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
                vendor_info = get_vendor_info(i_am.vendorID)

                try:
                    device_description: str = await app.read_property(
                        device_address, device_identifier, "description"
                    )

                except ErrorRejectAbortNack as err:
                    device_description: str = "Unknown"
                    sys.stderr.write(f"{device_identifier} description error: {err}\n")
                devices.append(
                    {
                        "device_address": str(device_address),
                        "device_identifier": str(device_identifier),
                        "vendor_id": i_am.vendorID,
                        "vendor_info": vendor_info,
                        "description": device_description,
                        "maxAPDULengthAccepted": i_am.maxAPDULengthAccepted,
                    }
                )
            return devices  # noqa: TRY300
        except Exception as err:
            print("BACnet discovery failed: %s", err)
            raise ConfigEntryNotReady from err
        finally:
            # ensure the application is stopped
            if app is not None:
                app.close()

    async def getObjects(
        self,
        device_address: Address,
        device_identifier: ObjectIdentifier,
        vendor_id: int,
        address_with_mask: str = "192.168.1.104/24",
    ) -> dict[str, Any]:
        """Get the objects of a BACnet device."""
        app = None
        try:
            # Simulate argparse.Namespace as used in CLI
            args = Namespace(
                address=address_with_mask,
                loggers=False,
                debug=None,
                color=None,
                route_aware=None,
                name="Excelsior",
                instance=999,
                network=0,
                vendoridentifier=999,
                foreign=None,
                ttl=30,
                bbmd=None,
            )
            app = Application.from_args(args)
            print(f"Getting objects for device {device_identifier} at {device_address}")
            object_list = await self.object_identifiers(
                app, device_address, device_identifier
            )
            # print(f"Object list: {object_list}")
            objects = {}
            for object_identifier in object_list:
                object_class = get_vendor_info(
                    vendor_id
                ).get_object_class(object_identifier[0])
                if object_class is None:
                    sys.stderr.write(f"unknown object type: {object_identifier}\n")
                    continue
                print(f"Object: {object_identifier} ({object_class})")

                # read the property list
                property_list: list[PropertyIdentifier] | None = None
                try:
                    property_list = await app.read_property_multiple(
                        device_address, (object_identifier, "8")
                    )

                    objects[str(object_identifier)] = self.create_bacnet_object_from_properties(object_class, property_list)
                except ErrorRejectAbortNack as err:
                    sys.stderr.write(
                        f"{object_identifier} property-list error: {err}\n"
                    )
            return objects
        except Exception as err:
            print("BACnet getObjects failed: %s", err)
            raise ConfigEntryNotReady from err
        finally:
            # ensure the application is stopped
            if app is not None:
                app.close()
