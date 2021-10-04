"""
Config Flow for Idasen Desk Controller Integration
"""

import time

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryNotReady

import homeassistant.helpers.config_validation as cv

from .const import LOGGER, DOMAIN
from .deskControl import DeskController


class IdasenControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Idasen Desk Controller config flow."""
    def __init__(self):
        """Initialize flow."""
        self._devices = None
        self._id = None
        self._controller = DeskController()

    def _get_entry(self): #TODO
        data = {
            #"address": self.address,
        }
        return self.async_create_entry(
            title=self._title,
            data=data,
        )

    def _testConnection(self):
        """Try to connect and get status"""
        return self._controller.getStatus()

    def _getDevices(self):
        """Scan for devices"""
        self._devices = self._controller.scanDevices()
        return self._devices



    async def async_step_user(self, user_input = None):
        """Invoked when a user initiates a flow via the user interface."""
        if user_input is not None:
                return await self.async_step_connection()
        return self.async_show_form(
            step_id="user", data_schema=None, errors={}
        )

    async def async_step_connection(self, user_input = None):
        """Second step in config flow to connect the desk"""
        errors: Dict[str, str] = {}
        devices = await self.hass.async_add_executor_job(self._getDevices)
        names = devices.keys()
        data_schema = vol.Schema({
                vol.Required("name"): vol.In(names)
        })

        if user_input is not None:
            self._controller.name = user_input.get("name")
            self._controller.address = self._devices[self._controller.name]
            print(self._controller.name)
            print(self._controller.address)

            status = await self.hass.async_add_executor_job(self._testConnection)

            if status == None:
                errors["base"] = "invalid_device"
            if not errors:
                await self.async_set_unique_id(self.address)
                self._abort_if_unique_id_configured()
                return self._get_entry()

        return self.async_show_form(step_id="connection", data_schema=data_schema, errors=errors)
