"""Complete traceability (v6.4): event journal, environment record and reproducible package.

Event journal — every lifecycle action on an experiment (saved, verified, replayed, exported,
packaged, refused) is appended to the `experiment_events` table with its time and details.

Reproducible package — one ZIP file a third party can use without this installation:
  dossier.json, configuration.json, events.json, environment.json
  data/            catalogue datasets used (JSON + CSV), original imported files, source dossiers
  platform/        snapshot of the platform's Python code and reference data (standard library only)
  reproduce.py     re-runs the calculation with the bundled code and compares it with the dossier
  README_REPRODUCE.md
  MANIFEST.json    SHA-256 and size of every file, and a fingerprint of the manifest itself

The fingerprint detects accidental or deliberate changes to the package content. It is not a
signature: it does not prove who produced the package (no external authenticity claim).
"""
from __future__ import annotations

import hashlib
import io
import json
import platform as platform_module
import sqlite3
import sys
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import history
from version import APP_VERSION

ROOT = Path(__file__).resolve().parent
PACKAGE_FORMAT = "virtual-lab-reproducible-package"
PACKAGE_VERSION = 1
# Code and reference data copied into a package (never user databases, imported assets or caches).
SNAPSHOT_FILES = ("*.py",)
SNAPSHOT_DIRS = (("data_catalog", "*.json"), ("data_catalog/datasets", "*.json"), ("scientific_library", "*.json"), ("benchmarks", "*.py"))
EXCLUDED_SNAPSHOT = {"app_test.py"}


class PackageError(ValueError):
    def __init__(self, message: str, code: str = "package_error", **params):
        super().__init__(message)
        self.code = code
        self.params = params


# ---- event journal ---------------------------------------------------------------------------

def _connect():
    conn = history._connect()
    conn.execute("""CREATE TABLE IF NOT EXISTS experiment_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, experiment_id INTEGER NOT NULL, at_utc TEXT NOT NULL, event TEXT NOT NULL, details_json TEXT NOT NULL)""")
    return conn


def log_event(experiment_id: int, event: str, **details: Any) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("INSERT INTO experiment_events (experiment_id, at_utc, event, details_json) VALUES (?,?,?,?)",
                     (int(experiment_id), datetime.now(timezone.utc).isoformat(timespec="microseconds"), event, json.dumps(details, ensure_ascii=False, default=str)))


def events(experiment_id: int) -> list[dict[str, Any]]:
    with closing(_connect()) as conn:
        rows = conn.execute("SELECT at_utc, event, details_json FROM experiment_events WHERE experiment_id = ? ORDER BY id", (int(experiment_id),)).fetchall()
    return [{"at_utc": r["at_utc"], "event": r["event"], "details": json.loads(r["details_json"])} for r in rows]


def environment() -> dict[str, Any]:
    """Software environment of this computation (no personal data: no user name, host name or paths)."""
    import chemical_kinetics, electrical_circuits, fitting, pipelines, workbench_circuit, workbench_transient
    return {"app_version": APP_VERSION, "python": platform_module.python_version(), "implementation": platform_module.python_implementation(),
            "os": platform_module.system(), "machine": platform_module.machine(), "sqlite": sqlite3.sqlite_version,
            "engines": {m.ENGINE_ID: m.ENGINE_VERSION for m in (chemical_kinetics, electrical_circuits, fitting, pipelines, workbench_circuit, workbench_transient)},
            "third_party_packages": "none (Python standard library only)", "recorded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def seeds(configuration: Any) -> dict[str, Any]:
    """Every random seed found in a configuration (path → value)."""
    found: dict[str, Any] = {}

    def walk(value, path):
        if isinstance(value, dict):
            for k, v in value.items():
                if k == "seed" and isinstance(v, (int, float)):
                    found[path + k] = v
                walk(v, f"{path}{k}.")
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, f"{path}{i}.")
    walk(configuration, "")
    return found


# ---- package ---------------------------------------------------------------------------------

def _snapshot() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for pattern in SNAPSHOT_FILES:
        for path in sorted(ROOT.glob(pattern)):
            if path.name not in EXCLUDED_SNAPSHOT:
                files[f"platform/{path.name}"] = path.read_bytes()
    for folder, pattern in SNAPSHOT_DIRS:
        for path in sorted((ROOT / folder).glob(pattern)):
            files[f"platform/{folder}/{path.name}"] = path.read_bytes()
    return files


