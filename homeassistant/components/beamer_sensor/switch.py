"""Platform for sensor integration."""

from __future__ import annotations

from typing import Any

import requests
from requests.auth import HTTPDigestAuth

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    add_entities([BeamerPowerSwitch()])


class BeamerPowerSwitch(SwitchEntity):
    """Representation of a Sensor."""

    _attr_name = "Beamer Power"
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_is_on = False

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        # self._attr_state = "warmup"
        url = "https://10.1.195.1/cgi-bin/json_query?jsoncallback=PWR?"
        user = "EPSONWEB"
        password = "12345678"
        request = requests.get(
            url,
            auth=HTTPDigestAuth(user, password),
            verify=False,
            headers={"Referer": "1"},
            timeout=10,
        )
        if request.status_code == 200:
            state = request.json()["projector"]["feature"]["reply"]
            if state in {"00", "04"}:
                self.is_on = False
            elif state in {"01", "02", "03"}:
                self.is_on = True
            else:
                self.is_on = False

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        url = "https://10.1.195.1/cgi-bin/json_query?jsoncallback=PWR%20ON"
        user = "EPSONWEB"
        password = "12345678"
        requests.get(
            url,
            auth=HTTPDigestAuth(user, password),
            verify=False,
            headers={"Referer": "1"},
            timeout=10,
        )

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        url = "https://10.1.195.1/cgi-bin/json_query?jsoncallback=PWR%20OFF"
        user = "EPSONWEB"
        password = "12345678"
        requests.get(
            url,
            auth=HTTPDigestAuth(user, password),
            verify=False,
            headers={"Referer": "1"},
            timeout=10,
        )
