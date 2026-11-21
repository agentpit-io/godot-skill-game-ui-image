---
name: game-ui-image-to-godot
description: Convert game UI mockups, screenshots, or design images into organized image assets and Godot 4 Control-based scenes. Use when a user asks to inspect or slice a game interface image, create UI atlases or PNG parts, generate .tscn/.gd files, wire TextureButtons, or rebuild a Godot UI from a visual reference. Do not use for general gameplay coding unrelated to UI assets or interface reconstruction.
---

# Game UI Image to Godot 4

Turn a flattened or layered game-interface design into a maintainable Godot 4 UI implementation. This skill includes deterministic Python helpers for image inspection, rectangle-based cropping, and `.tscn`/`.gd` generation.

## Core rules

1. **Inspect before editing.** Read the target project's `AGENTS.md`, existing scene conventions, `project.godot`, and relevant UI scenes before writing files. Preserve existing code and naming conventions where practical.
2. **Do not pretend a crop is segmentation.** A bounding-box crop copies pixels inside a rectangle; it does not remove a baked-in background, separate overlapping artwork, or recreate hidden pixels. Keep the original flattened design as a reference/background unless the user provides transparent layers or authorizes a background-removal/inpainting tool.
3. **Use vision for recognition, scripts for exact repeatable work.** Inspect the image visually and propose element IDs, types, and bounding boxes. Use the Python tools to crop exactly those boxes. Ask for confirmation only when ambiguity could materially change the result; otherwise create a clearly labelled draft manifest and report uncertain boxes.
4. **Keep text editable.** Prefer Godot `Label` nodes over rasterized text. For a button with baked-in lettering, do not add a duplicate Label.
5. **Use Control UI nodes.** Typical mapping: background/image → `TextureRect`; art button → `TextureButton`; resizable frame → `NinePatchRect`; text → `Label`; root → `Control`.
6. **Respect the project.** Do not overwrite existing `.tscn`, `.gd`, images, or `project.godot` without checking and obtaining explicit approval or using an explicit `--force` requested by the user. Never change the main scene or project-wide stretch settings silently.
7. **Validate.** If the Godot executable is available, import and open the generated scene headlessly. If not, run Python validation and state that Godot runtime validation was not performed.

## Workflow

### 1. Locate the project and reference image

- Identify the Godot project root (the folder containing `project.godot`).
- Locate the design image and determine its pixel dimensions.
- If either path is missing, ask one concise question. Do not create an unrelated new project unless requested.
- Prefer PNG for assets with transparency. Keep the original reference image unchanged.

### 2. Inspect the design image and create a manifest draft

Run from the skill directory or use the full script path:

```bash
python scripts/inspect_design.py /path/to/main_menu.png --output /path/to/ui_manifest.json --project-name MainMenu
```

The tool reports dimensions and creates a starter manifest. It does **not** detect controls by itself. Use visual understanding to fill `background` and `elements` with `bbox` values in `ui_manifest.json`.

Bounding boxes use `[x, y, width, height]`. The default `bbox_units` is `normalized` (0–1 relative to the source image). Use `pixels` for integer pixel coordinates. The box should include the complete visible component and a small transparent/visual margin where necessary.

Supported element types:

- `background`: full-screen image. Usually placed in the top-level `background` field.
- `image`: non-interactive visual such as logo, portrait, or icon.
- `button`: `TextureButton` with optional hover/pressed/disabled state crops and editable text overlay.
- `panel`: `NinePatchRect`, using optional `nine_patch` margins in pixels of the exported panel image.
- `label`: editable `Label`, no image crop required.

A button's `states` object may contain `hover`, `pressed`, and `disabled` entries. Each state can override `source`, `bbox`, `bbox_units`, and `output`. If a state has no `bbox`, it reuses the element's box; if it has no `output`, the generator omits that state.

### 3. Validate and crop assets

Read `references/manifest-reference.md` and validate the manifest. Then run:

```bash
python scripts/slice_assets.py /path/to/ui_manifest.json --project-root /path/to/godot-project
```

The script writes crops to each element's project-relative `output` path. It preserves alpha when present. Source paths are relative to the manifest file (or absolute); output paths must stay inside the Godot project. Existing output files are never replaced unless `--force` is passed.

Create a visual review sheet from the crop report:

```bash
python scripts/make_contact_sheet.py /path/to/godot-project/.ui-slicing-report.json --output /path/to/godot-project/ui_contact_sheet.png
```

Inspect the contact sheet and correct uncertain boxes in the manifest before scene generation.

### 4. Generate Godot scenes and scripts

After all referenced PNGs exist, run:

```bash
python scripts/generate_godot_ui.py /path/to/ui_manifest.json --project-root /path/to/godot-project
```

The generator creates the configured `.tscn` and `.gd` paths. It fails rather than overwrite existing outputs unless `--force` is passed. It generates:

- A full-rect `Control` root.
- An optional full-rect background `TextureRect`.
- `TextureRect` nodes for image elements.
- `TextureButton` nodes with optional state textures.
- Child `Label` nodes for editable button text when `text` is non-empty.
- `NinePatchRect` nodes for panels.
- `Label` nodes for text-only elements.
- Signal connections to generated handler stubs in the scene script.

The generator uses normalized anchors derived from each bounding box. This preserves relative positions and sizes as the parent changes, but very different aspect ratios still require visual review and potentially manual anchor/container adjustments. The scene is a starting point, not a substitute for device testing.

### 5. Run Godot validation

If `godot` (or a versioned binary such as `godot4`) is on `PATH`, validate with:

```bash
godot --headless --path /path/to/godot-project --editor --quit --import
godot --headless --path /path/to/godot-project --scene res://scenes/ui/main_menu.tscn --quit-after 2
```

Replace the scene path with the manifest's `project.scene_path`. On Windows, use the executable's full path or the PowerShell command name configured on that machine. Godot's command-line flags vary slightly by version; consult `godot --help` if a flag is unavailable.

If validation fails, capture the full error, fix only the generated files or clearly attributable integration issue, and rerun. Do not claim the scene runs if Godot is unavailable or no run was performed.

### 6. Final report

Report:

- Original image dimensions and design resolution.
- Cropped assets and their output paths.
- Generated scene and script paths.
- Any uncertain/overlapping crops or baked-in text/backgrounds.
- Godot validation command and its actual result.
- Remaining manual work such as responsive layout tuning, font import, localization, or button actions.

## Manifest example

See `examples/main_menu_manifest.json` and `schemas/ui-manifest.schema.json`. Keep the JSON as the source of truth for crop rectangles and element metadata so the UI can be regenerated.

## Troubleshooting

- **Wrong crop:** correct the bounding box in the manifest; do not patch the output PNG by hand unless the user wants a manual art edit.
- **Transparent edges are important:** keep the full rectangle; do not auto-trim alpha because it changes the visual alignment relative to the design coordinates.
- **Nine-patch corners distort:** adjust `nine_patch.left/top/right/bottom` to the border thickness measured in the exported crop.
- **Buttons look stretched:** inspect texture aspect ratio and button bounds; use different state assets with matching dimensions, then adjust layout.
- **Different screen aspect ratios:** test the project's target ratios; move from proportional anchors to containers or custom anchors for elements that should retain fixed size.
- **Scene does not open:** check `res://` paths, resource declarations, node names, script syntax, and the Godot version. Use `--headless --editor --quit --import` to reveal import/parser errors.
