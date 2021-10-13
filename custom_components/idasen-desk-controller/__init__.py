"""Idasen Desk Controller integration."""
from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .desk_control import DeskController
from .const import DOMAIN, PLATFORMS


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DeskController from a config entry."""
    controller = DeskController(entry.data["name"], entry.data["address"])
    await controller.start_monitoring()
    hass.data[DOMAIN][entry.entry_id] = controller

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(
                    entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        controller = hass.data[DOMAIN][entry.entry_id]
        await controller.disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
