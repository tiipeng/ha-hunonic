from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN
from .entity import HunonicEntity, parse_value
from .api import publish_switch_command


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = [HunonicSwitch(coordinator, entry.entry_id, d["id"]) for d in coordinator.data.get("devices", []) if d.get("type") == "switch"]
    async_add_entities(entities)


class HunonicSwitch(HunonicEntity, SwitchEntity):
    def __init__(self, coordinator, entry_id, device_id):
        super().__init__(coordinator, entry_id, device_id)

    @property
    def name(self):
        return self.device.get("name")

    @property
    def is_on(self):
        # Observed Hunonic switch value: {"turn": 1/2}; 1 appears on, 2 appears off.
        turn = parse_value(self.device).get("turn")
        if turn is None:
            return None
        return int(turn) == 1

    async def async_turn_on(self, **kwargs):
        await self._async_publish_switch(True)

    async def async_turn_off(self, **kwargs):
        await self._async_publish_switch(False)

    async def _async_publish_switch(self, turn_on: bool) -> None:
        profile = self.coordinator.data.get("profile", {})
        user_id = profile.get("id") or profile.get("user_id")
        await self.hass.async_add_executor_job(publish_switch_command, self.device, int(user_id), turn_on)
        await self.coordinator.async_request_refresh()
