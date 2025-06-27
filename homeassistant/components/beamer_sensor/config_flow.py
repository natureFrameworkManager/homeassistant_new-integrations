"""Config flow for Beamer Sensor integration."""

from __future__ import annotations

import socket
import time
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .api import EpsonBeamerAPI
from .const import DOMAIN


class BeamerSensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Beamer Sensor."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self.host: str | None = None
        self.name: str | None = None
        self.username: str | None = None
        self.password: str | None = None
        self.discovered_devices: list[dict[str, str | None]] = []

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            print("User input:", user_input)
            if user_input.get("ip") is not None:
                self.host = user_input["ip"]
                if not await self.async_check_connection():
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._get_schema(),
                        errors={"base": "connot_connect"},
                    )
            if user_input.get("username") is not None:
                self.username = user_input["username"]
            if user_input.get("password") is not None:
                self.password = user_input["password"]

            if (
                user_input.get("ip") is not None
                and user_input.get("username") is not None
                and user_input.get("password") is not None
            ):
                api = EpsonBeamerAPI(
                    self.host,
                    self.username,
                    self.password,
                    self.hass,
                )
                if not await api.check_credentials():
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._get_schema(),
                        errors={"base": "invalid_auth"},
                    )

                serial = await api.get_serial_number()
                print("Got Serial number:", serial)
                if serial is not None:
                    unique_id = serial
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                if self.name is None:
                    self.name = await api.get_name()
                # Create the config entry
                return self.async_create_entry(
                    title=self.name,
                    data={
                        "ip": self.host,
                        "username": self.username,
                        "password": self.password,
                        "serial_number": serial,
                        "api": api,
                    },
                )

            if user_input.get("ip") is not None and (
                user_input.get("username") is None or user_input.get("password") is None
            ):
                # Check if the default credentials are available
                if not await self.async_check_default_credentials():
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._get_schema(),
                        errors={"base": "invalid_auth"},
                    )
                print("Default credentials are available")
                print("username:", self.username, "password:", self.password)
                api = EpsonBeamerAPI(
                    self.host,
                    self.username,
                    self.password,
                    self.hass,
                )
                serial = await api.get_serial_number()
                print("Got Serial number:", serial)
                if serial is not None:
                    unique_id = serial
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                if self.name is None:
                    self.name = await api.get_name()
                # Create the config entry
                return self.async_create_entry(
                    title=self.name,
                    data={
                        "ip": self.host,
                        "username": self.username,
                        "password": self.password,
                        "serial_number": serial,
                        "api": api,
                    },
                )

            self.discovered_devices = discover()
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

    async def async_check_default_credentials(self) -> bool:
        """Check if the default connection is available."""
        assert self.host
        api = EpsonBeamerAPI(
            self.host,
            self.username,
            self.password,
            self.hass,
        )
        if not await api.check_credentials("EPSONWEB", "12345678"):
            if not await api.check_credentials("EPSONWEB", "admin"):
                if not await api.check_credentials("EPSONWEB", "1234"):
                    return False
        self.username = api._username
        self.password = api._password
        return True

    async def async_check_connection(self) -> bool:
        """Check if the connection is available."""
        assert self.host
        api = EpsonBeamerAPI("", "", "", self.hass)
        return await api.check_connection(self.host)

    async def async_step_connect(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Connect to the receiver."""
        assert self.host
        api = EpsonBeamerAPI(
            self.host,
            self.username,
            self.password,
            self.hass,
        )
        # Validate the API connection (and authentication)
        if not await api.check_credentials("EPSONWEB", "12345678"):
            if not await api.check_credentials("EPSONWEB", "admin"):
                if not await api.check_credentials("EPSONWEB", "1234"):
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._get_schema(),
                        errors={"base": "invalid_auth"},
                    )
        serial = await api.get_serial_number()
        print("Got Serial number:", serial)
        if serial is not None:
            unique_id = serial
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
        # Create the config entry
        return self.async_create_entry(
            title=self.name,
            data={
                "ip": self.host,
                "username": self.username,
                "password": self.password,
                "serial_number": serial,
                "api": api,
            },
        )

    @callback
    def _get_schema(self):
        """Return the data schema for the config flow."""

        if self.discovered_devices is not None and len(self.discovered_devices) > 0:
            return vol.Schema(
                {
                    vol.Required("ip"): vol.In(
                        {
                            device["ip"]: device["projector_id"]
                            for device in self.discovered_devices
                        }
                    ),
                    vol.Optional("username", default="EPSONWEB"): str,
                    vol.Optional("password"): str,
                }
            )
        # If no devices are discovered, show the IP field
        # and make username and password optional
        return vol.Schema(
            {
                vol.Optional("ip"): str,
                vol.Optional(
                    "username", description={"suggested_value": "EPSONWEB"}
                ): str,
                vol.Optional("password"): str,
            }
        )


def discover(
    timeout: float = 2.0,
    broadcast_ip: str = "10.1.255.255",
    port: int = 3629,
    local_ip: str = "0.0.0.0",
) -> list[dict[str, str | None]]:
    """Discover Epson beamers on the network via UDP broadcast.

    Args:
        timeout: How many seconds to wait for responses.
        broadcast_ip: Broadcast address to send the discovery packet.
        port: UDP port to use.
        local_ip: Optional local IP to bind to.

    Returns:
        List of dicts with keys: 'ip', 'projector_id'.

    """

    hex_array = [
        0x45,
        0x53,
        0x43,
        0x2F,
        0x56,
        0x50,
        0x2E,
        0x6E,
        0x65,
        0x74,
        0x10,
        0x01,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
    message = bytes(hex_array)
    responses: list[dict[str, str | None]] = []

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        sock.bind((local_ip, port))
        sock.sendto(message, (broadcast_ip, port))

        print("Sending discovery packet:", " ".join(f"{b:02x}" for b in message))
        print("ASCII:", message.decode("ascii", errors="replace"))
        print("Broadcasting to:", broadcast_ip, ":", port)
        print("Binding to local IP:", local_ip, ":", port)
        print("Timeout:", timeout)

        start = time.monotonic()
        seen_ips = set()
        while time.monotonic() - start < timeout:
            try:
                data, addr = sock.recvfrom(4096)
                ip = addr[0]
                if ip in seen_ips:
                    continue
                if len(data) >= 23:
                    seen_ips.add(ip)
                    projector_id = (
                        data[18:23]
                        .decode("ascii", errors="replace")
                        .replace("\x00", "")
                    )
                    responses.append({"ip": ip, "projector_id": projector_id})
            except TimeoutError:
                break
        responses.append({"ip": "10.1.195.1", "projector_id": "EB205"})
    print("Discovered devices:", responses.__len__())
    return responses
