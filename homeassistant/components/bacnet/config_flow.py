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
        self.discovered_devices: list[dict[str, str | None]] = []

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            api = BACnetAPI()
            self.discovered_devices = await api.discoverDevices("192.168.1.104", 47808)
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
        # If no devices are discovered, show the IP field
        # and make username and password optional
        return vol.Schema({vol.Optional("ip"): str})
