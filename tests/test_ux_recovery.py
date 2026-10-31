"""Reproduce user-facing recovery failures with isolated fixtures."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skill/progress-bar-studio/scripts"
sys.path.insert(0, str(SCRIPTS))
import style_router


class UXRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def command(self, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / "preset_library.py"), *map(str, args)],
                              capture_output=True, text=True)

    def test_missing_pillow_blocks_every_local_render_mode(self):
        result = subprocess.run([sys.executable, "-S", str(SCRIPTS / "preflight.py"), "--json"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        data = json.loads(result.stdout)
        self.assertFalse(data["ok"])
        self.assertIn("PILLOW_MISSING", data["blockers"])
        self.assertFalse(data["capabilities"]["pillow"])
        self.assertTrue(data["capabilities"]["imageEditing"].startswith("unknown"))
        self.assertTrue(data["capabilities"]["transcription"].startswith("unknown"))
        self.assertTrue(any("no-character mode also requires it" in action for action in data["nextActions"]))

    def test_absent_default_is_a_normal_first_project(self):
        result = self.command("show", "--default", "--library-dir", self.base, "--require-verified", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "not_found")
        self.assertFalse(data["reuseEligible"])
        self.assertEqual(list(self.base.iterdir()), [])

    def test_default_pointer_resolves_and_verifies_actual_saved_preset(self):
        result = self.command("save", "--name", "Test style", "--library-dir", self.base,
                              "--character-mode", "none", "--style", "S3", "--style-variant", "text",
                              "--palette", "text=#183D39", "--overlay-scale", "1", "--placement", "bottom",
                              "--position-x", "0", "--position-y", "0", "--sample-approved",
                              "--final-export-approved", "--set-default", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads(result.stdout)
        pointer_before = (self.base / "default-preset.json").read_bytes()
        shown = self.command("show", "--default", "--library-dir", self.base, "--require-verified", "--json")
        self.assertEqual(shown.returncode, 0, shown.stderr)
        actual = json.loads(shown.stdout)
        self.assertEqual(actual["preset"], saved["preset"])
        self.assertTrue(actual["reuseEligible"])
        self.assertEqual((self.base / "default-preset.json").read_bytes(), pointer_before)

    def test_default_cannot_silently_follow_an_outside_pointer(self):
        library = self.base / "library"
        library.mkdir()
        outside = self.base / "outside.json"
        outside.write_text(json.dumps({"name": "old", "schemaVersion": 1}))
        (library / "default-preset.json").write_text(json.dumps({"preset": str(outside)}))
        result = self.command("show", "--default", "--library-dir", library, "--json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside its library", result.stderr)
        self.assertEqual(json.loads(outside.read_text())["name"], "old")

    def test_none_profile_preserves_known_fields_without_character_tasks(self):
        data = {"style": {"preset": "S1", "palette": {"text": "#183D39"}},
                "placement": {"x": 0, "y": 0}, "character": {"mode": "none"}}
        report = style_router.inspect_config(data, self.base)
        self.assertIn("style.palette", report["knownFields"])
        self.assertIn("per-frame foot anchors", report["notApplicable"])
        self.assertFalse(any("anchor" in field for field in report["manualFields"]))
        self.assertTrue(report["nextActions"])
        self.assertFalse(report["automaticMigration"])
        top_level = {"style": {"preset": "S1"}, "palette": {"text": "#183D39"},
                     "character": {"mode": "none"}}
        diagnosed = style_router.inspect_config(top_level, self.base)
        self.assertTrue(any(field.startswith("palette ") for field in diagnosed["knownFields"]))
        top_level["style"]["palette"] = {"text": "#111111"}
        diagnosed = style_router.inspect_config(top_level, self.base)
        self.assertTrue(diagnosed["conflicts"])
        self.assertEqual(top_level["palette"]["text"], "#183D39")

    def test_visible_board_options_map_to_the_correct_compatibility_route(self):
        options = {item["option"]: item for item in style_router.creator_catalog()}
        self.assertEqual(len(options), 8)
        self.assertEqual(set(options), {1, 2, 7, 8, 10, 11, 13, 15})
        self.assertEqual(options[7]["styleKey"], "classic:S7")
        self.assertEqual(options[8]["styleKey"], "gallery:01")
        self.assertEqual(options[15]["styleKey"], "gallery:08")
        self.assertEqual(style_router.resolve_style("S6", style_router.INSTALLED_ORIGIN), "legacy:S6")


if __name__ == "__main__":
    unittest.main()
