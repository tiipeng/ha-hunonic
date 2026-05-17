from __future__ import annotations

from homeassistant.components.climate import ClimateEntity, HVACMode
from homeassistant.components.climate.const import ClimateEntityFeature
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN
from .entity import HunonicEntity, parse_value

MODE_MAP = {1: HVACMode.DRY, 2: HVACMode.COOL, 4: HVACMode.FAN_ONLY, 8: HVACMode.HEAT, 10: HVACMode.AUTO}
REVERSE_MODE_MAP = {v: k for k, v in MODE_MAP.items()}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = [HunonicClimate(coordinator, entry.entry_id, d["id"]) for d in coordinator.data.get("devices", []) if d.get("type") == "irchild" and "conditioner" in (d.get("name") or "").lower()]
    async_add_entities(entities)


class HunonicClimate(HunonicEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1
    _attr_min_temp = 16
    _attr_max_temp = 30
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.AUTO, HVACMode.COOL, HVACMode.DRY, HVACMode.FAN_ONLY, HVACMode.HEAT]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(self, coordinator, entry_id, device_id):
        super().__init__(coordinator, entry_id, device_id)

    @property
    def name(self):
        return self.device.get("name")

    @property
    def hvac_mode(self):
        value = parse_value(self.device)
        if int(value.get("power", 0)) == 0:
            return HVACMode.OFF
        return MODE_MAP.get(int(value.get("mode", 2)), HVACMode.COOL)

    @property
    def target_temperature(self):
        return parse_value(self.device).get("temp")

    async def async_set_temperature(self, **kwargs):
        raise NotImplementedError("Climate control is not enabled yet; IR MQTT payload still needs validation.")

    async def async_set_hvac_mode(self, hvac_mode):
        raise NotImplementedError("Climate control is not enabled yet; IR MQTT payload still needs validation.")
