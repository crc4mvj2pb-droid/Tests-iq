"""Compile every Python file and syntax-check every inline <script> block with Node.js (if available)."""
from __future__ import annotations

import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    py_files = [p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts]
    for path in py_files:
        py_compile.compile(str(path), doraise=True)
    print(f"Python: {len(py_files)} files compiled")
    blocks = re.findall(r"<script[^>]*>(.*?)</script>", (ROOT / "static" / "index.html").read_text(encoding="utf-8"), re.S)
    node = shutil.which("node")
    if not node:
        print(f"JavaScript: {len(blocks)} blocks NOT checked (Node.js not installed)")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        for i, block in enumerate(blocks):
            path = Path(tmp) / f"block{i}.js"; path.write_text(block, encoding="utf-8")
            result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
            if result.returncode:
                print(result.stderr); return 1
    print(f"JavaScript: {len(blocks)} inline blocks passed node --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
