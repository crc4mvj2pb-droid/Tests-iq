"""v9.1 — input security and resource limits."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import scientific_imports
import security


@pytest.fixture
def base(monkeypatch):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


def raw_post(url, text):
    req = urllib.request.Request(url, data=text.encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read()), r.headers
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read()), exc.headers


def test_security_headers_and_csp(base):
    with urllib.request.urlopen(base + "/", timeout=10) as r:
        assert r.headers["X-Content-Type-Options"] == "nosniff" and r.headers["X-Frame-Options"] == "DENY"
        csp = r.headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in csp and "default-src 'self'" in csp and "object-src 'none'" in csp
    with urllib.request.urlopen(base + "/api/health", timeout=10) as r:
        assert r.headers["Referrer-Policy"] == "no-referrer" and "Content-Security-Policy" not in r.headers


@pytest.mark.parametrize("payload,code", [('{"source_voltage": NaN, "resistors": []}', "invalid_json"),
                                          ('{"source_voltage": Infinity, "resistors": []}', "invalid_json"),
                                          ('{"a": ' * 100 + "1" + "}" * 100, "json_too_deep")])
def test_non_finite_literals_and_deep_nesting_are_refused(base, payload, code):
    status, body, _ = raw_post(base + "/api/electrical/dc-solve", payload)
    assert status == 400 and body["error_code"] == code


def test_rate_limit_answers_429_with_retry_after(base, monkeypatch):
    monkeypatch.setitem(app.LIMITS, "requests_per_minute", 10)
    codes = []
    for _ in range(14):
        try:
            with urllib.request.urlopen(base + "/api/health", timeout=10) as r:
                codes.append(r.status)
        except urllib.error.HTTPError as exc:
            codes.append(exc.code)
            retry = exc.headers["Retry-After"]
            body = json.loads(exc.read())
    assert codes[:10] == [200] * 10 and 429 in codes and int(retry) >= 1 and body["error_code"] == "rate_limited"


def test_token_bucket_refills():
    limiter = security.RateLimiter(60)  # one per second
    for _ in range(60):
        assert limiter.allow("x")[0]
    allowed, wait = limiter.allow("x")
    assert not allowed and 0 < wait <= 1.0
    assert limiter.allow("other client")[0]  # buckets are per client


def test_dtd_after_a_long_comment_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(scientific_imports, "ASSET_DIR", tmp_path)
    monkeypatch.setattr(scientific_imports, "INDEX", tmp_path / "index.json")
    payload = "<?xml version='1.0'?><!--" + "x" * 30000 + "--><!DOCTYPE lolz [<!ENTITY lol 'lol'><!ENTITY lol2 '&lol;&lol;'>]><sbml>&lol2;</sbml>"
    with pytest.raises(ValueError, match="DOCTYPE and ENTITY"):
        scientific_imports.import_sbml("bomb.xml", payload)
    assert not list(tmp_path.rglob("*.xml"))  # nothing stored
