"""Platform for cover entity."""

from typing import Any

from homeassistant.components.cover import (ATTR_POSITION, SUPPORT_CLOSE,
                                            SUPPORT_OPEN, SUPPORT_SET_POSITION,
                                            SUPPORT_STOP, CoverEntity)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MIN_HEIGHT, MAX_HEIGHT


async def async_setup_entry(hass: HomeAssistant,
                            config_entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback
                            ) -> None:
    """Add cover for passed config_entry in HA."""
    controller = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([DeskCover(controller)])


class DeskCover(CoverEntity):
    """Representation of the desk as a cover"""

    should_poll = False
    supported_features = SUPPORT_SET_POSITION | SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP

    def __init__(self, controller) -> None:
        """Initialize the cover."""
        self._controller = controller

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self._controller.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        self._controller.remove_callback(self.async_write_ha_state)

    @property
    def unique_id(self) -> str:
        """Return Unique ID string."""
        return f"{self._controller.address}_cover"

    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self._controller.address)},
            "name": self.name,
            #"sw_version": self._roller.firmware_version,
            "model": "Idasen",
            "manufacturer": "IKEA/LINAK",
        }

    @property
    def name(self) -> str:
        """Return the name of the desk."""
        return self._controller.name

    @property
    def available(self) -> bool:
        """Return True if desk is available."""
        return self._controller.is_connected

    @property
    def icon(self) -> str:
        """Return the icon of the cover."""
        return "mdi:desk"

    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return self._controller.height_percentage

    @property
    def is_closed(self) -> bool:
        """Return if the cover is closed, same as position 0."""
        return self._controller.is_on_lowest

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing or not."""
        return self._controller.speed < 0

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening or not."""
        return self._controller.speed > 0

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        print("stop cover")
        await self._controller.stop_movement()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self._controller.move_to_position(MAX_HEIGHT)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self._controller.move_to_position(MIN_HEIGHT)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self._controller.move_to_position(kwargs[ATTR_POSITION])