def _data_files(dossier: dict[str, Any]) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Datasets, original files and source dossiers the calculation depends on."""
    import data_catalog
    import scientific_imports
    files, needs = {}, {"local_catalog_entries": [], "source_dossiers": []}
    configuration = dossier.get("configuration") or {}
    dataset_id = configuration.get("dataset_id")
    if dataset_id:
        entry = data_catalog.get_entry(dataset_id)
        files[f"data/{dataset_id}.json"] = json.dumps(entry, ensure_ascii=False, indent=2).encode("utf-8")
        files[f"data/{dataset_id}.csv"] = data_catalog.export_csv(dataset_id).encode("utf-8")
        if entry.get("origin") == "local":
            needs["local_catalog_entries"].append(f"data/{dataset_id}.json")
            sha = (entry.get("provenance") or {}).get("file_sha256")
            for asset in scientific_imports.list_assets()["assets"]:
                if asset.get("sha256") == sha and asset.get("stored_path"):
                    original = scientific_imports.BASE / asset["stored_path"]
                    if original.is_file():
                        files[f"data/original/{asset['filename']}"] = original.read_bytes()
    source_id = configuration.get("source_experiment_id")
    if source_id is not None:
        source = history.get_experiment(int(source_id))
        if source is None:
            raise PackageError("The source dossier of this reading is missing from the history.", "missing_source_dossier")
        files[f"data/source_dossier_{source_id}.json"] = json.dumps(source, ensure_ascii=False, indent=2).encode("utf-8")
        needs["source_dossiers"].append(f"data/source_dossier_{source_id}.json")
    return files, needs


REPRODUCE_SCRIPT = r'''"""Reproduce the calculation of this package with the bundled platform code (standard library only).

Usage:  python reproduce.py        (Python 3.10 or later; no network, no installation)
Writes reproduction_report.json next to this script. Exit code 0 = reproduced within tolerance.
"""
import hashlib, json, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def check_manifest():
    manifest = json.loads((HERE / "MANIFEST.json").read_text(encoding="utf-8"))
    bad = [f["path"] for f in manifest["files"] if not (HERE / f["path"]).is_file()
           or hashlib.sha256((HERE / f["path"]).read_bytes()).hexdigest() != f["sha256"]]
    listing = json.dumps(manifest["files"], sort_keys=True, separators=(",", ":")).encode("utf-8")
    return bad, hashlib.sha256(listing).hexdigest() == manifest["manifest_sha256"]


def main():
    bad, listing_ok = check_manifest()
    if bad or not listing_ok:
        print("Package altered: files differing from MANIFEST.json:", bad or "(manifest listing)")
        return 2
    sys.path.insert(0, str(HERE / "platform"))
    import history
    history.DB_PATH = Path(tempfile.mkdtemp()) / "reproduction.sqlite3"
    import data_catalog, experiment_service
    from dossier import dossier_content_hash
    dossier = json.loads((HERE / "dossier.json").read_text(encoding="utf-8"))
    needs = json.loads((HERE / "package.json").read_text(encoding="utf-8"))["needs"]
    configuration = dict(dossier["configuration"])
    for path in needs["local_catalog_entries"]:
        entry = json.loads((HERE / path).read_text(encoding="utf-8"))
        data_catalog.add_entry({k: v for k, v in entry.items() if k not in ("record_type", "content_sha256", "origin", "integrity_ok")})
    for path in needs["source_dossiers"]:
        source = json.loads((HERE / path).read_text(encoding="utf-8"))
        source.pop("history_record", None)
        saved = history.save_experiment(source)
        configuration["source_experiment_id"] = saved["id"]
    model_id = dossier["model_id"]
    if model_id not in experiment_service.REPLAYERS:
        report = {"status": "not_reproducible_automatically", "model_id": model_id, "reason": "no replayer for this model in the bundled platform"}
    else:
        run, compare, engine = experiment_service.REPLAYERS[model_id]
        recorded_hash_ok = dossier_content_hash(dossier) == dossier.get("dossier_hash")
        result = run(configuration)
        comparison = compare(dossier, result)
        report = {"status": "reproduced" if comparison["identical_within_tolerance"] and recorded_hash_ok else "not_reproduced",
                  "model_id": model_id, "dossier_hash_matches_content": recorded_hash_ok, "engine_recorded": dossier.get("engine"),
                  "engine_used": {"id": engine[0], "version": engine[1]}, "python": sys.version.split()[0], "comparison": comparison}
    (HERE / "reproduction_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"{report['status']}: {model_id}" + (f" — {report['comparison']['compared_values']} values compared, max |difference| = "
                                                 f"{report['comparison']['max_abs_difference']:.3g}" if "comparison" in report else ""))
    return 0 if report["status"] == "reproduced" else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

README = """# Paquet reproductible — Virtual Lab Platform {app_version}

