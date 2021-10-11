"""Platform for sensor integration."""

from homeassistant.helpers.entity import Entity
from .const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Add sensors for passed config_entry in HA."""
    controller = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([SpeedSensor(controller), HeightSensor(controller)])


class SensorBase(Entity):
    """Base representation of a Sensor."""

    should_poll = False

    def __init__(self, controller):
        """Initialize the sensor."""
        self._controller = controller

    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, self._controller.address)}}

    @property
    def available(self) -> bool:
        """Desk is available"""
        return self._controller.is_available

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._controller.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._controller.remove_callback(self.async_write_ha_state)


class HeightSensor(SensorBase):
    """Representation of a Sensor."""

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return f"{self._controller.address}_height"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._controller.name} Height"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._controller.height

    @property
    def icon(self) -> str:
        """Return the icon of the cover."""
        return "mdi:arrow-expand-vertical"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "mm"


class SpeedSensor(SensorBase):
    """Representation of a Sensor."""

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return f"{self._controller.address}_speed"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._controller.name} Speed"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._controller.speed

    @property
    def icon(self) -> str:
        """Return the icon of the cover."""
        return "mdi:speedometer"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "mm/s"
