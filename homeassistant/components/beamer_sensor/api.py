"""API client for Epson projectors using ECP/VP.net protocol."""

from __future__ import annotations

import json
from typing import Any

import requests
from requests.auth import HTTPDigestAuth
import urllib3

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

urllib3.disable_warnings()


class EpsonBeamerAPI:
    """API client for Epson projectors."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Initialize the API client."""
        self._host = host
        self._username = username
        self._password = password
        self._base_url = f"https://{self._host}"
        self._hass = hass  # Pass HomeAssistant instance for executor

    def _sync_request(self, command: str) -> dict[str, Any]:
        """Send a command and return the parsed JSON response (sync, for executor)."""
        url = f"{self._base_url}/cgi-bin/json_query?jsoncallback={command}"
        headers = {"Referer": "1"}
        try:
            response = requests.get(
                url,
                auth=HTTPDigestAuth(self._username, self._password),
                headers=headers,
                verify=False,
                timeout=10,
            )
            response.raise_for_status()
            text = response.text
            # print("Raw response:", text)
            # print("Parsed JSON:", json.loads(text))
            return json.loads(text)
        except requests.HTTPError as http_err:
            if response.status_code == 401:
                print("Unauthorized: Invalid credentials")
                raise HomeAssistantError(
                    "Unauthorized: Invalid credentials"
                ) from http_err
            if response.status_code == 404:
                print("Not Found: Invalid command or endpoint")
                raise HomeAssistantError(
                    "Not Found: Invalid command or endpoint"
                ) from http_err
            raise HomeAssistantError(f"HTTP error occurred: {http_err}") from http_err
        except json.JSONDecodeError as json_err:
            print("Failed to parse JSON response:", json_err)
            raise HomeAssistantError(
                f"Failed to parse JSON response: {json_err}"
            ) from json_err
        except requests.RequestException as err:
            raise HomeAssistantError(f"Failed to connect to projector: {err}") from err

    async def _request(self, command: str) -> dict[str, Any]:
        """Async wrapper for the sync request using Home Assistant's executor."""
        if not self._hass:
            raise HomeAssistantError(
                "HomeAssistant instance not set for EpsonBeamerAPI"
            )
        return await self._hass.async_add_executor_job(self._sync_request, command)

    async def get_power_state(self) -> str | None:
        """Get the current power state."""
        data = await self._request("PWR?")
        return data.get("projector", {}).get("feature", {}).get("reply")

    async def get_serial_number(self) -> str | None:
        """Get the current power state."""
        data = await self._request("SNO?")
        return data.get("projector", {}).get("feature", {}).get("reply")

    async def get_name(self) -> str | None:
        """Get the current power state."""
        data = await self._request("IMNWPNAME?")
        return data.get("projector", {}).get("feature", {}).get("reply")

    async def set_power_state(self, state: str) -> None:
        """Set the power state ('ON' or 'OFF')."""
        await self._request(f"PWR%20{state}")

    async def get_source_list(self) -> dict[str, str]:
        """Get available input sources as a mapping of source_id to name."""
        data = await self._request("SOURCELIST?")
        reply = data.get("projector", {}).get("feature", {}).get("reply")
        if not reply or "ERR" in reply:
            return {}
        split_data = reply.split(" ")
        return {
            split_data[i]: split_data[i + 1].replace("^", " ")
            for i in range(0, len(split_data), 2)
        }

    async def get_current_source(self) -> str | None:
        """Get the currently selected source name."""
        source_map = await self.get_source_list()
        data = await self._request("SOURCE?")
        reply = data.get("projector", {}).get("feature", {}).get("reply")
        if not reply or "ERR" in reply:
            return ""
        return source_map.get(reply)

    async def set_source(self, source_id: str) -> None:
        """Set the input source by source_id."""
        await self._request(f"SOURCE%20{source_id}")

    async def check_credentials(self, username: str = "", password: str = "") -> bool:
        """Check if the credentials are valid by making a test request.

        Returns True if credentials are valid, False if unauthorized (error 40).
        Raises HomeAssistantError for other errors.
        """

        print("Checking credentials:", self._host, self._username, self._password)

        if username != "" and password != "":
            self._username = username
            self._password = password

        try:
            await self._request("PWR?")
        except HomeAssistantError as err:
            # Check for HTTP 401 Unauthorized or 'unauthorized' in the error message
            msg = str(err).lower()
            print("Error message:", msg)
            print("Error code:", err)
            if "401" in msg or "unauthorized" in msg:
                return False
            raise
        print("Credentials are valid:", self._username, self._password)
        return True

    def sync_check_connection(self, host) -> bool:
        """Check if the projector is reachable."""

        url = "https://" + host
        print("Checking connection to:", url)

        try:
            requests.get(url, verify=False, timeout=10)
            return True
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError):
            return False
        except Exception:
            return False

    async def check_connection(self, host) -> bool:
        """Check if the projector is reachable."""
        return await self._hass.async_add_executor_job(self.sync_check_connection, host)
