from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class PipelineSmokeTest(unittest.TestCase):
    def test_inspect_slice_generate(self):
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            project = temp / "godot_project"
            project.mkdir()
            (project / "project.godot").write_text("config_version=5\n", encoding="utf-8")
            design_dir = temp / "design"
            design_dir.mkdir()
            img_path = design_dir / "menu.png"
            img = Image.new("RGBA", (200, 100), (30, 40, 50, 255))
            draw = ImageDraw.Draw(img)
            draw.rectangle((20, 20, 79, 49), fill=(255, 0, 0, 255))
            draw.rectangle((100, 20, 179, 59), fill=(0, 255, 0, 255))
            img.save(img_path)

            manifest_path = temp / "ui_manifest.json"
            subprocess.run([sys.executable, str(SCRIPTS / "inspect_design.py"), str(img_path), "--output", str(manifest_path)], check=True)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["background"] = {
                "id": "background", "type": "background", "bbox": [0, 0, 1, 1],
                "output": "assets/ui/background.png", "fit": "cover"
            }
            manifest["elements"] = [
                {"id": "play_button", "type": "button", "bbox": [0.1, 0.2, 0.3, 0.3],
                 "output": "assets/ui/play.png", "text": "Play", "action": "start_game",
                 "states": {"hover": {"bbox": [0.5, 0.2, 0.4, 0.4], "output": "assets/ui/play_hover.png"}}},
                {"id": "caption", "type": "label", "bbox": [0.1, 0.7, 0.5, 0.1], "text": "Hello", "font_size": 24}
            ]
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            subprocess.run([sys.executable, str(SCRIPTS / "validate_manifest.py"), str(manifest_path), "--check-source"], check=True)
            subprocess.run([sys.executable, str(SCRIPTS / "slice_assets.py"), str(manifest_path), "--project-root", str(project)], check=True)
            subprocess.run([sys.executable, str(SCRIPTS / "make_contact_sheet.py"), str(project / ".ui-slicing-report.json"), "--output", str(project / "ui_contact_sheet.png")], check=True)
            subprocess.run([sys.executable, str(SCRIPTS / "generate_godot_ui.py"), str(manifest_path), "--project-root", str(project)], check=True)

            scene = (project / "scenes/ui/main_menu.tscn").read_text(encoding="utf-8")
            script = (project / "scripts/ui/main_menu.gd").read_text(encoding="utf-8")
            self.assertIn('type="TextureButton"', scene)
            self.assertIn('signal="pressed"', scene)
            self.assertIn("_on_start_game_pressed", script)
            self.assertTrue((project / "assets/ui/play_hover.png").is_file())
            self.assertTrue((project / "ui_contact_sheet.png").is_file())


if __name__ == "__main__":
    unittest.main()
