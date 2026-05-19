#!/usr/bin/env python3
"""Package ankqol into a .ankiaddon archive for upload to AnkiWeb."""

import zipfile
from pathlib import Path

# Only these files go into the distributable archive.
# Add new source files here when the add-on grows.
INCLUDE = [
    "__init__.py",
    "archive_feature.py",
    "manifest.json",
    "config.json",
]

DIST_DIR = Path(__file__).parent / "dist"
OUTPUT   = DIST_DIR / "ankqol.ankiaddon"


def build() -> None:
    DIST_DIR.mkdir(exist_ok=True)

    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        root = Path(__file__).parent
        for name in INCLUDE:
            path = root / name
            if not path.exists():
                print(f"  MISSING  {name}")
                continue
            zf.write(path, arcname=name)
            print(f"  added    {name}")

    size_kb = OUTPUT.stat().st_size / 1024
    print(f"\nBuilt: {OUTPUT}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    build()
