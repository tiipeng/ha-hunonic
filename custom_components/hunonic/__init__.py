from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import HunonicClient
from .const import CONF_BASE_URL, CONF_HOME_ID, CONF_TOKEN_ID, DEFAULT_BASE_URL, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


def iter_devices(data: dict[str, Any]):
    for home in data.get("homes", []):
        for room in home.get("rooms", []) or []:
            for device in room.get("devices", []) or []:
                device.setdefault("room_name", room.get("name"))
                yield device


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    client = HunonicClient(session, entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL))
    token_id = entry.data[CONF_TOKEN_ID]
    home_id = entry.data[CONF_HOME_ID]

    async def _async_update_data() -> dict[str, Any]:
        profile = await client.profile(token_id)
        devices = await client.devices(token_id, home_id)
        homes = devices.get("data") or []
        flattened = list(iter_devices({"homes": homes}))
        return {"profile": profile.get("data") or {}, "homes": homes, "devices": flattened}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{entry.entry_id}",
        update_method=_async_update_data,
        update_interval=timedelta(seconds=60),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"client": client, "coordinator": coordinator}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