Expérience n° {experiment_id} : {title}
Modèle : `{model_id}`. Moteur : `{engine}`. Créé le {created}.

## Reproduire le calcul
1. Python 3.10 ou plus récent. Aucune installation ni connexion réseau n'est nécessaire.
2. Dans ce dossier, lancer : `python reproduce.py`
3. Résultat : `reproduction_report.json`. Le code de sortie vaut 0 si le calcul est reproduit dans la tolérance du moteur.

Le script vérifie d'abord `MANIFEST.json` : un fichier modifié est détecté et la reproduction est refusée.
L'empreinte du manifeste sert à contrôler l'**intégrité** du paquet. Ce n'est pas une signature : elle ne prouve pas qui a produit le paquet.

## Contenu
- `dossier.json` : dossier enregistré (configuration, résultats, hypothèses, limites, empreintes) ;
- `configuration.json`, `events.json` (journal), `environment.json` (logiciel utilisé) ;
- `data/` : données utilisées (catalogue, fichiers d'origine, dossiers sources) ;
- `platform/` : code de la plateforme au moment de l'export (bibliothèque standard Python seulement).
"""


def build_package(experiment_id: int) -> tuple[bytes, dict[str, Any]]:
    record = history.get_experiment_record(int(experiment_id))
    if record is None:
        raise PackageError("Experiment not found.", "not_found")
    dossier = record["dossier"]
    data, needs = _data_files(dossier)
    env = environment()
    journal = events(experiment_id)
    files: dict[str, bytes] = {
        "dossier.json": json.dumps(dossier, ensure_ascii=False, indent=2).encode("utf-8"),
        "configuration.json": json.dumps(dossier.get("configuration", {}), ensure_ascii=False, indent=2).encode("utf-8"),
        "events.json": json.dumps(journal, ensure_ascii=False, indent=2).encode("utf-8"),
        "environment.json": json.dumps({**env, "seeds": seeds(dossier.get("configuration", {}))}, ensure_ascii=False, indent=2).encode("utf-8"),
        "package.json": json.dumps({"format": PACKAGE_FORMAT, "format_version": PACKAGE_VERSION, "experiment_id": experiment_id,
                                    "model_id": dossier.get("model_id"), "needs": needs}, indent=2).encode("utf-8"),
        "reproduce.py": REPRODUCE_SCRIPT.encode("utf-8"),
        "README_REPRODUCE.md": README.format(app_version=APP_VERSION, experiment_id=experiment_id, title=dossier.get("title", ""), model_id=dossier.get("model_id"),
                                             engine=json.dumps(dossier.get("engine")), created=dossier.get("created_at_utc", "")).encode("utf-8"),
        **data, **_snapshot(),
    }
    listing = [{"path": p, "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)} for p, b in sorted(files.items())]
    manifest = {"format": PACKAGE_FORMAT, "format_version": PACKAGE_VERSION, "hash_algorithm": "SHA-256", "files": listing,
                "manifest_sha256": hashlib.sha256(json.dumps(listing, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
                "scope": "integrity of the listed files; not a signature and not a proof of authorship"}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(files.items()):
            zf.writestr(path, content)
        zf.writestr("MANIFEST.json", json.dumps(manifest, indent=2))
    log_event(experiment_id, "packaged", manifest_sha256=manifest["manifest_sha256"], files=len(listing))
    return buffer.getvalue(), manifest


def verify_package(data: bytes) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        manifest = json.loads(zf.read("MANIFEST.json"))
        names = set(zf.namelist()) - {"MANIFEST.json"}
        listed = {f["path"]: f for f in manifest["files"]}
        altered = [p for p, f in listed.items() if p not in names or hashlib.sha256(zf.read(p)).hexdigest() != f["sha256"]]
        unlisted = sorted(names - set(listed))
    listing_ok = hashlib.sha256(json.dumps(manifest["files"], sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest() == manifest["manifest_sha256"]
    return {"valid": not altered and not unlisted and listing_ok, "altered": altered, "unlisted": unlisted, "manifest_listing_ok": listing_ok,
            "manifest_sha256": manifest["manifest_sha256"]}
