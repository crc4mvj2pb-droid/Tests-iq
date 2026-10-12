"""Build a clean, verifiable release archive.

Usage:  python scripts/build_release.py [output_dir]
Creates virtual_lab_platform_v<version>.zip with a MANIFEST.sha256 listing every file,
then re-opens the archive and checks every checksum. Local data (SQLite history,
caches, test artifacts) is never packaged.
"""
from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from version import APP_VERSION  # noqa: E402

EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", "test-artifacts", "dist", ".git", "backups", "logs"}
EXCLUDED_SUFFIXES = {".pyc", ".sqlite3-journal"}
# The user's history database and its migration backups are local data, never packaged.
EXCLUDED_PREFIXES = ("virtual_lab_history.sqlite3",)


def release_files() -> list[Path]:
    files = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if path.is_dir() or any(part in EXCLUDED_DIRS for part in rel.parts) or path.suffix in EXCLUDED_SUFFIXES or path.name.startswith(EXCLUDED_PREFIXES):
            continue
        files.append(path)
    return files


def main() -> int:
    out_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    folder = f"virtual_lab_platform_v{APP_VERSION}"
    target = out_dir / f"{folder}.zip"
    manifest = []
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in release_files():
            data = path.read_bytes()
            rel = path.relative_to(ROOT).as_posix()
            manifest.append(f"{hashlib.sha256(data).hexdigest()}  {rel}")
            zf.writestr(f"{folder}/{rel}", data)
        zf.writestr(f"{folder}/MANIFEST.sha256", "\n".join(manifest) + "\n")
    # Verify what was written, not what we intended to write.
    with zipfile.ZipFile(target) as zf:
        assert zf.testzip() is None, "corrupted archive member"
        listed = zf.read(f"{folder}/MANIFEST.sha256").decode().splitlines()
        for line in listed:
            digest, rel = line.split("  ", 1)
            assert hashlib.sha256(zf.read(f"{folder}/{rel}")).hexdigest() == digest, rel
        assert not [n for n in zf.namelist() if n.endswith(".pyc") or "virtual_lab_history.sqlite3" in n]
    archive_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    print(f"{target} — {len(listed)} files verified — SHA-256 {archive_digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
