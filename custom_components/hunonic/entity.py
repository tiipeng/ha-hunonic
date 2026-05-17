from __future__ import annotations

import json
from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


def parse_value(device: dict[str, Any]) -> dict[str, Any]:
    value = device.get("value")
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            return {}
    return {}


class HunonicEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id: str, device_id: str, suffix: str | None = None) -> None:
        super().__init__(coordinator)
        self.entry_id = entry_id
        self.device_id = str(device_id)
        self.suffix = suffix
        suffix_part = f"_{suffix}" if suffix else ""
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{self.device_id}{suffix_part}"

    @property
    def device(self) -> dict[str, Any]:
        for device in self.coordinator.data.get("devices", []):
            if str(device.get("id")) == self.device_id:
                return device
        return {}

    @property
    def device_info(self):
        d = self.device
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": d.get("name") or f"Hunonic {self.device_id}",
            "manufacturer": "Hunonic",
            "model": d.get("root_type") or d.get("type"),
            "suggested_area": d.get("room_name"),
        }

    @property
    def available(self) -> bool:
        return bool(self.device) and self.device.get("state") != "0"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.device
        return {
            "hunonic_id": d.get("id"),
            "root_id": d.get("root_id"),
            "root_type": d.get("root_type"),
            "room_name": d.get("room_name"),
            "last_online": d.get("last_online"),
            "topicsub": d.get("topicsub"),
            "topicpub": d.get("topicpub"),
        }
