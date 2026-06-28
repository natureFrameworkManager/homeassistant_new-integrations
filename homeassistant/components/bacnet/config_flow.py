"""Config flow for the bacnet integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import selector

from .api import BACnetAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for bacnet."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise Class."""
        self.objects = {}
        self.next_entity = None
        self.api = BACnetAPI()
        self.devices = []
        self.device = None
        self.create_entities = {}

    def _get_user_schema(self):
        options = []
        for device in self.devices:
            options.append(device["device_address"])
        options.sort()
        return vol.Schema(
            {
                vol.Required("ip"): selector(
                    {
                        "select": {"custom_value": True, "options": options},
                    }
                ),
            }
        )

    def _get_add_entity_schema(self):
        return vol.Schema(
            {
                vol.Optional("text"): selector(
                    {
                        "constant": {
                            "value": True,
                            "label": "Host: " + str(self.device["device_address"]),
                        }
                    }
                ),
                vol.Optional("entity_type", default="finish"): vol.In(
                    {
                        "sensor": "Analog Sensor",
                        "binary_sensor": "Binary Sensor",
                        "climate_h": "Heating",
                        "finish": "Finish Setup",
                    }
                ),
            }
        )

    def _get_heating_entity_schema(self):
        options = {}
        for object_name in self.objects:
            object_instance = self.objects[object_name]
            if (
                hasattr(object_instance, "description")
                and hasattr(object_instance, "objectName") is not None
            ):
                options[object_name] = (
                    str(object_instance.description)
                    + " - "
                    + str(object_instance.objectName)
                )

            elif hasattr(object_instance, "description") is not None:
                options[object_name] = str(object_instance.description)
            else:
                options[object_name] = str(object_instance.objectName)
        return vol.Schema(
            {
                vol.Optional("text"): selector(
                    {
                        "constant": {
                            "value": True,
                            "label": "Host: " + str(self.device["device_address"]),
                        }
                    }
                ),
                vol.Required("name"): str,
                vol.Required("current_temperature"): vol.In(
                    dict(sorted(options.items(), key=lambda item: item[1]))
                ),
                vol.Required("target_temperature"): vol.In(
                    dict(sorted(options.items(), key=lambda item: item[1]))
                ),
            }
        )

    STEP_CONFIG_BINARY_ENTITY_SCHEMA = vol.Schema(
        {
            vol.Optional("text"): selector(
                {"constant": {"value": True, "label": "Host: 192.168.1.112"}}
            ),
            vol.Required("name"): str,
            vol.Required("is_on"): selector(
                {
                    "select": {
                        "options": [
                            "Option 1",
                            "Option 2",
                            "Option 3",
                            "Option 4",
                            "Option 5",
                            "Option 6",
                        ],
                    },
                }
            ),
            vol.Required("device_class", default="none"): selector(
                {
                    "select": {
                        "options": [
                            "none",
                            "Option 2",
                            "Option 3",
                            "Option 4",
                            "Option 5",
                            "Option 6",
                        ],
                    },
                }
            ),
        }
    )

    STEP_CONFIG_ANALOG_ENTITY_SCHEMA = vol.Schema(
        {
            vol.Optional("text"): selector(
                {"constant": {"value": True, "label": "Host: 192.168.1.112"}}
            ),
            vol.Required("name"): str,
            vol.Required("native_value"): selector(
                {
                    "select": {
                        "options": [
                            "Option 1",
                            "Option 2",
                            "Option 3",
                            "Option 4",
                            "Option 5",
                            "Option 6",
                        ],
                    },
                }
            ),
            vol.Required("device_class", default="none"): selector(
                {
                    "select": {
                        "options": [
                            "none",
                            "Option 2",
                            "Option 3",
                            "Option 4",
                            "Option 5",
                            "Option 6",
                        ],
                    },
                }
            ),
        }
    )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            print(f"User input received: {user_input}")
            self.device = await self.api.discoverDevices(user_input["ip"])
            if len(self.device) > 0:
                self.device = self.device[0]
                print(self.device)
                self.objects = await self.api.getObjects(
                    self.device["device_address"],
                    self.device["device_identifier"],
                    self.device["vendor_id"],
                )
                print(self.objects)

                return self.async_show_form(
                    step_id="add_entity",
                    data_schema=self._get_add_entity_schema(),
                    errors=errors,
                )
            else:
                errors["base"] = "cannot_connect"

        self.devices = await self.api.discoverDevices()
        print(self.devices)
        return self.async_show_form(
            step_id="user", data_schema=self._get_user_schema(), errors=errors
        )

    async def async_step_add_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle Adding new Entity."""
        errors: dict[str, str] = {}

        if user_input is not None:
            print(f"User input received: {user_input}")
            if user_input.get("entity_type") is not None:
                self.next_entity = user_input.get("entity_type")
                if self.next_entity == "climate_h":
                    return self.async_show_form(
                        step_id="config_entity",
                        data_schema=self._get_heating_entity_schema(),
                        errors=errors,
                    )
                if self.next_entity == "binary_sensor":
                    return self.async_show_form(
                        step_id="config_entity",
                        data_schema=self.STEP_CONFIG_BINARY_ENTITY_SCHEMA,
                        errors=errors,
                    )
                if self.next_entity == "sensor":
                    return self.async_show_form(
                        step_id="config_entity",
                        data_schema=self.STEP_CONFIG_ANALOG_ENTITY_SCHEMA,
                        errors=errors,
                    )
                if self.next_entity == "finish":
                    print(f"Create Entities: {self.create_entities}")
                    self.device["vendor_info"] = ""
                    return self.async_create_entry(
                        title="self.device_identifier",
                        data={
                            "entities": self.create_entities,
                            "device": self.device,
                        },
                    )
        return self.async_show_form(
            step_id="add_entity",
            data_schema=self._get_add_entity_schema(),
            errors=errors,
        )

    async def async_step_config_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle Adding new Entity."""
        errors: dict[str, str] = {}

        if user_input is not None:
            print(f"User input received: {user_input}")
            print(f"Entity: {self.next_entity}")
            if self.create_entities.get(self.next_entity) is None:
                self.create_entities[self.next_entity] = []
            self.create_entities[self.next_entity].append(user_input)
            return self.async_show_form(
                step_id="add_entity",
                data_schema=self._get_add_entity_schema(),
                errors=errors,
            )

        return self.async_show_form(
            step_id="config_entity",
            data_schema=self._get_add_entity_schema(),
            errors=errors,
        )
