from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN
from .entity import HunonicEntity, parse_value


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
        raise NotImplementedError("Switch control is not enabled yet; MQTT command payload still needs validation.")

    async def async_turn_off(self, **kwargs):
        raise NotImplementedError("Switch control is not enabled yet; MQTT command payload still needs validation.")
