#!/usr/bin/env python3
"""Validate a UI manifest before cropping or generating Godot files."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import ManifestError, load_manifest, source_path
from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--check-source", action="store_true", help="Also open the source image and check pixel bounds")
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)

    image = source_path(manifest)
    if args.check_source:
        if not image.is_file():
            raise ManifestError(f"Source image not found: {image}")
        with Image.open(image) as im:
            width, height = im.size
        for item in ([manifest["background"]] if manifest.get("background") else []) + manifest.get("elements", []):
            if item.get("type") == "label":
                continue
            units = item.get("bbox_units", manifest.get("bbox_units", "normalized"))
            x, y, w, h = item["bbox"]
            if units == "normalized":
                x, y, w, h = x * width, y * height, w * width, h * height
            if x < 0 or y < 0 or x + w > width + 1 or y + h > height + 1:
                raise ManifestError(f"Bounding box for '{item['id']}' exceeds source image ({width}x{height}).")
        print(f"Source image OK: {width} x {height}")

    print(f"Manifest OK: {len(manifest.get('elements', []))} elements; background: {'yes' if manifest.get('background') else 'no'}")
    print(f"Scene: {manifest['project']['scene_path']}")
    print(f"Script: {manifest['project']['script_path']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ManifestError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
