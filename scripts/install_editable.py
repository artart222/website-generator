#!/usr/bin/env python
"""Install all workspace packages in editable mode (development)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = [
    ROOT / "packages" / "wg-contracts",
    ROOT / "packages" / "wg-core",
    ROOT / "packages" / "wg-runtime",
    ROOT / "packages" / "wg-commerce",
]


def main() -> int:
    for package_dir in PACKAGES:
        print(f"Installing editable: {package_dir.name}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-e", str(package_dir)],
            cwd=ROOT,
        )
    print("Installing editable: website-generator (root)")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-e", f".[dev]"],
        cwd=ROOT,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
