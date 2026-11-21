"""Shared helpers for game-ui-image-to-godot scripts."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SUPPORTED_TYPES = {"image", "button", "panel", "label"}
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class ManifestError(ValueError):
    pass


def load_manifest(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"Manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ManifestError("Manifest root must be a JSON object.")
    validate_manifest(data)
    data["_manifest_path"] = str(path)
    return data


def validate_manifest(data: dict[str, Any]) -> None:
    if data.get("schema_version") != 1:
        raise ManifestError("schema_version must be 1.")
    project = data.get("project")
    if not isinstance(project, dict):
        raise ManifestError("project must be an object.")
    design_size = project.get("design_size")
    if not (isinstance(design_size, list) and len(design_size) == 2 and all(isinstance(v, (int, float)) and v > 0 for v in design_size)):
        raise ManifestError("project.design_size must be [width, height] with positive numbers.")
    for key, suffix in (("scene_path", ".tscn"), ("script_path", ".gd")):
        value = project.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ManifestError(f"project.{key} must be a non-empty project-relative path.")
        _validate_project_relative(value, f"project.{key}")
        if not value.lower().endswith(suffix):
            raise ManifestError(f"project.{key} must end with {suffix}.")
    if project["scene_path"] == project["script_path"]:
        raise ManifestError("project.scene_path and project.script_path must be different files.")
    if not isinstance(data.get("source_image"), str) or not data["source_image"].strip():
        raise ManifestError("source_image must be a non-empty path.")
    units = data.get("bbox_units", "normalized")
    if units not in {"normalized", "pixels"}:
        raise ManifestError("bbox_units must be 'normalized' or 'pixels'.")
    bg = data.get("background")
    if bg is not None:
        _validate_element(bg, "background", units)
        if bg.get("type", "background") not in {"background", "image"}:
            raise ManifestError("background.type must be 'background' or 'image'.")
    elements = data.get("elements", [])
    if not isinstance(elements, list):
        raise ManifestError("elements must be an array.")
    ids: set[str] = set()
    if bg:
        ids.add(bg["id"])
    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            raise ManifestError(f"elements[{index}] must be an object.")
        _validate_element(element, f"elements[{index}]", units)
        if element["id"] in ids:
            raise ManifestError(f"Duplicate element id: {element['id']}")
        ids.add(element["id"])


def _validate_element(element: dict[str, Any], label: str, default_units: str) -> None:
    element_id = element.get("id")
    if not isinstance(element_id, str) or not ID_RE.fullmatch(element_id):
        raise ManifestError(f"{label}.id must match {ID_RE.pattern} (lowercase letters, digits, underscores).")
    element_type = element.get("type", "background" if label == "background" else None)
    allowed = SUPPORTED_TYPES | ({"background"} if label == "background" else set())
    if element_type not in allowed:
        raise ManifestError(f"{label}.type must be one of: {', '.join(sorted(allowed))}.")
    if element_type != "label":
        output = element.get("output")
        if not isinstance(output, str) or not output.strip():
            raise ManifestError(f"{label}.output is required for {element_type} elements.")
        _validate_project_relative(output, f"{label}.output")
        _validate_bbox(element.get("bbox"), element.get("bbox_units", default_units), f"{label}.bbox")
    else:
        if not isinstance(element.get("text"), str):
            raise ManifestError(f"{label}.text is required for label elements.")
        _validate_bbox(element.get("bbox"), element.get("bbox_units", default_units), f"{label}.bbox")
    if element_type == "button":
        states = element.get("states", {})
        if not isinstance(states, dict):
            raise ManifestError(f"{label}.states must be an object.")
        for state_name, state in states.items():
            if state_name not in {"hover", "pressed", "disabled"}:
                raise ManifestError(f"Unsupported button state '{state_name}' in {label}.")
            if not isinstance(state, dict):
                raise ManifestError(f"{label}.states.{state_name} must be an object.")
            if "output" in state:
                _validate_project_relative(state["output"], f"{label}.states.{state_name}.output")
            if "bbox" in state:
                _validate_bbox(state["bbox"], state.get("bbox_units", element.get("bbox_units", default_units)), f"{label}.states.{state_name}.bbox")
    padding = element.get("padding", 0)
    if not (isinstance(padding, int) and padding >= 0) and not (isinstance(padding, list) and len(padding) == 4 and all(isinstance(v, int) and v >= 0 for v in padding)):
        raise ManifestError(f"{label}.padding must be a non-negative integer or [left, top, right, bottom].")


def _validate_bbox(bbox: Any, units: str, label: str) -> None:
    if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(v, (int, float)) for v in bbox)):
        raise ManifestError(f"{label} must be [x, y, width, height].")
    x, y, w, h = bbox
    if w <= 0 or h <= 0:
        raise ManifestError(f"{label} width and height must be positive.")
    if units not in {"normalized", "pixels"}:
        raise ManifestError(f"{label} units must be 'normalized' or 'pixels'.")
    if units == "normalized" and (x < 0 or y < 0 or x + w > 1.000001 or y + h > 1.000001):
        raise ManifestError(f"{label} normalized coordinates must stay inside [0, 1].")
    if units == "pixels" and (x < 0 or y < 0):
        raise ManifestError(f"{label} pixel coordinates cannot be negative.")


def _validate_project_relative(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{label} must be a non-empty relative path.")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ManifestError(f"{label} must stay inside the Godot project (no absolute paths or '..').")


def source_path(manifest: dict[str, Any], value: str | None = None) -> Path:
    manifest_dir = Path(manifest["_manifest_path"]).parent
    raw = value or manifest["source_image"]
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = manifest_dir / path
    return path.resolve()


def project_path(project_root: Path, relative: str) -> Path:
    _validate_project_relative(relative, "output path")
    root = project_root.expanduser().resolve()
    result = (root / relative).resolve()
    if root not in result.parents and result != root:
        raise ManifestError(f"Output path escapes project root: {relative}")
    return result


def iter_crop_specs(manifest: dict[str, Any]):
    bg = manifest.get("background")
    if bg:
        yield bg, "normal", bg
    for element in manifest.get("elements", []):
        if element.get("type") != "label":
            yield element, "normal", element
            if element.get("type") == "button":
                for state_name, state in element.get("states", {}).items():
                    if state.get("output"):
                        merged = dict(element)
                        merged.update(state)
                        merged["bbox_units"] = state.get("bbox_units", element.get("bbox_units", manifest.get("bbox_units", "normalized")))
                        if "bbox" not in state:
                            merged["bbox"] = element["bbox"]
                        yield element, state_name, merged


def gd_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return f'"{escaped}"'


def node_name(element_id: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in element_id.split("_"))


def method_name(action: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_]+", "_", action.strip()).strip("_").lower()
    if not clean:
        clean = "ui_action"
    if clean[0].isdigit():
        clean = "action_" + clean
    return f"_on_{clean}_pressed"
