"""API for interacting with BACnet devices in Home Assistant."""

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BACnetAPI

_LOGGER = logging.getLogger(__name__)


class APICoordinator(DataUpdateCoordinator):
    """API call coordinator."""

    def __init__(self, hass: HomeAssistant, config_entry, my_api: BACnetAPI) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="BACnet",
            config_entry=config_entry,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=30),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=True,
        )
        self.my_api = my_api
        self._config_entry = config_entry
        self.data = {}

    async def _async_setup(self):
        """Set up the coordinator.

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        # self._device = await self.my_api.get_device()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""
        print("Updating BACnet data...")
        contexts = self.async_contexts()
        try:
            async with asyncio.timeout(10):
                contexts = self.async_contexts()

                flattened_contexts = []
                for context in contexts:
                    if type(context) is list:
                        flattened_contexts.extend(context)
                    else:
                        flattened_contexts.append(context)

                print(f"Flattened contexts: {flattened_contexts}")

                # Initialize results dict
                results = await self.my_api.getProperties(flattened_contexts)
                print(f"Fetched results: {results}")
                return results

        except Exception as err:
            raise UpdateFailed(f"Error communicating with BACnet device: {err}")
