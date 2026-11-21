# Godot 4 layout and validation notes

## Generated layout strategy

The generator maps each bounding box to proportional `Control` anchors and sets offsets to zero. The element therefore keeps its proportional position and size relative to its parent. This is a practical first pass for matching a single reference aspect ratio.

It is not a complete responsive-layout system. For materially different aspect ratios, review the scene and replace selected proportional anchors with container-based or edge/center-anchored layout. Keep important buttons within mobile safe areas. Test at the project's intended resolutions.

## Node mapping

| Art / content | Node |
|---|---|
| Full-screen background | `TextureRect` |
| Static art, logo, portrait, icon | `TextureRect` |
| Art-driven interactive button | `TextureButton` |
| Stretchable frame/panel | `NinePatchRect` |
| Editable text | `Label` |
| Screen root | `Control` |

`TextureButton` supports normal, hover, pressed, disabled, and focused textures. The generated scene currently wires normal/hover/pressed/disabled when supplied. Add keyboard focus and controller navigation intentionally when required.

## Recommended project settings

Set the project's design resolution to `project.design_size` using Project Settings → Display → Window → Size. Choose the project's content scale mode and aspect policy deliberately; do not let a generated skill silently rewrite `project.godot`. A Canvas Items scale mode is commonly useful for UI, but the correct choice depends on whether the game is 2D, 3D, desktop, or mobile.

## Command-line checks

From a terminal with Godot 4 available:

```bash
godot --version
godot --headless --path /path/to/project --editor --quit --import
godot --headless --path /path/to/project --scene res://scenes/ui/main_menu.tscn --quit-after 2
```

`--headless` suppresses window creation; `--editor --quit --import` imports project resources and exits. A short scene run can still reveal load-time errors, but it does not replace visual inspection in the editor.

## Nine-patch notes

`NinePatchRect` preserves the four corners while stretching or tiling the edges and center. Set `patch_margin_left`, `patch_margin_top`, `patch_margin_right`, and `patch_margin_bottom` based on the exported crop's border thickness. Keep each margin smaller than the corresponding texture dimension and visually inspect the result.
