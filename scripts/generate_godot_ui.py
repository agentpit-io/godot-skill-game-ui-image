#!/usr/bin/env python3
"""Generate a Godot 4 Control scene and GDScript from a UI manifest."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from common import ManifestError, gd_string, load_manifest, method_name, node_name, project_path


def as_res_path(path: str) -> str:
    return "res://" + Path(path).as_posix().lstrip("/")


def color_value(value: Any) -> str:
    if value is None:
        return "Color(1, 1, 1, 1)"
    if isinstance(value, str):
        raw = value.strip().lstrip("#")
        if len(raw) not in {6, 8} or not re.fullmatch(r"[0-9a-fA-F]+", raw):
            raise ManifestError(f"Invalid font_color '{value}'; use #RRGGBB or #RRGGBBAA.")
        vals = [int(raw[i:i + 2], 16) / 255.0 for i in range(0, len(raw), 2)]
        if len(vals) == 3:
            vals.append(1.0)
    elif isinstance(value, list) and len(value) in {3, 4} and all(isinstance(v, (int, float)) for v in value):
        vals = [float(v) for v in value]
        if len(vals) == 3:
            vals.append(1.0)
        if any(v < 0 or v > 1 for v in vals):
            raise ManifestError("font_color numeric components must be between 0 and 1.")
    else:
        raise ManifestError("font_color must be '#RRGGBB', '#RRGGBBAA', or [r,g,b,a].")
    return "Color(" + ", ".join(f"{v:.5f}" for v in vals) + ")"


def anchors_for(element: dict[str, Any], manifest: dict[str, Any]) -> tuple[float, float, float, float]:
    x, y, w, h = element["bbox"]
    units = element.get("bbox_units", manifest.get("bbox_units", "normalized"))
    if units == "pixels":
        design_w, design_h = manifest["project"]["design_size"]
        x, w = x / design_w, w / design_w
        y, h = y / design_h, h / design_h
    values = (x, y, x + w, y + h)
    if any(v < -0.000001 or v > 1.000001 for v in values):
        raise ManifestError(f"Element '{element['id']}' bbox maps outside normalized viewport: {values}")
    return tuple(max(0.0, min(1.0, float(v))) for v in values)  # type: ignore[return-value]


def layout_properties(element: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    left, top, right, bottom = anchors_for(element, manifest)
    return [
        f"anchor_left = {left:.6f}",
        f"anchor_top = {top:.6f}",
        f"anchor_right = {right:.6f}",
        f"anchor_bottom = {bottom:.6f}",
        "offset_left = 0.0",
        "offset_top = 0.0",
        "offset_right = 0.0",
        "offset_bottom = 0.0",
    ]


def add_texture(path: str, project_root: Path, resource_ids: dict[str, str]) -> str:
    # Validate and register an existing image asset.
    asset_path = project_path(project_root, path)
    if not asset_path.is_file():
        raise ManifestError(f"Texture asset does not exist: {asset_path} (run slice_assets.py first)")
    if path not in resource_ids:
        resource_ids[path] = f"tex_{len(resource_ids) + 1}"
    return resource_ids[path]


def node_block(name: str, node_type: str, props: list[str], children: list[str] | None = None) -> str:
    lines = [f'[node name={gd_string(name)} type={gd_string(node_type)} parent="."]']
    lines.extend(props)
    block = "\n".join(lines)
    if children:
        block += "\n\n" + "\n\n".join(children)
    return block


def add_label_properties(element: dict[str, Any], prefix: str = "") -> list[str]:
    props = [f"{prefix}text = {gd_string(str(element.get('text', '')))}"]
    font_size = element.get("font_size")
    if font_size is not None:
        if not isinstance(font_size, (int, float)) or font_size <= 0:
            raise ManifestError(f"font_size for '{element['id']}' must be a positive number.")
        props.append(f"{prefix}theme_override_font_sizes/font_size = {int(font_size)}")
    if "font_color" in element:
        props.append(f"{prefix}theme_override_colors/font_color = {color_value(element['font_color'])}")
    horizontal = int(element.get("horizontal_alignment", 1))
    vertical = int(element.get("vertical_alignment", 1))
    if horizontal not in {0, 1, 2}:
        raise ManifestError(f"horizontal_alignment for '{element['id']}' must be 0, 1, or 2.")
    if vertical not in {0, 1, 2}:
        raise ManifestError(f"vertical_alignment for '{element['id']}' must be 0, 1, or 2.")
    props.append(f"{prefix}horizontal_alignment = {horizontal}")
    props.append(f"{prefix}vertical_alignment = {vertical}")
    return props


def generate(manifest: dict[str, Any], project_root: Path, force: bool) -> tuple[Path, Path]:
    project = manifest["project"]
    scene_path = project_path(project_root, project["scene_path"])
    script_path = project_path(project_root, project["script_path"])
    for output in (scene_path, script_path):
        if output.exists() and not force:
            raise ManifestError(f"Generated file already exists (use --force to replace): {output}")

    textures: dict[str, str] = {}
    if manifest.get("background"):
        bg = manifest["background"]
        add_texture(bg["output"], project_root, textures)
    elements = sorted(manifest.get("elements", []), key=lambda item: int(item.get("z_index", 0)))
    for item in elements:
        if item.get("type") != "label":
            add_texture(item["output"], project_root, textures)
        if item.get("type") == "button":
            for state in item.get("states", {}).values():
                if state.get("output"):
                    add_texture(state["output"], project_root, textures)

    script_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.parent.mkdir(parents=True, exist_ok=True)

    script_res_id = "main_script"
    ext_resources = [f'[ext_resource type="Script" path={gd_string(as_res_path(project["script_path"]))} id={gd_string(script_res_id)}]']
    for path, res_id in textures.items():
        ext_resources.append(f'[ext_resource type="Texture2D" path={gd_string(as_res_path(path))} id={gd_string(res_id)}]')

    scene_blocks: list[str] = []
    connections: list[str] = []
    handler_actions: dict[str, str] = {}

    root_name = str(project.get("name", "MainMenu"))
    root_name = re.sub(r"[^A-Za-z0-9_]", "", root_name) or "MainMenu"
    root_lines = [
        f'[gd_scene load_steps={len(ext_resources) + 1} format=3]',
        "",
        "\n".join(ext_resources),
        "",
        f'[node name={gd_string(root_name)} type="Control"]',
        "layout_mode = 3",
        "anchors_preset = 15",
        "anchor_right = 1.0",
        "anchor_bottom = 1.0",
        "grow_horizontal = 2",
        "grow_vertical = 2",
        f"script = ExtResource({gd_string(script_res_id)})",
    ]

    if manifest.get("background"):
        bg = manifest["background"]
        bg_name = node_name(bg["id"])
        tex_ref = textures[bg["output"]]
        fit_map = {"stretch": 0, "tile": 1, "keep": 2, "keep_centered": 3, "contain": 5, "cover": 6}
        fit = bg.get("fit", "cover")
        if fit not in fit_map:
            raise ManifestError(f"Unsupported background.fit '{fit}'.")
        bg_props = [
            "layout_mode = 1",
            "anchors_preset = 15",
            "anchor_right = 1.0",
            "anchor_bottom = 1.0",
            "grow_horizontal = 2",
            "grow_vertical = 2",
            f"texture = ExtResource({gd_string(tex_ref)})",
            "expand_mode = 1",
            f"stretch_mode = {fit_map[fit]}",
            "mouse_filter = 2",
            f"z_index = {int(bg.get('z_index', -100))}",
        ]
        scene_blocks.append(f'[node name={gd_string(bg_name)} type="TextureRect" parent="."]\n' + "\n".join(bg_props))

    for element in elements:
        element_type = element["type"]
        name = node_name(element["id"])
        props = ["layout_mode = 1"] + layout_properties(element, manifest)
        props.append(f"z_index = {int(element.get('z_index', 0))}")

        if element_type == "image":
            tex = textures[element["output"]]
            stretch_mode = int(element.get("stretch_mode", 5))
            if stretch_mode not in range(7):
                raise ManifestError(f"stretch_mode for '{element['id']}' must be an integer from 0 to 6.")
            props.extend([f"texture = ExtResource({gd_string(tex)})", "expand_mode = 1", f"stretch_mode = {stretch_mode}", "mouse_filter = 2"])
            scene_blocks.append(f'[node name={gd_string(name)} type="TextureRect" parent="."]\n' + "\n".join(props))

        elif element_type == "panel":
            tex = textures[element["output"]]
            margins = element.get("nine_patch", {})
            props.extend([f"texture = ExtResource({gd_string(tex)})", "mouse_filter = 2"])
            for side in ("left", "top", "right", "bottom"):
                value = margins.get(side, 0)
                if not isinstance(value, int) or value < 0:
                    raise ManifestError(f"nine_patch.{side} for '{element['id']}' must be a non-negative integer.")
                props.append(f"patch_margin_{side} = {value}")
            if "draw_center" in element:
                if not isinstance(element["draw_center"], bool):
                    raise ManifestError(f"draw_center for '{element['id']}' must be true or false.")
                props.append(f"draw_center = {'true' if element['draw_center'] else 'false'}")
            scene_blocks.append(f'[node name={gd_string(name)} type="NinePatchRect" parent="."]\n' + "\n".join(props))

        elif element_type == "label":
            props.extend(add_label_properties(element))
            props.append("mouse_filter = 2")
            scene_blocks.append(f'[node name={gd_string(name)} type="Label" parent="."]\n' + "\n".join(props))

        elif element_type == "button":
            states = element.get("states", {})
            props.extend([
                f"texture_normal = ExtResource({gd_string(textures[element['output']])})",
                "ignore_texture_size = true",
                "stretch_mode = 0",
            ])
            for state_name, property_name in (("hover", "texture_hover"), ("pressed", "texture_pressed"), ("disabled", "texture_disabled")):
                state_output = states.get(state_name, {}).get("output")
                if state_output:
                    props.append(f"{property_name} = ExtResource({gd_string(textures[state_output])})")
            label_child = None
            button_text = element.get("text", "")
            if button_text:
                child_props = [
                    "layout_mode = 1",
                    "anchors_preset = 15",
                    "anchor_right = 1.0",
                    "anchor_bottom = 1.0",
                    "grow_horizontal = 2",
                    "grow_vertical = 2",
                ] + add_label_properties(element)
                child_props.append("mouse_filter = 2")
                label_child = f'[node name="Text" type="Label" parent={gd_string(name)}]\n' + "\n".join(child_props)
            scene_blocks.append(f'[node name={gd_string(name)} type="TextureButton" parent="."]\n' + "\n".join(props) + ("\n\n" + label_child if label_child else ""))
            action = str(element.get("action", element["id"]))
            method = method_name(action)
            handler_actions[method] = action
            connections.append(f'[connection signal="pressed" from={gd_string(name)} to="." method={gd_string(method)}]')

    scene_text = "\n".join(root_lines)
    if scene_blocks:
        scene_text += "\n\n" + "\n\n".join(scene_blocks)
    if connections:
        scene_text += "\n\n" + "\n".join(connections)
    scene_text += "\n"

    gd_lines = ["extends Control", "", "# Generated by game-ui-image-to-godot. Replace these placeholders with game logic."]
    if handler_actions:
        for method, action in handler_actions.items():
            gd_lines.extend([
                "",
                f"func {method}() -> void:",
                "\t# TODO: connect this handler to the appropriate game logic.",
                f"\tprint({gd_string('UI action triggered: ' + action)})",
            ])
    else:
        gd_lines.append("func _ready() -> void:")
        gd_lines.append("\tpass")
    gd_text = "\n".join(gd_lines) + "\n"

    scene_path.write_text(scene_text, encoding="utf-8")
    script_path.write_text(gd_text, encoding="utf-8")
    return scene_path, script_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Godot project root")
    parser.add_argument("--force", action="store_true", help="Replace existing scene/script files")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    project_root = args.project_root.expanduser().resolve()
    if not (project_root / "project.godot").is_file():
        raise ManifestError(f"No project.godot found under project root: {project_root}")
    scene_path, script_path = generate(manifest, project_root, args.force)
    print(f"Generated scene: {scene_path}")
    print(f"Generated script: {script_path}")
    print("Review the generated scene in Godot and connect placeholder handlers to real game logic.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ManifestError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
