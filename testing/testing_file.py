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

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
show_warnings: bool = True

@bacpypes_debugging

async def main() -> None:
    app = None
    try:
        parser = SimpleArgumentParser()

        args = parser.parse_args()
        if _debug:
            _log.debug("args: %r", args)

        # build an application
        app = Application.from_args(args)
        print(args)

        if _debug:
            _log.debug("app: %r", app)

        device_identifier = "device,12"
        device_address = "192.168.1.112"

        print(f"{device_identifier} @ {device_address}")

        try:
            device_description: str = await app.read_property(
                device_address, "file, 1000002", "all"
            )
            print(f"    description: {device_description}")

        except ErrorRejectAbortNack as err:
            sys.stderr.write(f"{device_identifier} description error: {err}\n")

    finally:
        if app:
            app.close()


if __name__ == "__main__":
    asyncio.run(main())
