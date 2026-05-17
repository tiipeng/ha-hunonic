from __future__ import annotations

import base64
import hashlib
from typing import Any
from urllib.parse import urlencode

from aiohttp import ClientSession

from .const import APP_NAME, APP_ROLE, DEFAULT_BASE_URL

_ACCESS_KEY = "accessKey98ccdcbbe7b5528bec0ca31bbe8d93b4e76590dd"
_SIGN_SALT = "HUNONICBIGBUG94d3c445e72ae7805fca3489edac9608c893e66b"


class HunonicError(Exception):
    """Base Hunonic API error."""


class HunonicAuthError(HunonicError):
    """Authentication failed."""


def _b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


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
