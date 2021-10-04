"""
Platform for Idasen Desk Controller Integration
"""

import random

from homeassistant.helpers.entity import Entity
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
)

from .const import (
    DOMAIN,
    LOGGER,
    HEIGHT_CHAR_ID
)
from .btctl import BTctl

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Linak DPG Desk from a config entry."""

    async_add_entities([DeskSensor(config_entry)])

class DeskSensor(Entity):
    """Representation of Height Sensor for Linak Desk."""

    def __init__(self, config_entry):
        """Initialize the Linak DPG desk."""
        self._config_entry = config_entry
        self._name = config_entry.data.get("name")
        self._uuid = config_entry.data.get("id")
        self._address = config_entry.data.get("address")
        self._state = STATE_OFF
        self._height = None
        self._offset = 70
        self._unit_of_measurement = "cm"

    def update(self):
        """Update state of the device."""
        try:
            wrapper = BTctl()
            wrapper.connect(self._address)

            if wrapper.gatt():
                output = wrapper.attribute_read_value(HEIGHT_CHAR_ID)

        except:
            self._state = STATE_OFF

        else:
            if output:
                hex_arr = []

                for value in output[-1].split(" "):
                    if value.strip():
                        if not value.endswith("..."):
                            hex_arr.append(value)

                better_arr = " ".join(hex_arr).encode()

                val = BTctl().convertHexStr(better_arr[0:5])

                if val:
                    self._state = float(val) / 100
                    self._height = self._state + self._offset

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the device."""
        return self._uuid

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def offset(self):
        """Return the offset of the device."""
        return self._offset

    @property
    def address(self):
        """Return the address of the device."""
        return self._address

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attr = {}
        attr["height"] = self._height
        attr["offset"] = self._offset
        attr["unit_of_measurement"] = self._unit_of_measurement
        attr["mac_address"] = self._address

        return attr
