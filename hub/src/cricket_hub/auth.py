from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time

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


_misses: dict[str, list[float]] = {}
_lock = threading.Lock()


def check_pin(given: str, client: str = "") -> bool:
    """Constant-time PIN check. 5 wrong tries in a minute from one client lock that client out for 60 s."""
    with _lock:
        t = time.monotonic()
        for k in [k for k, v in _misses.items() if not v or t - v[-1] >= 60]:
            del _misses[k]                         # evict stale clients
        if sum(len(v) for v in _misses.values()) >= 30:
            return False                           # global budget: many clients guessing at once
        recent = [m for m in _misses.get(client, []) if t - m < 60]
        if len(recent) >= 5:
            _misses[client] = recent
            return False
        if hmac.compare_digest(given.encode(), pin().encode()):
            _misses.pop(client, None)
            return True
        recent.append(t)
        _misses[client] = recent
        return False


def token() -> str:
    return hmac.new(_secret().encode(), f"admin:{pin()}".encode(), hashlib.sha256).hexdigest()


def is_admin(request: Request) -> bool:
    return hmac.compare_digest(request.cookies.get(COOKIE, ""), token())


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Unlock with the admin PIN first")
