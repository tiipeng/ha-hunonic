from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .const import DOMAIN
from .entity import HunonicEntity, parse_value


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []
    for d in coordinator.data.get("devices", []):
        value = parse_value(d)
        if d.get("root_type") == "ocswifi" or "warning" in value or "change" in value:
            entities.append(HunonicDoorSensor(coordinator, entry.entry_id, d["id"]))
    async_add_entities(entities)


class HunonicDoorSensor(HunonicEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_name = "Door"

    def __init__(self, coordinator, entry_id, device_id):
        super().__init__(coordinator, entry_id, device_id, "door")

    @property
    def is_on(self):
        # Hunonic door payload currently observed: state 0/1. 1 means open for Tuan's Tattoo Room sample.
        state = parse_value(self.device).get("state")
        return bool(state) if state is not None else None
