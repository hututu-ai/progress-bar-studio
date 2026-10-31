"""Source-qualified compatibility with independent temporary, synthetic inputs."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skill/progress-bar-studio/scripts"
sys.path.insert(0, str(SCRIPTS))
import style_router as router


class StyleRouterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        font = str(router.classic.choose_font(None, self.base))
        self.raw = {"style": "01", "outputWidth": 480, "displayWidth": 480,
                    "fontRegular": font, "fontBold": font, "labelSize": 18, "kickerSize": 11,
                    "progressMode": "chapter-weighted", "character": {"mode": "none"},
                    "palette": {"surface": "#FFFFFF", "active": "#19766C", "inactive": "#DDECEA",
                                "pill": "#EEF6F4", "text": "#183D39", "quiet": "#56736F",
                                "outline": "#BCD8D2", "selected": "#176558", "onSelected": "#FFFFFF"}}
        self.timeline = {"duration": 10, "fps": 24, "chapters": [
            {"start": 0, "label": "开场", "kicker": "开场", "segmentId": "test-1"},
            {"start": 3, "label": "安装", "kicker": "第一步", "segmentId": "test-2"},
            {"start": 7, "label": "验证", "kicker": "第二步", "segmentId": "test-3"}]}

    def routed(self, raw=None, timeline=None):
        return router.migrate_config(raw or self.raw, router.INSTALLED_ORIGIN,
                                     self.base, self.base, timeline or self.timeline)

    def test_catalog_exposes_all_eight_gallery_and_seven_classic_routes(self):
        keys = {entry["styleKey"] for entry in router.catalog()}
        self.assertEqual(keys, {f"gallery:{i:02d}" for i in range(1, 9)} |
                         {f"classic:S{i}" for i in range(1, 8)})
        for key in keys:
            self.assertEqual(router.resolve_style(key), key)
        self.assertEqual(len(router.catalog(True)), 23)

    def test_unqualified_styles_are_never_guessed_and_old_meanings_remain(self):
        for value in ("S1", "S5", "S6", "S7", "01", "R1"):
            with self.assertRaisesRegex(router.classic.ConfigError, "explicit origin"):
                router.resolve_style(value)
        expected = {"S5": "里程碑圆点", "S6": "章节卡片", "S7": "书签页签"}
        for native, name in expected.items():
            old = router.resolve_style(native, router.INSTALLED_ORIGIN)
            new = router.resolve_style(native, router.CLASSIC_ORIGIN)
            self.assertEqual(old, "legacy:" + native)
            self.assertEqual(router.REGISTRY[old]["name"], name)
            self.assertEqual(new, "classic:" + native)
            self.assertNotEqual(router.REGISTRY[old]["name"], router.REGISTRY[new]["name"])
        with self.assertRaisesRegex(router.classic.ConfigError, "S4"):
            router.resolve_style("S4", router.INSTALLED_ORIGIN)
        with self.assertRaises(router.classic.ConfigError):
            router.resolve_style("classic:S6", router.INSTALLED_ORIGIN)

    def test_eight_legacy_aliases_resolve_to_the_original_geometry(self):
        expected = ["S1", "R1", "R2", "R3", "R4", "R5", "R6", "R7"]
        for i, native in enumerate(expected, 1):
            key = router.resolve_style(str(i), router.INSTALLED_ORIGIN)
            self.assertEqual(key, f"gallery:{i:02d}")
            self.assertEqual(router.REGISTRY[key]["nativeStyle"], native)
            if native.startswith("R"):
                self.assertEqual(router.resolve_style(native, router.INSTALLED_ORIGIN), key)

    def test_all_gallery_migrations_preserve_fields_and_preview_pixels(self):
        for code in (f"{i:02d}" for i in range(1, 9)):
            raw = copy.deepcopy(self.raw)
            raw["style"] = code
            before = copy.deepcopy(raw)
            timeline = copy.deepcopy(self.timeline)
            migrated = self.routed(raw)
            self.assertEqual(raw, before)
            self.assertEqual(migrated["rendererConfig"], before)
            self.assertEqual(migrated["timeline"], timeline)
            direct = router.Overlay(raw, timeline["chapters"], 10, self.base)
            after = router.build_renderer(migrated, self.base)
            self.assertEqual(after.overlay.progress_mode, "chapter-weighted")
            for time in (0, 2.999, 3, 6.999, 7, 10):
                with self.subTest(style=code, time=time):
                    self.assertEqual(direct.frame(time).tobytes(), after.frame(time).tobytes())
                    self.assertEqual(after.frame(time).getchannel("A").getextrema(), (0, 255))

    def test_all_historical_s_styles_keep_original_pixels(self):
        for native in ("S1", "S2", "S3", "S5", "S6", "S7", "S8", "S9"):
            raw = self.raw | {"style": native}
            migrated = self.routed(raw)
            self.assertEqual(migrated["styleKey"], "legacy:" + native)
            direct = router.Overlay(raw, self.timeline["chapters"], 10, self.base)
            after = router.build_renderer(migrated, self.base)
            self.assertEqual(direct.frame(3.5).tobytes(), after.frame(3.5).tobytes())

    def test_seven_new_styles_remain_selectable_without_geometry_changes(self):
        for i in range(1, 8):
            config = router.classic.demo_config(f"S{i}")
            data = {"schemaVersion": 1, "styleKey": f"classic:S{i}", "rendererConfig": config}
            before = router.classic.Renderer(router.classic.validate_config(config, self.base))
            after = router.build_renderer(data, self.base)
            self.assertEqual(before.frame(3).tobytes(), after.frame(3).tobytes())

    def test_namespace_conflict_unknown_fields_and_hidden_assets_fail(self):
        data = self.routed()
        data["styleKey"] = "gallery:06"
        with self.assertRaisesRegex(router.classic.ConfigError, "conflicts"):
            router.build_renderer(data, self.base)
        with self.assertRaisesRegex(router.classic.ConfigError, "unmapped"):
            self.routed(self.raw | {"unexpectedScale": 2})
        data = self.routed(self.raw | {"character": {"mode": "none", "frames": ["private.png"]}})
        with self.assertRaisesRegex(router.classic.ConfigError, "hidden"):
            router.build_renderer(data, self.base)
        with self.assertRaisesRegex(router.classic.ConfigError, "unknown stable"):
            router.resolve_style("gallery:09")

    def test_relocated_config_preserves_relative_assets_and_cycle_fields(self):
        source, target = self.base / "source", self.base / "migrated"
        source.mkdir(); target.mkdir()
        font = source / "font.otf"
        shutil.copyfile(self.raw["fontRegular"], font)
        frames = []
        for i in range(4):
            path = source / f"f{i}.png"
            image = Image.new("RGBA", (64, 64))
            draw = ImageDraw.Draw(image)
            draw.rectangle((20+i, 5, 40+i, 60), fill="#19766C")
            # Real shape changes: a translated rectangle is not a walking cycle.
            draw.rectangle((35, 45-i*3, 44+i, 51-i*2), fill='#19766C')
            image.save(path)
            frames.append(path.name)
        character = {"mode": "four-frame", "frames": frames,
                     "anchors": [{"x": 32, "y": 60}] * 4, "cycleFps": 6, "visibleHeight": 42}
        raw = self.raw | {"fontRegular": "font.otf", "fontBold": "font.otf", "character": character}
        before = copy.deepcopy(raw)
        migrated = router.migrate_config(raw, router.INSTALLED_ORIGIN, source, target, self.timeline)
        self.assertEqual(migrated["rendererConfig"], before)
        self.assertEqual(migrated["assetBase"], "../source")
        self.assertEqual(sorted(p.name for p in target.iterdir()), [])
        direct = router.Overlay(raw, self.timeline["chapters"], 10, source)
        after = router.build_renderer(migrated, target)
        for time in (0, 1/6, 2/6, 3/6, 10):
            self.assertEqual(direct.frame(time).tobytes(), after.frame(time).tobytes())
        self.assertEqual(raw, before)

    def test_defaults_are_frozen_only_for_explicit_legacy_migration(self):
        raw = copy.deepcopy(self.raw)
        del raw["palette"]
        migrated = self.routed(raw)
        self.assertEqual(migrated["provenance"]["expandedLegacyPaletteTokens"], sorted(router.DEFAULT))
        direct = router.Overlay(raw, self.timeline["chapters"], 10, self.base)
        self.assertEqual(direct.frame(3).tobytes(), router.build_renderer(migrated, self.base).frame(3).tobytes())
        del migrated["rendererConfig"]["palette"]
        with self.assertRaisesRegex(router.classic.ConfigError, "explicit palette"):
            router.build_renderer(migrated, self.base)

    def test_fractional_source_fps_and_single_pose_are_preserved(self):
        image = Image.new("RGBA", (64, 64))
        ImageDraw.Draw(image).rectangle((20, 5, 40, 60), fill="#19766C")
        image.save(self.base / "single.png")
        char = {"mode": "single", "frames": ["single.png"], "anchors": [{"x": 32, "y": 60}], "visibleHeight": 42}
        timeline = copy.deepcopy(self.timeline)
        timeline["fps"] = "30000/1001"
        raw = self.raw | {"character": char}
        env = self.routed(raw, timeline)
        after = router.build_renderer(env, self.base)
        self.assertEqual(env["timeline"]["fps"], "30000/1001")
        self.assertAlmostEqual(after.config.fps, 30000/1001)
        self.assertEqual(env["rendererConfig"]["character"], char)
        direct = router.Overlay(raw, timeline["chapters"], 10, self.base)
        self.assertEqual(after.frame(4).tobytes(), direct.frame(4).tobytes())

    def test_historical_profile_and_missing_assets_are_reported_without_mutation(self):
        profile = {"schemaVersion": 1, "approvedAt": "old", "style": {"preset": "S1"},
                   "character": {"mode": "four-frame", "assetPaths": ["missing.png"]}}
        before = copy.deepcopy(profile)
        report = router.inspect_config(profile, self.base)
        self.assertFalse(report["automaticMigration"])
        self.assertEqual(report["missingCharacterAssets"], 1)
        self.assertFalse(report["approvalCopied"])
        self.assertEqual(profile, before)
        with self.assertRaisesRegex(router.classic.ConfigError, "manual review"):
            router.migrate_config(profile, router.INSTALLED_ORIGIN, self.base, self.base)
        data = self.routed(self.raw | {"fontRegular": "missing.otf"})
        self.assertFalse(router.inspect_config(data, self.base)["ready"])
        self.assertEqual(list(self.base.iterdir()), [])

    def test_cli_migration_never_overwrites_and_profile_failure_writes_nothing(self):
        source, output = self.base / "raw.json", self.base / "routed.json"
        source.write_text(json.dumps(self.raw))
        timeline = self.base / "timeline.json"
        timeline.write_text(json.dumps(self.timeline))
        command = [sys.executable, str(SCRIPTS / "style_router.py"), "migrate-config", str(source), str(output),
                   "--origin", router.INSTALLED_ORIGIN, "--timeline", str(timeline)]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        saved = output.read_bytes()
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertEqual(output.read_bytes(), saved)
        source.write_text(json.dumps({"style": {"preset": "S6"}}))
        output.unlink()
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())
        self.assertFalse(json.loads(result.stdout)["automaticMigration"])

    def test_export_gates_do_not_convert_synthetic_inputs_to_final(self):
        data = self.routed()
        data["synthetic"] = True
        for kwargs in ({"purpose": "final", "final_approved": True},
                       {"purpose": "final"}, {"purpose": "sample", "seconds": 16},
                       {"purpose": "debug", "start": 9, "seconds": 2}):
            with self.assertRaises(router.classic.ConfigError):
                router.export_mov(data, self.base, self.base / "never.mov", **kwargs)
        self.assertFalse((self.base / "never.mov").exists())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
    def test_gallery_mov_uses_actual_pts_including_last_encoded_frame(self):
        data = self.routed(self.raw | {"style": "04"})
        data["synthetic"] = True
        output = self.base / "debug.mov"
        # One encoded frame at 2.999 must remain in the first chapter.
        report = router.export_mov(data, self.base, output, "debug", start=2.999, seconds=1/24)
        self.assertEqual(report["frameCount"], 1)
        self.assertEqual(report["styleKey"], "gallery:04")
        renderer = router.build_renderer(data, self.base)
        actual = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(output),
                                          "-f", "rawvideo", "-pix_fmt", "rgba", "-"])
        image = Image.frombytes("RGBA", (renderer.config.width, renderer.config.height), actual)
        from PIL import ImageChops, ImageStat
        def error(time):
            expected = renderer.frame(time)
            return sum(ImageStat.Stat(ImageChops.difference(image, expected)).mean)
        self.assertLess(error(2.999), error(3.0))
        self.assertEqual(image.getchannel("A").getextrema(), (0, 255))


if __name__ == "__main__":
    unittest.main()
