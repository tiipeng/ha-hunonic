from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature

from .const import DOMAIN
from .entity import HunonicEntity, parse_value


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []
    for d in coordinator.data.get("devices", []):
        value = parse_value(d)
        if "temp" in value:
            entities.append(HunonicValueSensor(coordinator, entry.entry_id, d["id"], "temperature", "temp", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS))
        if "humi" in value:
            entities.append(HunonicValueSensor(coordinator, entry.entry_id, d["id"], "humidity", "humi", SensorDeviceClass.HUMIDITY, PERCENTAGE))
        for key in ("batt_percent", "bat_pcn"):
            if key in value:
                entities.append(HunonicValueSensor(coordinator, entry.entry_id, d["id"], "battery", key, SensorDeviceClass.BATTERY, PERCENTAGE))
        if d.get("type") == "switch" and "turn" in value:
            entities.append(HunonicTextSensor(coordinator, entry.entry_id, d["id"], "switch_state", "turn", {1: "on", 2: "off"}))
        if d.get("type") == "irchild" and "conditioner" in (d.get("name") or "").lower():
            if "power" in value:
                entities.append(HunonicTextSensor(coordinator, entry.entry_id, d["id"], "ac_power", "power", {0: "off", 1: "on"}))
            if "temp" in value:
                entities.append(HunonicValueSensor(coordinator, entry.entry_id, d["id"], "target_temperature", "temp", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS))
    async_add_entities(entities)


class HunonicValueSensor(HunonicEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry_id, device_id, name, key, device_class, unit):
        super().__init__(coordinator, entry_id, device_id, name)
        self._attr_translation_key = name
        self._attr_name = name.replace("_", " ").title()
        self.key = key
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        return parse_value(self.device).get(self.key)


class HunonicTextSensor(HunonicEntity, SensorEntity):
    def __init__(self, coordinator, entry_id, device_id, name, key, mapping=None):
        super().__init__(coordinator, entry_id, device_id, name)
        self._attr_name = name.replace("_", " ").title()
        self.key = key
        self.mapping = mapping or {}

    @property
    def native_value(self):
        value = parse_value(self.device).get(self.key)
        return self.mapping.get(value, self.mapping.get(str(value), value))
