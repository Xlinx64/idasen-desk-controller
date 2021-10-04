"""
Config Flow for Linak DPG Desk Panel Integration
"""

import time

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryNotReady

import homeassistant.helpers.config_validation as cv

from .const import LOGGER, DOMAIN
from .deskControl import DeskController




class LinakDPGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Linak DPG config flow."""
    def __init__(self):
        """Initialize flow."""
        self._devices = None
        self._name = None
        self._address = None
        self._id = None

    def _get_entry(self): #TODO
        data = {
            "address": self._address,
            "id": self._id,
            "name": self._name
        }

        return self.async_create_entry(
            title=self._title,
            data=data,
        )

    def _getDevices(self):
        """Try to connect."""
        self._devices = DeskController().scanDevices()
        return self._devices

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            if len(user_input["name"]) < 3:
                raise Exception(f"Name must be atleast 3 characteres.")

            self._name = user_input.get("name")
            self._address = self._devices[self._name]
            await self.async_set_unique_id(self._address)
            self._abort_if_unique_id_configured()

            print(self._name)
            print(self._address)
            if False != True:
                raise Exception(f"HAHAH")
                return self.async_abort(reason=result)
            return self._get_entry()

        devices = await self.hass.async_add_executor_job(self._getDevices)
        names = devices.keys()
        data_schema = vol.Schema({
                vol.Required("name"): vol.In(names)
        })
        return self.async_show_form(step_id="user", data_schema=data_schema)
