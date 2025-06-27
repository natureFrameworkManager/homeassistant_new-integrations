"""The Beamer Sensor integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import EpsonBeamerAPI
from .const import DOMAIN

_PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]

# ConfigEntry type alias with API object
type BeamerSensorConfigEntry = ConfigEntry[EpsonBeamerAPI]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Beamer Sensor from a config entry."""
    print("creating entry", entry.data)
    # Create API instance
    host = entry.data.get("ip", "10.1.195.1")
    username = entry.data.get("username", "EPSONWEB")
    password = entry.data.get("password", "12345678")

    # Pass hass to EpsonBeamerAPI for executor use
    api = entry.data.get("api", EpsonBeamerAPI(host, username, password, hass))

    # Validate the API connection (and authentication)
    try:
        # Try to fetch the power state as a connectivity check
        print("test powerstate: ", await api.get_power_state())
    except Exception as err:
        raise ConfigEntryNotReady from err

    # Store the API object for platforms to access
    entry.runtime_data = api

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
