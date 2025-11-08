"""The bacnet integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import BACnetAPI
from .coordinator import APICoordinator

_PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR, Platform.BINARY_SENSOR]
type BACnetConfigEntry = ConfigEntry[BACnetAPI]

apis = {}
apiCoordinators = {}


async def async_setup_entry(hass: HomeAssistant, entry: BACnetConfigEntry) -> bool:
    """Set up bacnet from a config entry."""

    # TODO 1. Create API instance
    # TODO 2. Validate the API connection (and authentication)
    # TODO 3. Store an API object for your platforms to access
    # entry.runtime_data = MyAPI(...)

    print(f"Create Entries: {entry.data}")
    if apis.get(entry.data["own_ip"]) is None:
        apis[entry.data["own_ip"]] = BACnetAPI(entry.data["own_ip"])
    if apiCoordinators.get(entry.data["own_ip"]) is None:
        apiCoordinators[entry.data["own_ip"]] = APICoordinator(
            hass,
            entry,
            apis[entry.data["own_ip"]],
        )
        await apiCoordinators[entry.data["own_ip"]].async_config_entry_first_refresh()
    print(f"{entry.data['device']}")
    print(f"{entry.data['device']['device_address']}")
    print(f"{entry.data['device']['device_identifier']}")
    entry.runtime_data = {}
    entry.runtime_data["api_coordinator"] = apiCoordinators.get(entry.data["own_ip"])
    entry.runtime_data["device_obj"] = await apis.get(entry.data["own_ip"]).getDevice(
        entry.data["device"]["device_address"],
        entry.data["device"]["device_identifier"],
    )
    print(f"Device: {entry.runtime_data}")
    print(f"APIs: {apis.keys()}")
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BACnetConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
