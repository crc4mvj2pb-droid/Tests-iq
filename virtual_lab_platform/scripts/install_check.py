"""Installation check of an extracted release (v9.4) — standard library only.

Usage (from the extracted folder):  python scripts/install_check.py
Starts the real server (python app.py) on a free port with temporary data, backup and log folders, then
exercises the main paths over HTTP: health, version, contracts, a model run, a saved and verified dossier,
a report, a reproducible package re-run in an isolated process, a backup verified and restored, the
assistant, diagnostics. It also times 200 sequential requests. Nothing is written into the installation.
Exit code 0 when every check passes. Prints one line per check.
"""
from __future__ import annotations

import io
import json
import os
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINETICS = {"species": [{"id": "A", "initial_concentration": 1.0}, {"id": "B", "initial_concentration": 0.0}],
            "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.5}], "duration": 2.0, "dt": 0.1}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    results = []

    def check(name, ok, detail=""):
        results.append(ok)
        print(f"[{'OK' if ok else 'FAIL'}] {name}{' — ' + detail if detail else ''}")

    tmp = Path(tempfile.mkdtemp(prefix="vl_install_check_"))
    port = free_port()
    env = {k: v for k, v in os.environ.items() if not k.startswith("VIRTUAL_LAB")}
    env.update(VIRTUAL_LAB_PORT=str(port), VIRTUAL_LAB_DB=str(tmp / "history.sqlite3"), VIRTUAL_LAB_BACKUP_DIR=str(tmp / "backups"),
               VIRTUAL_LAB_LOG_DIR=str(tmp / "logs"), PYTHONNOUSERSITE="1")
    proc = subprocess.Popen([sys.executable, "app.py"], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    base = f"http://127.0.0.1:{port}"

    def get(path, raw=False):
        with urllib.request.urlopen(base + path, timeout=60) as r:
            data = r.read()
            return data if raw else json.loads(data)

    def post(path, body):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())
    try:
        for _ in range(150):
            try:
                health = get("/api/health"); break
            except OSError:
                time.sleep(0.1)
        else:
            check("server start", False, "no answer after 15 s"); return 1
        check("server start (standard library only)", health["status"] == "ok", f"version {health['version']}, Python {sys.version.split()[0]}")
        check("interface page", b"Virtual Lab" in get("/", raw=True))
        contracts = get("/api/contracts")["contracts"]
        check("model contracts", len(contracts) >= 19, f"{len(contracts)} contracts")
        code, run = post("/api/models/rc_rl_step_response/run", {"inputs": {"resistance_ohm": 1000, "capacitance_f": 1e-6}})
        check("model run", code == 200 and abs(run["outputs"]["time_constant"]["value"] - 1e-3) < 1e-15, "τ = 1 ms for 1 kΩ · 1 µF")
        code, dossier = post("/api/chemistry/kinetics-run", KINETICS)
        eid = dossier.get("history_record", {}).get("id")
        verify = get(f"/api/history/{eid}/verify")
        check("saved dossier verified", code == 200 and verify["valid"] and verify["level"] == "full", f"experiment {eid}")
        report = get(f"/api/history/{eid}/report.html", raw=True).decode()
        check("scientific report", "Conclusions" in report and "<svg" in report)
        package = get(f"/api/history/{eid}/package", raw=True)
        target = tmp / "third_party"
        target.mkdir()
        zipfile.ZipFile(io.BytesIO(package)).extractall(target)
        rep = subprocess.run([sys.executable, "-I", "reproduce.py"], cwd=target, capture_output=True, text=True, timeout=300)
        check("reproducible package re-run in an isolated process", rep.returncode == 0, rep.stdout.strip()[:100])
        code, backup = post("/api/admin/backup", {"label": "install-check"})
        code_v, verified = post("/api/admin/backup/verify", {"file": backup.get("file")})
        code_r, restored = post("/api/admin/backup/restore", {"file": backup.get("file")})
        check("backup, verification and restore", code == 200 and verified.get("valid") and code_r == 200 and restored.get("experiments") == 1)
        code, answer = post("/api/assistant/ask", {"question": "Quelle est la constante de temps d'un circuit RC avec R = 2 kΩ et C = 3 µF ?"})
        check("assistant traced answer", code == 200 and answer["status"] == "answered" and answer["untraced_numbers"] == [])
        diag = get("/api/diagnostics")
        check("diagnostics", diag["database"]["ok"] and not diag["recovery_mode"]["active"], f"{diag['database']['experiments']} experiments, {diag['backups']['count']} backups")
        timings = []
        for _ in range(200):
            t0 = time.perf_counter(); get("/api/health"); timings.append((time.perf_counter() - t0) * 1000)
        p95 = sorted(timings)[int(0.95 * len(timings)) - 1]
        check("200 sequential requests", True, f"median {statistics.median(timings):.2f} ms, p95 {p95:.2f} ms (single local user)")
        check("nothing written into the installation", not (ROOT / "backups").exists() and not (ROOT / "logs").exists())
    finally:
        proc.terminate()
        try:
            proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
