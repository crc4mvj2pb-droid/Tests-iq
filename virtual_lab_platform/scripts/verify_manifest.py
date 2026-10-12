"""Verify every file listed in MANIFEST.sha256 (independent of build_release.py). Exit code 1 on any mismatch."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    manifest = ROOT / "MANIFEST.sha256"
    if not manifest.exists():
        print("MANIFEST.sha256 not found (it is created inside release archives).")
        return 1
    bad = 0
    lines = [l for l in manifest.read_text(encoding="utf-8").splitlines() if l.strip()]
    for line in lines:
        digest, rel = line.split("  ", 1)
        path = ROOT / rel
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            print(f"MISMATCH {rel}"); bad += 1
    print(f"{len(lines) - bad}/{len(lines)} files verified")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
