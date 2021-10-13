"""Platform for switch entity."""
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(hass: HomeAssistant,
                            config_entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    """Add sensors for passed config_entry in HA."""
    controller = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([ConnectionSwitch(controller)])


class ConnectionSwitch(SwitchEntity):

    should_poll = False

    def __init__(self, controller) -> None:
        """Initialize the sensor."""
        self._controller = controller

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self._controller.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        self._controller.remove_callback(self.async_write_ha_state)

    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, self._controller.address)}}

    @property
    def available(self) -> bool:
        """Return True if switch is available."""
        return True

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return f"{self._controller.address}_connection"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._controller.name} Verbindung"

    @property
    def icon(self) -> str:
        """Return the icon of the cover."""
        return "mdi:bluetooth" if self._controller.is_connected else "mdi:bluetooth-off"

    @property
    def is_on(self):
        return self._controller.is_connected

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._controller.disconnect()

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._controller.start_monitoring()
