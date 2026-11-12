from __future__ import annotations

import hashlib
import hmac
import os
import secrets

from fastapi import HTTPException, Request

from .db import get_setting, set_setting

COOKIE = "hub_admin"


def _secret() -> str:
    s = get_setting("cookie_secret")
    if not s:
        s = secrets.token_hex(32)
        set_setting("cookie_secret", s)
    return s


def pin() -> str:
    return os.environ.get("HUB_PIN", "4817")


def token() -> str:
    return hmac.new(_secret().encode(), f"admin:{pin()}".encode(), hashlib.sha256).hexdigest()


def is_admin(request: Request) -> bool:
    return hmac.compare_digest(request.cookies.get(COOKIE, ""), token())


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Unlock with the admin PIN first")
