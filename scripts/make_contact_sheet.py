#!/usr/bin/env python3
"""Create a labelled preview sheet from the crop report emitted by slice_assets.py."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help=".ui-slicing-report.json")
    parser.add_argument("--output", type=Path, default=Path("ui_contact_sheet.png"))
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--cell-width", type=int, default=260)
    parser.add_argument("--cell-height", type=int, default=210)
    args = parser.parse_args()
    if args.columns < 1 or args.cell_width < 120 or args.cell_height < 100:
        parser.error("columns must be >=1; cell dimensions must be at least 120x100")

    rows = json.loads(args.report.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        parser.error("Report is empty or not a JSON array.")

    count = len(rows)
    cols = args.columns
    row_count = math.ceil(count / cols)
    sheet = Image.new("RGB", (cols * args.cell_width, row_count * args.cell_height), (42, 45, 52))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for index, item in enumerate(rows):
        x = (index % cols) * args.cell_width
        y = (index // cols) * args.cell_height
        image_path = Path(item["output"])
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        with Image.open(image_path) as source:
            thumb = source.convert("RGBA")
            thumb.thumbnail((args.cell_width - 20, args.cell_height - 56), Image.Resampling.LANCZOS)
        # Checkerboard transparency preview.
        preview = Image.new("RGBA", (args.cell_width - 20, args.cell_height - 56), (225, 225, 225, 255))
        pdraw = ImageDraw.Draw(preview)
        checker = 12
        for cy in range(0, preview.height, checker):
            for cx in range(0, preview.width, checker):
                if (cx // checker + cy // checker) % 2:
                    pdraw.rectangle((cx, cy, cx + checker - 1, cy + checker - 1), fill=(190, 190, 190, 255))
        px = (preview.width - thumb.width) // 2
        py = (preview.height - thumb.height) // 2
        preview.alpha_composite(thumb, (px, py))
        sheet.paste(preview.convert("RGB"), (x + 10, y + 10))
        title = f"{item.get('id', 'item')} [{item.get('state', 'normal')}]"
        size = item.get("size", [0, 0])
        draw.text((x + 10, y + args.cell_height - 32), title[:34], fill=(255, 255, 255), font=font)
        draw.text((x + 10, y + args.cell_height - 17), f"{size[0]} x {size[1]}", fill=(190, 195, 205), font=font)

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="PNG", optimize=True)
    print(f"Contact sheet: {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
