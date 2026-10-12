"""v4.8 — the local server refuses foreign Host (DNS rebinding) and foreign Origin (CSRF) requests."""
from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import pytest

import app
import history

BODY = json.dumps({"components": [{"instanceId": "s", "id": "dc-source", "displayName": "S", "qty": 9},
                                  {"instanceId": "r", "id": "resistor", "displayName": "R", "qty": 1000},
                                  {"instanceId": "g", "id": "ground", "displayName": "G", "qty": 0}],
                   "connections": [{"a": "s", "pinA": "P", "b": "r", "pinB": "A"}, {"a": "r", "pinA": "B", "b": "g", "pinB": "GND"},
                                   {"a": "s", "pinA": "N", "b": "g", "pinB": "GND"}]})


@pytest.fixture
def port(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v48.sqlite3")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        yield srv.server_address[1]
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


def request(port, method, path, headers, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
    for k, v in headers.items():
        conn.putheader(k, v)
    data = body.encode() if body else b""
    conn.putheader("Content-Length", str(len(data)))
    conn.endheaders(data)
    resp = conn.getresponse(); status = resp.status; resp.read(); conn.close()
    return status


@pytest.mark.parametrize("host_template", ["127.0.0.1:{p}", "localhost:{p}", "[::1]:{p}"])
def test_local_hosts_are_accepted(port, host_template):
    assert request(port, "GET", "/api/health", {"Host": host_template.format(p=port)}) == 200


@pytest.mark.parametrize("host", ["attacker.example:{p}", "127.0.0.1.attacker.example:{p}", "127.0.0.1:1", "localhost"])
def test_foreign_host_is_refused(port, host):
    assert request(port, "GET", "/api/history", {"Host": host.format(p=port)}) == 403


def test_cross_site_post_is_refused_and_writes_nothing(port):
    status = request(port, "POST", "/api/electrical/workbench-run",
                     {"Host": f"127.0.0.1:{port}", "Origin": "https://evil.example", "Content-Type": "text/plain"}, BODY)
    assert status == 403
    assert history.list_experiments() == []


@pytest.mark.parametrize("origin", ["http://127.0.0.1:{p}", "http://localhost:{p}"])
def test_same_origin_post_is_accepted(port, origin):
    status = request(port, "POST", "/api/electrical/workbench-run",
                     {"Host": f"127.0.0.1:{port}", "Origin": origin.format(p=port), "Content-Type": "application/json"}, BODY)
    assert status == 200


@pytest.mark.parametrize("origin", ["null", "http://127.0.0.1:1", "https://127.0.0.1:{p}", "file://"])
def test_odd_origins_are_refused(port, origin):
    assert request(port, "POST", "/api/electrical/workbench-run", {"Host": f"127.0.0.1:{port}", "Origin": origin.format(p=port)}, BODY) == 403
