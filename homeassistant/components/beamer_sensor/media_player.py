"""Platform for sensor integration."""

from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BeamerSensorConfigEntry
from .api import EpsonBeamerAPI
from .const import DOMAIN

# def setup_platform(
#     hass: HomeAssistant,
#     config: ConfigType,
#     add_entities: AddEntitiesCallback,
#     discovery_info: DiscoveryInfoType | None = None,
# ) -> None:
#     """Set up the sensor platform."""
#     add_entities([BeamerMediaPlayer()])


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BeamerSensorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Beamer from a config entry."""
    entities = []
    unique_id = await config_entry.runtime_data.get_serial_number()
    entities.append(BeamerMediaPlayer(unique_id, config_entry.runtime_data))
    async_add_entities(entities, update_before_add=True)


class BeamerMediaPlayer(MediaPlayerEntity):
    """Representation of an Epson Beamer media player."""

    _attr_name = "Beamer"

    def __init__(self, unique_id, api: EpsonBeamerAPI) -> None:
        """Initialize the media player entity."""
        self._api = api
        self._attr_state = None
        self._attr_unique_id = unique_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": self._attr_name,
            "manufacturer": "Epson",
            # "model": api.get_model_name(),
            # "sw_version": api.get_firmware_version(),
        }
        self._attr_source = None
        self._attr_source_list: list[str] = []
        self.reverse_source_map: dict[str, str] = {}

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added to Home Assistant."""
        await self.async_update()

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features that are supported."""
        return (
            MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.SELECT_SOURCE
        )

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self._api.set_power_state("ON")

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self._api.set_power_state("OFF")

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        if not self.reverse_source_map:
            await self._update_source_list()
        source_id = self.reverse_source_map.get(source)
        if source_id:
            await self._api.set_source(source_id)

    async def async_update(self) -> None:
        """Fetch new state data for the media player."""
        # Update power state
        power_state = await self._api.get_power_state()
        if power_state == "00":
            self._attr_state = MediaPlayerState.OFF
        elif power_state == "01":
            self._attr_state = MediaPlayerState.ON
        elif power_state == "02":
            self._attr_state = "Warmup"
        elif power_state == "03":
            self._attr_state = "Cooldown"
        elif power_state == "04":
            self._attr_state = MediaPlayerState.STANDBY
        else:
            self._attr_state = None

        # Update source list and current source
        await self._update_source_list()
        current_source = await self._api.get_current_source()
        self._attr_source = current_source

    async def _update_source_list(self) -> None:
        """Update the available source list and reverse mapping."""
        source_map = await self._api.get_source_list()
        self.reverse_source_map = {v: k for k, v in source_map.items()}
        self._attr_source_list = list(source_map.values())
