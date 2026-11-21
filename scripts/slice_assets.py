#!/usr/bin/env python3
"""Crop UI component PNGs from source image regions described in a manifest."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from PIL import Image

from common import ManifestError, iter_crop_specs, load_manifest, project_path, source_path


def as_crop_box(spec: dict[str, Any], image_size: tuple[int, int]) -> tuple[int, int, int, int]:
    image_w, image_h = image_size
    x, y, w, h = spec["bbox"]
    units = spec.get("bbox_units", "normalized")
    if units == "normalized":
        x, w = x * image_w, w * image_w
        y, h = y * image_h, h * image_h
    left, top = math.floor(x), math.floor(y)
    right, bottom = math.ceil(x + w), math.ceil(y + h)
    padding = spec.get("padding", 0)
    if isinstance(padding, int):
        pad_left = pad_top = pad_right = pad_bottom = padding
    else:
        pad_left, pad_top, pad_right, pad_bottom = padding
    left = max(0, left - pad_left)
    top = max(0, top - pad_top)
    right = min(image_w, right + pad_right)
    bottom = min(image_h, bottom + pad_bottom)
    if left >= right or top >= bottom:
        raise ManifestError(f"Crop for '{spec.get('id')}' is empty after clipping.")
    if x < 0 or y < 0 or x + w > image_w + 1 or y + h > image_h + 1:
        raise ManifestError(f"Crop for '{spec.get('id')}' is outside source image {image_w}x{image_h}.")
    return left, top, right, bottom


def crop_to_png(source: Path, dest: Path, box: tuple[int, int, int, int], force: bool) -> dict[str, Any]:
    if dest.exists() and not force:
        raise ManifestError(f"Output already exists (use --force to replace): {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as img:
        if "A" in img.getbands() or "transparency" in img.info:
            converted = img.convert("RGBA")
        else:
            converted = img.convert("RGB")
        cropped = converted.crop(box)
        if dest.suffix.lower() != ".png":
            raise ManifestError(f"Output must use .png to preserve alpha: {dest}")
        cropped.save(dest, format="PNG", optimize=True)
        return {"source": str(source), "output": str(dest), "bbox_pixels": list(box), "size": list(cropped.size), "mode": cropped.mode}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Godot project root; output paths are relative to it")
    parser.add_argument("--force", action="store_true", help="Replace existing crop files")
    parser.add_argument("--report", type=Path, help="Optional JSON report path (defaults to <project>/.ui-slicing-report.json)")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    project_root = args.project_root.expanduser().resolve()
    if not (project_root / "project.godot").is_file():
        raise ManifestError(f"No project.godot found under project root: {project_root}")

    # Preflight every crop before writing anything, so a typo cannot leave a half-built asset set.
    plan = []
    planned_outputs: set[Path] = set()
    for parent, state_name, spec in iter_crop_specs(manifest):
        src = source_path(manifest, spec.get("source"))
        if not src.is_file():
            raise ManifestError(f"Source image for '{parent['id']}' ({state_name}) not found: {src}")
        with Image.open(src) as img:
            source_size = img.size
            box = as_crop_box(spec, source_size)
        output_path = spec.get("output")
        if not output_path:
            continue
        dest = project_path(project_root, output_path)
        if dest.resolve() == src.resolve():
            raise ManifestError(f"Refusing to overwrite source image with its crop: {src}")
        if dest in planned_outputs:
            raise ManifestError(f"Multiple manifest entries target the same output: {dest}")
        if dest.exists() and not args.force:
            raise ManifestError(f"Output already exists (use --force to replace): {dest}")
        planned_outputs.add(dest)
        plan.append((parent, state_name, src, dest, box))

    report: list[dict[str, Any]] = []
    for parent, state_name, src, dest, box in plan:
        entry = crop_to_png(src, dest, box, args.force)
        entry.update({"id": parent["id"], "state": state_name})
        report.append(entry)
        print(f"[{parent['id']}:{state_name}] {dest.relative_to(project_root).as_posix()} {entry['size'][0]}x{entry['size'][1]}")

    report_path = args.report.expanduser().resolve() if args.report else project_root / ".ui-slicing-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Cropped {len(report)} asset(s). Report: {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ManifestError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
