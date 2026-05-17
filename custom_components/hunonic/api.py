from __future__ import annotations

import base64
import hashlib
import json
import socket
from typing import Any
from urllib.parse import urlencode

from aiohttp import ClientSession

from .const import APP_NAME, APP_ROLE, DEFAULT_BASE_URL

_ACCESS_KEY = "accessKey98ccdcbbe7b5528bec0ca31bbe8d93b4e76590dd"
_SIGN_SALT = "HUNONICBIGBUG94d3c445e72ae7805fca3489edac9608c893e66b"
_MQTT_SERVER_B64 = "QS4npF55SVwlPsXdQv8N6Ggej7kNcW6TGz4HpBfPwctPKBsL8hyiM4g4rMw57DjLZIG7TUoxtfuXhX+e5OwjJbc2nOado6wycygF4nwxXuLd0hvOfd4+7MabxyW28bhZLRDr3QYOFfKv2ygK7vpYQVpbi9NpxvwVw5g9bECPS/LdL0COsTYaYS+j5nNLoxgjHj5eSnOBebSQh7J23Otwjg=="
_MQTT_INFO_KEY = b"yAlaCKUYI3qr0kTd"
_MQTT_INFO_IV = b"QFjnL4GVODlNB0eZ"
_ZERO16 = b"0000000000000000"
_KEY_ACTION_USER = 209
_SWITCH_CONTROL_DEVICE = 0


class HunonicError(Exception):
    """Base Hunonic API error."""


class HunonicAuthError(HunonicError):
    """Authentication failed."""


class HunonicMqttError(HunonicError):
    """MQTT command failed."""


def _b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def _pkcs7_unpad(data: bytes) -> bytes:
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 16:
        raise HunonicMqttError("Invalid MQTT server info padding")
    return data[:-pad_len]


def _pkcs7_pad(data: bytes) -> bytes:
    pad_len = 16 - (len(data) % 16)
    return data + bytes([pad_len]) * pad_len


def _aes_cbc_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return encryptor.update(_pkcs7_pad(data)) + encryptor.finalize()


def _aes_cbc_decrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    return _pkcs7_unpad(decryptor.update(data) + decryptor.finalize())


def _mqtt_server_info() -> dict[str, Any]:
    raw = _aes_cbc_decrypt(base64.b64decode(_MQTT_SERVER_B64), _MQTT_INFO_KEY, _MQTT_INFO_IV)
    return json.loads(raw.decode("utf-8"))


def _derive_switch_key_iv(root_id: str) -> tuple[bytes, bytes]:
    seed = _aes_cbc_encrypt(str(root_id).encode("utf-8"), _ZERO16, _ZERO16)
    if len(seed) < 28:
        raise HunonicMqttError("Derived MQTT switch key is too short")
    return seed[4:20], seed[12:28]


def _switch_action_code(index_in_root: int, turn_on: bool) -> int:
    base = int(index_in_root) * 2
    return base - 1 if turn_on else base


def build_switch_command(device: dict[str, Any], user_id: int, turn_on: bool) -> tuple[str, bytes]:
    """Build the Hunonic MQTT switch command JSON and encrypted payload."""
    root_id = str(device["root_id"])
    root_type = str(device["root_type"])
    command = {
        "u": int(user_id),
        root_type: _SWITCH_CONTROL_DEVICE,
        "act_id": _KEY_ACTION_USER,
        "action": _switch_action_code(int(device.get("index_in_root", 1)), turn_on),
    }
    command_json = json.dumps(command, separators=(",", ":"), ensure_ascii=False)
    key, iv = _derive_switch_key_iv(root_id)
    return command_json, _aes_cbc_encrypt(command_json.encode("utf-8"), key, iv)


