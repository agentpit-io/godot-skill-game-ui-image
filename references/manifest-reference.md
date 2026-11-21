# UI manifest reference

The manifest is the machine-readable source of truth for slicing and scene generation. Use `examples/main_menu_manifest.json` as a complete example.

## Top-level fields

| Field | Required | Meaning |
|---|---:|---|
| `schema_version` | yes | Currently `1`. |
| `project.name` | yes | Godot scene root node name. |
| `project.design_size` | yes | `[width, height]` of the reference design. |
| `project.scene_path` | yes | Generated `.tscn`, relative to Godot project root. |
| `project.script_path` | yes | Generated `.gd`, relative to Godot project root. |
| `source_image` | yes | Source image path relative to manifest file, or absolute path. |
| `bbox_units` | no | `normalized` (default) or `pixels`. |
| `background` | no | One full-screen crop specification. |
| `elements` | yes | Ordered UI element specifications; generator sorts by `z_index`. |

## Element fields

Common fields:

- `id`: unique lowercase identifier matching `^[a-z][a-z0-9_]*$`.
- `type`: `image`, `button`, `panel`, or `label` (background field also accepts `background`).
- `bbox`: `[x, y, width, height]` in the selected units.
- `bbox_units`: optional override of the global setting.
- `source`: optional alternate source image; relative to the manifest file or absolute.
- `output`: required PNG path relative to the Godot project root for all non-label elements.
- `padding`: optional crop padding, either one integer or `[left, top, right, bottom]`, in source-image pixels.
- `z_index`: optional CanvasItem draw order. Larger values are drawn in front.

Normalized boxes are fractions of the source image: `[0.1, 0.2, 0.3, 0.1]` means x=10%, y=20%, width=30%, height=10%. Pixel boxes use source-image pixels. Boxes must remain within the source image; padding is clipped at the image edge.

## Element types

### image

Creates a `TextureRect`. Optional `stretch_mode` is a Godot `TextureRect.StretchMode` integer (default `5`, keep aspect centered). Prefer semantic settings over arbitrary numbers; available values are documented in `class_texturerect`.

### button

Creates a `TextureButton`. The normal state is `output`. Optional state crops:

```json
"states": {
  "hover": {"bbox": [0.1, 0.2, 0.2, 0.1], "output": "assets/ui/play_hover.png"},
  "pressed": {"bbox": [0.1, 0.3, 0.2, 0.1], "output": "assets/ui/play_pressed.png"},
  "disabled": {"source": "design/disabled.png", "bbox": [0, 0, 1, 1], "output": "assets/ui/play_disabled.png"}
}
```

A state can override `source`, `bbox`, `bbox_units`, and `padding`; omitted values inherit the parent element. If `text` is non-empty, a centered child `Label` is created. Leave `text` empty/omitted when the image already contains lettering. `action` becomes the generated signal handler name; e.g. `start_game` creates `_on_start_game_pressed()`.

### panel

Creates a `NinePatchRect`. Optional `nine_patch` margins are integers in pixels measured on the **exported crop**, not the original full image:

```json
"nine_patch": {"left": 28, "top": 28, "right": 28, "bottom": 28}
```

### label

Creates an editable `Label` and does not crop an image. Requires `text`. Optional `font_size`, `font_color` (`#RRGGBB`, `#RRGGBBAA`, or normalized `[r,g,b,a]`), `horizontal_alignment` (0 left, 1 center, 2 right), and `vertical_alignment` (0 top, 1 center, 2 bottom).

## Safety and path rules

All generated output paths must be project-relative and cannot contain `..` or be absolute. Source image paths may be absolute or relative to the manifest file. The scripts do not overwrite existing crop, scene, or script files unless `--force` is explicitly passed.
