#!/usr/bin/env python3
"""Inspect an image and create a starter UI manifest (no AI detection performed)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Source UI design image (PNG/JPG/WebP, etc.)")
    parser.add_argument("--output", type=Path, default=Path("ui_manifest.json"), help="Manifest JSON output path")
    parser.add_argument("--project-name", default="MainMenu", help="Godot scene/root name")
    parser.add_argument("--scene", default="scenes/ui/main_menu.tscn", help="Project-relative output scene path")
    parser.add_argument("--script", default="scripts/ui/main_menu.gd", help="Project-relative output GDScript path")
    args = parser.parse_args()

    image_path = args.image.expanduser().resolve()
    if not image_path.is_file():
        parser.error(f"Image does not exist: {image_path}")
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            image_format = img.format
            has_alpha = "A" in img.getbands() or "transparency" in img.info
    except Exception as exc:
        parser.error(f"Cannot read image: {exc}")

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    rel_source = Path(__import__("os").path.relpath(image_path, output.parent)).as_posix()
    manifest = {
        "schema_version": 1,
        "project": {
            "name": args.project_name,
            "design_size": [width, height],
            "scene_path": args.scene,
            "script_path": args.script,
        },
        "source_image": rel_source,
        "bbox_units": "normalized",
        "background": None,
        "elements": [],
    }
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Image: {image_path}")
    print(f"Dimensions: {width} x {height} | format: {image_format} | alpha: {'yes' if has_alpha else 'no'}")
    print(f"Starter manifest: {output}")
    print("Next: visually identify components and fill background/elements bounding boxes in the manifest.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Cancelled", file=sys.stderr)
        raise SystemExit(130)