def publish_switch_command(device: dict[str, Any], user_id: int, turn_on: bool) -> None:
    """Publish one MQTT switch command. Runs in an executor from HA entity code."""
    import paho.mqtt.client as mqtt

    topic = device.get("topicpub") or device.get("topicsub")
    if not topic:
        raise HunonicMqttError("Device has no MQTT publish topic")
    _command_json, payload = build_switch_command(device, user_id, turn_on)
    server = _mqtt_server_info()
    host = str(server.get("server"))
    port = int(server.get("port", 1883))
    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.username_pw_set(server.get("user"), server.get("pass"))

    # Hunonic's broker hostname returns multiple A records. In Colima/Docker on
    # macOS, some of those routes intermittently fail with ENETUNREACH, so try
    # each IPv4 address before surfacing the error to Home Assistant.
    errors: list[str] = []
    connected = False
    for addr in _resolve_ipv4(host, port):
        try:
            result = client.connect(addr, port, keepalive=20)
            if result == 0:
                connected = True
                break
            errors.append(f"{addr}: MQTT connect rc={result}")
        except OSError as err:
            errors.append(f"{addr}: {err}")
    if not connected:
        raise HunonicMqttError("MQTT connect failed: " + "; ".join(errors))
    client.loop_start()
    try:
        info = client.publish(topic, payload=payload, qos=0, retain=False)
        info.wait_for_publish(timeout=10)
    finally:
        client.loop_stop()
        client.disconnect()
    if not info.is_published():
        raise HunonicMqttError("MQTT publish timed out")


def _resolve_ipv4(host: str, port: int) -> list[str]:
    addresses: list[str] = []
    for family, _socktype, _proto, _canonname, sockaddr in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM):
        if family == socket.AF_INET:
            ip = sockaddr[0]
            if ip not in addresses:
                addresses.append(ip)
    return addresses or [host]


def hunonic_signature(params: dict[str, Any]) -> str:
    n: float = 0
    for key, value in params.items():
        if key == "signature":
            continue
        if value not in (None, False, 0, ""):
            encoded = _b64(str(value))
            try:
                n += float(encoded)
            except ValueError:
                n += ord(encoded[0]) + ord(encoded[len(encoded) // 2]) + ord(encoded[-1])
        if key:
            n += ord(str(key)[0]) + 58
    if float(n).is_integer():
        n = int(n)
    first = hashlib.md5(str(n).encode()).hexdigest()
    tmp = "accessKey=" + _ACCESS_KEY + first
    return hashlib.md5(("sha256fake" + tmp + _SIGN_SALT).encode()).hexdigest()


class HunonicClient:
    def __init__(self, session: ClientSession, base_url: str = DEFAULT_BASE_URL) -> None:
        self.session = session
        self.base_url = base_url.rstrip("/") + "/"

    def _url(self, path: str) -> str:
        return self.base_url + path.lstrip("/")

    async def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        payload["app_role"] = APP_ROLE
        payload["signature"] = hunonic_signature(payload)
        async with self.session.post(self._url(path), data=payload) as resp:
            body = await resp.json(content_type=None)
        if not isinstance(body, dict):
            raise HunonicError(f"Unexpected API response for {path}")
        if body.get("status") is not True:
            raise HunonicAuthError(body.get("message", "Hunonic API request failed"))
        return body

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = dict(params)
        payload["app_role"] = APP_ROLE
        payload["signature"] = hunonic_signature(payload)
        async with self.session.get(self._url(path + "?" + urlencode(payload))) as resp:
            body = await resp.json(content_type=None)
        if not isinstance(body, dict):
            raise HunonicError(f"Unexpected API response for {path}")
        if body.get("status") is not True:
            raise HunonicError(body.get("message", "Hunonic API request failed"))
        return body

    async def login(self, username: str, password: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "password": hashlib.md5(password.encode("utf-8")).hexdigest(),
            "app_name": APP_NAME,
            "lang": "de",
            "is_pro_app": 1,
        }
        payload["email" if "@" in username else "phone"] = username
        return await self._post("user/login", payload)

    async def profile(self, token_id: str) -> dict[str, Any]:
        return await self._get("user/getFullProfile", {"token_id": token_id})

    async def devices(self, token_id: str, home_id: str) -> dict[str, Any]:
        return await self._get("device/listDeviceOfHomeSelect", {"token_id": token_id, "home_id": home_id})
