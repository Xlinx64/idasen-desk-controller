"""
Config Flow for Idasen Desk Controller Integration
"""

import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from .const import LOGGER, DOMAIN
from .desk_control import DeskController


class IdasenControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Idasen Desk Controller config flow."""

    def __init__(self):
        """Initialize flow."""
        self._found_devices = None
        self._id = None
        self._controller = DeskController()

    def _get_entry(self):
        data = {
            "name": self._controller.name,
            "address": self._controller.address
        }
        return self.async_create_entry(
            title=self._controller.name,
            data=data,
        )

    def _test_connection(self):
        """Try to connect and get height"""
        return self._controller.check_Connection()

    def _scan_devices(self):
        """Scan for devices"""
        self._found_devices = self._controller.scan_devices()
        return self._found_devices

    def _get_scanned_device_names(self):
        return self._scan_devices().keys()

    async def async_step_user(self, user_input=None):
        """Invoked when a user initiates a flow via the user interface."""
        errors = {}

        if user_input is not None:
            device_names = await self.hass.async_add_executor_job(self._get_scanned_device_names)
            if len(device_names) > 0:
                return await self.async_step_connection()
            errors["base"] = "no_devices_found"
        return self.async_show_form(
            step_id="user", data_schema=None, errors=errors
        )

    async def async_step_connection(self, user_input=None):
        """Second step in config flow to connect the desk"""
        errors = {}

        if user_input is not None:
            self._controller.name = user_input.get("name")
            self._controller.address = self._found_devices[self._controller.name]
            print(self._controller.name)
            print(self._controller.address)

            height = await self.hass.async_add_executor_job(self._test_connection)
            print(f"HEIGHT: {height}")
            if height is None:
                errors["base"] = "invalid_device"
            if not errors:
                await self.async_set_unique_id(self._controller.address)
                self._abort_if_unique_id_configured()
                return self._get_entry()
            await self.hass.async_add_executor_job(self._get_scanned_device_names)

        data_schema = vol.Schema({
                vol.Required("name"): vol.In(self._found_devices.keys())
        })

        return self.async_show_form(step_id="connection", data_schema=data_schema, errors=errors)
