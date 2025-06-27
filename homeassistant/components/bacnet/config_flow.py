"""Config flow for the bacnet integration."""

from .api import BACnetAPI

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_flow

from .const import DOMAIN


class BacnetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Bacnet."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self.address: str | None = None
        self.device_identifier: str | None = None
        self.discovered_devices: list[dict[str, str | None]] = []

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            if user_input.get("ip") is not None:
                self.address = user_input["ip"].split("-")[0]
                self.device_identifier = user_input["ip"].split("-")[1]
                self.vendor_id = user_input["ip"].split("-")[2]
                api = BACnetAPI()
                objects = await api.getObjects(
                    self.address, self.device_identifier, self.vendor_id
                )
                print("BACnet objects:", objects)
                serial = self.device_identifier
                if serial is not None:
                    unique_id = serial
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                # Create the config entry
                return self.async_create_entry(
                    title=self.device_identifier,
                    data={
                        "objects": objects,
                        "device_address": self.address,
                        "device_identifier": self.device_identifier,
                        "vendor_id": self.vendor_id,
                        "serial_number": serial,
                    },
                )
            api = BACnetAPI()
            self.discovered_devices = await api.discoverDevices()
            print("Discovered devices:", self.discovered_devices)
            if len(self.discovered_devices) > 1:
                # show selection form
                return self.async_show_form(
                    step_id="user", data_schema=self._get_schema(), errors=errors
                )
            errors["base"] = "discovery_error"

        return self.async_show_form(
            step_id="user", data_schema=self._get_schema(), errors=errors
        )

    @callback
    def _get_schema(self):
        """Return the data schema for the config flow."""

        if self.discovered_devices is not None and len(self.discovered_devices) > 0:
            return vol.Schema(
                {
                    vol.Required("ip"): vol.In(
                        {
                            device["device_address"]
                            + "-"
                            + device["device_identifier"]
                            + "-"
                            + str(device["vendor_id"]): device["description"]
                            + " ("
                            + device["device_address"]
                            + ")"
                            for device in self.discovered_devices
                        }
                    )
                }
            )
        # If no devices are discovered, show the IP field
        # and make username and password optional
        return vol.Schema({vol.Optional("ip"): str})
