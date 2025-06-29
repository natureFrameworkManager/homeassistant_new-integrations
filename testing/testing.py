"""Simple example that sends a Who-Is request and prints out the device identifier,
address, and description for the devices that respond.
"""

import asyncio
import sys

from bacpypes3.apdu import AbortPDU, AbortReason, ErrorRejectAbortNack
from bacpypes3.app import Application
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.debugging import ModuleLogger, bacpypes_debugging
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier, PropertyIdentifier
from bacpypes3.vendor import get_vendor_info
from bacpypes3.object import BinaryValueObject

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
show_warnings: bool = True

@bacpypes_debugging
async def object_identifiers(
    app: Application, device_address: Address, device_identifier: ObjectIdentifier
) -> list[ObjectIdentifier]:
    """Read the entire object list from a device at once, or if that fails, read
    the object identifiers one at a time.
    """

    # try reading the whole thing at once, but it might be too big and
    # segmentation isn't supported
    try:
        object_list = await app.read_property(
            device_address, device_identifier, "object-list"
        )
        return object_list
    except AbortPDU as err:
        if err.apduAbortRejectReason != AbortReason.segmentationNotSupported:
            if show_warnings:
                sys.stderr.write(f"{device_identifier} object-list abort: {err}\n")
            return []
    except ErrorRejectAbortNack as err:
        if show_warnings:
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
        if show_warnings:
            sys.stderr.write(
                f"{device_identifier} object-list length error/reject: {err}\n"
            )

    return object_list


def create_bacnet_object_from_properties(
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
                if show_warnings:
                    print(
                        f"Warning: Could not cast {attr_name}={value!r} to {expected_type}: {err}"
                    )

    return object_class(**props)


def get_set_properties(obj: object) -> dict[str, object]:
    """Return a dict of all set (non-None) properties for a BACnet object."""
    # BACpypes3 objects have _elements with property names
    return {
        attr: getattr(obj, attr)
        for attr in obj._elements.keys()
        if getattr(obj, attr, None) is not None
    }

async def main() -> None:
    app = None
    try:
        parser = SimpleArgumentParser()
        parser.add_argument(
            "low_limit",
            type=int,
            help="device instance range low limit",
        )
        parser.add_argument(
            "high_limit",
            type=int,
            help="device instance range high limit",
        )
        args = parser.parse_args()
        if _debug:
            _log.debug("args: %r", args)

        # build an application
        app = Application.from_args(args)
        print(args)
        if _debug:
            _log.debug("app: %r", app)

        # run the query
        i_ams = await app.who_is(args.low_limit, args.high_limit)
        for i_am in i_ams:
            if _debug:
                _log.debug("    - i_am: %r", i_am)

            device_address: Address = i_am.pduSource
            device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
            vendor_info = get_vendor_info(i_am.vendorID)
            print(f"{device_identifier} @ {device_address}")

            try:
                device_description: str = await app.read_property(
                    device_address, device_identifier, "description"
                )
                print(f"    description: {device_description}")

            except ErrorRejectAbortNack as err:
                if show_warnings:
                    sys.stderr.write(f"{device_identifier} description error: {err}\n")
            object_list = await object_identifiers(app, device_address, device_identifier)
            for object_identifier in object_list:
                object_class = vendor_info.get_object_class(object_identifier[0])
                if _debug:
                    _log.debug("    - object_class: %r", object_class)
                if object_class is None:
                    if show_warnings:
                        sys.stderr.write(f"unknown object type: {object_identifier}\n")
                    continue

                print(f"    {object_identifier}:")

                # read the property list
                property_list: list[PropertyIdentifier] | None = None
                try:
                    property_list = await app.read_property_multiple(
                        device_address, (object_identifier, "8")
                    )
                    object_object = (create_bacnet_object_from_properties(object_class, property_list))
                    if hasattr(object_object, "presentValue") and False:
                        print(f"      object_present_value: {object_object.presentValue}")
                    print(f"    set properties: {get_set_properties(object_object)}")
                    for property in object_class._required + ("objectName", "objectType", "description"):
                        if hasattr(object_object, property):
                            value = getattr(object_object, property)
                            if value is not None:
                                print(f"      {property}: {value}")
                        else:
                            if show_warnings:
                                sys.stderr.write(
                                    f"Warning: {object_identifier} missing required property: {property}\n"
                                )
                    if object_class is BinaryValueObject:
                        object_class._required

                    # property: (ObjectIdentifier, PropertyIdentifier, int | None, str | int | None)
                    # for property in property_list:
                    #     print(f"    - {property[1]}: {property[3]}")
                    # if _debug:
                    #     _log.debug("    - property_list: %r", property_list)
                except ErrorRejectAbortNack as err:
                    if show_warnings:
                        sys.stderr.write(
                            f"{object_identifier} property-list error: {err}\n"
                        )
    finally:
        if app:
            app.close()


if __name__ == "__main__":
    asyncio.run(main())
