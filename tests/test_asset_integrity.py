#!/usr/bin/env python3
"""Real-image regressions for transparency, preset approvals, and safe reuse."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPTS = Path(__file__).resolve().parents[1] / "skill" / "progress-bar-studio" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from asset_validation import config_sha256


def run(*args, expected=0):
    result = subprocess.run([str(arg) for arg in args], capture_output=True, text=True)
    if result.returncode != expected:
        raise AssertionError(f"Expected {expected}, got {result.returncode}: {result.stderr}\n{result.stdout}")
    return result


class AssetIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sheet = self.root / "sheet.png"
        image = Image.new("RGBA", (128, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        for index in range(4):
            draw.rectangle((index * 32 + 8 + index, 6, index * 32 + 23, 25), fill=(50 + index * 30, 120, 70, 255))
        image.save(self.sheet)
        self.cycle = self.root / "cycle"
        self.library = self.root / "library"

    def tearDown(self):
        self.temp.cleanup()

    def split(self, source=None, *extra, expected=0):
        return run(sys.executable, SCRIPTS / "split_walk_cycle.py", "--input", source or self.sheet,
                   "--out-dir", self.cycle, *extra, expected=expected)

    def save(self, *extra, approved=True, mode="walk-cycle", expected=0):
        args = [sys.executable, SCRIPTS / "preset_library.py", "save", "--name", "Test style",
                "--library-dir", self.library, "--character-mode", mode, "--style", "S2",
                "--style-variant", "segmented-soft-runway", "--palette", "primary=#247A63",
                "--overlay-scale", "1", "--placement", "top", "--position-x", "0", "--position-y", "32"]
        if mode == "walk-cycle":
            args += ["--character-cycle-dir", self.cycle]
        if approved:
            args += ["--sample-approved", "--final-export-approved"]
        return run(*args, *extra, "--json", expected=expected)

    def show(self, path, *extra, expected=0):
        return run(sys.executable, SCRIPTS / "preset_library.py", "show", "--preset", path,
                   *extra, "--json", expected=expected)

    def manifest(self):
        return self.cycle / "character-walk-cycle.json"

    def edit_manifest(self, change):
        path = self.manifest()
        value = json.loads(path.read_text())
        change(value)
        path.write_text(json.dumps(value))

    def test_split_rejects_opaque_jpeg_and_rgba_before_writing(self):
        for mode, extension in (("RGB", "jpg"), ("RGBA", "png")):
            with self.subTest(mode=mode):
                source = self.root / f"opaque.{extension}"
                Image.new(mode, (128, 32), "white").save(source)
                self.split(source, expected=1)
                self.assertFalse(self.cycle.exists())

    def test_split_rejects_empty_or_opaque_cell_without_partial_outputs(self):
        for fill in ((0, 0, 0, 0), (255, 255, 255, 255)):
            with self.subTest(fill=fill):
                with Image.open(self.sheet) as image:
                    image.paste(fill, (96, 0, 128, 32))
                    source = self.root / "bad-cell.png"
                    image.save(source)
                self.split(source, expected=1)
                self.assertFalse(self.cycle.exists())

    def test_split_rejects_unsafe_prefix_and_invalid_fps(self):
        for extra in (("--prefix", "../escape"), ("--fps", "nan"), ("--fps", "0")):
            self.split(None, *extra, expected=1)
            self.assertFalse(self.cycle.exists())

    def test_save_requires_both_approval_records(self):
        for extra in ((), ("--sample-approved",), ("--final-export-approved",)):
            self.save(*extra, approved=False, mode="none", expected=2)
            self.assertFalse((self.library / "test-style").exists())

    def test_verified_preset_rejects_missing_visual_configuration(self):
        # Missing fields must not become eligible for the complete-reuse card.
        args = [sys.executable, SCRIPTS / "preset_library.py", "save", "--name", "Incomplete",
                "--library-dir", self.library, "--character-mode", "none", "--style", "S2",
                "--sample-approved", "--final-export-approved", "--json"]
        run(*args, expected=2)
        self.assertFalse((self.library / "incomplete").exists())
        for extra in (("--style-variant", ""), ("--overlay-scale", "nan"), ("--placement", ""),
                      ("--position-x", "nan")):
            self.save(*extra, mode="none", expected=2)
            self.assertFalse((self.library / "test-style").exists())

    def test_preview_must_match_approved_frame_order_and_timing(self):
        self.split()
        preview = self.cycle / "character-walk-preview.webp"
        original = preview.read_bytes()
        frames = [Image.open(self.cycle / f"character-walk-frame-{index:02d}.png").convert("RGBA")
                  for index in range(1, 5)]
        for sequence, duration in ((list(reversed(frames)), 125), (frames, 500)):
            sequence[0].save(preview, "WEBP", save_all=True, append_images=sequence[1:],
                             duration=duration, loop=0, lossless=True)
            self.save(expected=2)
            self.assertFalse((self.library / "test-style").exists())
            preview.write_bytes(original)

    def test_round_trip_verifies_and_copies_only_required_assets(self):
        self.split()
        (self.cycle / "unrelated-private-notes.txt").write_text("Not part of the cycle")
        payload = json.loads(self.save("--set-default").stdout)
        path = Path(payload["preset"])
        data = json.loads(self.show(path, "--require-verified").stdout)
        self.assertEqual(data["status"], "verified")
        self.assertTrue(data["reuseEligible"])
        self.assertTrue(data["sampleApproved"] and data["finalExportApproved"])
        self.assertEqual(len(data["assetChecksums"]), 7)
        self.assertFalse(list(path.parent.rglob("unrelated-private-notes.txt")))
        self.assertEqual(json.loads(Path(payload["defaultPreset"]).read_text())["preset"], str(path))

    def test_missing_or_modified_asset_blocks_reuse(self):
        self.split()
        path = Path(json.loads(self.save().stdout)["preset"])
        data = json.loads(path.read_text())
        frame = path.parent / data["character"]["cycle"]["frames"][0]
        original = frame.read_bytes()
        frame.write_bytes(b"broken PNG")
        inspected = json.loads(self.show(path).stdout)
        self.assertEqual(inspected["status"], "invalid")
        self.assertFalse(inspected["reuseEligible"])
        self.show(path, "--require-verified", expected=2)
        frame.write_bytes(original)
        self.assertTrue(json.loads(self.show(path).stdout)["reuseEligible"])
        frame.unlink()
        self.show(path, "--require-verified", expected=2)

    def test_valid_image_tampering_fails_checksum_even_when_layout_matches(self):
        self.split()
        path = Path(json.loads(self.save().stdout)["preset"])
        data = json.loads(path.read_text())
        preview = path.parent / "assets/walk-cycle/character-walk-preview.webp"
        # Metadata-only change leaves a valid, visually identical image.
        preview.write_bytes(preview.read_bytes() + b"changed")
        self.assertFalse(json.loads(self.show(path).stdout)["reuseEligible"])

    def test_changed_visual_configuration_is_not_verified(self):
        path = Path(json.loads(self.save(mode="none").stdout)["preset"])
        data = json.loads(path.read_text())
        data["palette"] = {"primary": "#000000"}
        path.write_text(json.dumps(data))
        self.assertFalse(json.loads(self.show(path).stdout)["reuseEligible"])

    def test_legacy_versions_are_readable_but_never_quietly_verified(self):
        for version in (1, 2, 3):
            path = self.root / f"legacy-{version}.json"
            path.write_text(json.dumps({"schemaVersion": version, "name": "Older style", "status": "verified"}))
            result = json.loads(self.show(path).stdout)
            self.assertEqual(result["status"], "unverified")
            self.assertFalse(result["reuseEligible"])
            self.assertTrue(result["inspectionIssues"])
            self.show(path, "--require-verified", expected=2)

    def test_rejects_non_object_json_without_traceback(self):
        path = self.root / "bad.json"
        path.write_text("[]")
        result = self.show(path, expected=2)
        self.assertNotIn("Traceback", result.stderr)

    def test_cycle_rejects_traversal_absolute_and_symlink_assets(self):
        self.split()
        original = self.manifest().read_text()
        outside = self.root / "outside.png"
        shutil.copy2(self.sheet, outside)
        link = self.cycle / "linked.png"
        link.symlink_to(outside)
        for unsafe in ("../outside.png", str(outside), "linked.png"):
            with self.subTest(path=unsafe):
                self.manifest().write_text(original)
                self.edit_manifest(lambda manifest: manifest["frames"].__setitem__(0, unsafe))
                self.save(expected=2)
                self.assertFalse((self.library / "test-style").exists())

    def test_show_rejects_outside_asset_even_with_recomputed_config_checksum(self):
        self.split()
        path = Path(json.loads(self.save().stdout)["preset"])
        data = json.loads(path.read_text())
        data["character"]["cycle"]["manifest"] = "../../outside-cycle.json"
        data["configSha256"] = config_sha256(data)
        path.write_text(json.dumps(data))
        self.assertFalse(json.loads(self.show(path).stdout)["reuseEligible"])

    def test_cycle_rejects_fake_frame_and_mismatched_sprite(self):
        self.split()
        frame = self.cycle / "character-walk-frame-01.png"
        original = frame.read_bytes()
        for replacement in (b"not a PNG", None):
            if replacement:
                frame.write_bytes(replacement)
            else:
                with Image.open(frame) as image:
                    image.putpixel((10, 10), (255, 0, 255, 255))
                    image.save(frame)
            self.save(expected=2)
            self.assertFalse((self.library / "test-style").exists())
            frame.write_bytes(original)

    def test_single_pose_requires_real_transparency(self):
        opaque = self.root / "opaque.png"
        Image.new("RGBA", (32, 32), "white").save(opaque)
        self.save("--character-image", opaque, mode="single-pose", expected=2)
        with Image.open(self.sheet) as sheet:
            sheet.crop((0, 0, 32, 32)).save(self.root / "pose.png")
        path = Path(json.loads(self.save("--character-image", self.root / "pose.png", mode="single-pose").stdout)["preset"])
        self.assertTrue(json.loads(self.show(path).stdout)["reuseEligible"])

    def test_no_character_invariant_and_no_overwrite(self):
        self.save("--character-image", self.sheet, mode="none", expected=2)
        path = Path(json.loads(self.save(mode="none").stdout)["preset"])
        original = path.read_bytes()
        self.save(mode="none", expected=2)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(json.loads(path.read_text())["assetChecksums"], {})

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
    def test_multibg_uses_custom_color_and_preserves_default(self):
        image = self.root / "transparent.png"
        Image.new("RGBA", (32, 32), (0, 0, 0, 0)).save(image)
        for suffix, color in (("default", None), ("green", "#00FF00")):
            output = self.root / f"{suffix}.png"
            args = [SCRIPTS / "make_multibg_preview.sh", image, output]
            if color:
                args.append(color)
            run(*args)
            with Image.open(output) as result:
                self.assertEqual(result.size, (64, 96))
                pixel = result.convert("RGB").getpixel((16, 80))
                expected = (251, 234, 240) if color is None else (0, 255, 0)
                self.assertTrue(all(abs(actual - target) <= 5 for actual, target in zip(pixel, expected)), pixel)
        bad = self.root / "bad.png"
        run(SCRIPTS / "make_multibg_preview.sh", image, bad, "red;evil", expected=64)
        self.assertFalse(bad.exists())


if __name__ == "__main__":
    unittest.main()
