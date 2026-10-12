"""Input security and resource limits of the local server (v9.1).

- JSON: NaN / Infinity literals are refused (json.loads accepts them by default) and nesting depth is limited.
- Headers: every response says nosniff, no framing, no referrer; HTML pages carry a Content-Security-Policy
  that only allows this server's own resources (the single-file interface uses inline scripts and styles).
- Rate limit: a token bucket per server and client address; above the limit the server answers 429 with
  Retry-After, so a runaway script cannot monopolise the machine.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

MAX_JSON_DEPTH = 64
SECURITY_HEADERS = {"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
                    "Cross-Origin-Opener-Policy": "same-origin"}
HTML_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")


class InputRejected(ValueError):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code
        self.params = {}


def _reject_constant(name: str):
    raise InputRejected(f"Non-finite number literal '{name}' is not accepted in JSON.", "invalid_json")


def _depth(value: Any, limit: int, level: int = 0) -> None:
    if level > limit:
        raise InputRejected(f"JSON nested deeper than {limit} levels.", "json_too_deep")
    if isinstance(value, dict):
        for v in value.values():
            _depth(v, limit, level + 1)
    elif isinstance(value, list):
        for v in value:
            _depth(v, limit, level + 1)


def parse_json(text: str) -> Any:
    try:
        value = json.loads(text, parse_constant=_reject_constant)
    except RecursionError:
        raise InputRejected(f"JSON nested deeper than {MAX_JSON_DEPTH} levels.", "json_too_deep") from None
    _depth(value, MAX_JSON_DEPTH)
    return value


class RateLimiter:
    def __init__(self, per_minute: int):
        self.capacity = float(per_minute)
        self.rate = per_minute / 60.0
        self.buckets: dict[str, tuple[float, float]] = {}
        self.lock = threading.Lock()

    def allow(self, client: str) -> tuple[bool, float]:
        now = time.monotonic()
        with self.lock:
            tokens, last = self.buckets.get(client, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - last) * self.rate)
            if tokens >= 1:
                self.buckets[client] = (tokens - 1, now)
                return True, 0.0
            self.buckets[client] = (tokens, now)
            return False, (1 - tokens) / self.rate


def has_dtd(text: str) -> bool:
    """True if an XML text declares a DOCTYPE or ENTITY anywhere (SBML never needs one)."""
    lowered = text.casefold()
    return "<!doctype" in lowered or "<!entity" in lowered
