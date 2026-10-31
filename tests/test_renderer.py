"""Deterministic raster-renderer regressions; no user asset or network needed."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill/progress-bar-studio/scripts/render_progress.py"
spec = importlib.util.spec_from_file_location("render_progress", SCRIPT)
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.raw = r.demo_config()
        self.raw["demoLabel"] = False
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def config(self, **changes):
        data = copy.deepcopy(self.raw)
        data.update(changes)
        return r.validate_config(data, self.base)

    def asset(self, name="approved.png", contact_x=12, width=48, height=64):
        image = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(image)
        draw.rectangle((5, 7, width - 5, height - 8), fill="#26416E")
        draw.rectangle((contact_x, height - 8, contact_x + 4, height - 4), fill="#26416E")
        path = self.base / name
        image.save(path)
        return path

    def test_core_and_extended_aliases(self):
        for style, (alias, _, _) in r.STYLE_NAMES.items():
            self.assertEqual(self.config(style=alias).style, style)

    def test_discovers_user_installed_mac_cjk_font_without_system_candidate(self):
        source = r.choose_font(None, self.base)
        target = self.base / "Library/Fonts/SourceHanSansCN-Regular.otf"
        target.parent.mkdir(parents=True)
        shutil.copyfile(source, target)
        with mock.patch.object(r, "FONT_CANDIDATES", ()), mock.patch.object(r.Path, "home", return_value=self.base):
            selected = r.choose_font(None, self.base)
        self.assertEqual(selected, target.resolve())
        self.assertGreater(r.ImageFont.truetype(str(selected), 24).getlength("中文章节"), 0)

    def test_auto_font_discovery_skips_corrupt_candidate_but_explicit_font_fails(self):
        source = r.choose_font(None, self.base)
        broken = self.base / "broken.otf"
        broken.write_bytes(b"not a font")
        with mock.patch.object(r, "FONT_CANDIDATES", (str(broken), str(source))):
            self.assertEqual(r.choose_font(None, self.base), source.resolve())
        with self.assertRaisesRegex(r.ConfigError, "font is not loadable"):
            r.choose_font(str(broken), self.base)

    def test_progress_clamps_and_boundary_is_half_open(self):
        config = self.config()
        for time, progress, index in ((-1, 0, 0), (0, 0, 0), (2.999, .2999, 0), (3, .3, 1), (7, .7, 2), (10, 1, 2), (11, 1, 2)):
            state = config.state(time)
            self.assertAlmostEqual(state.progress, progress)
            self.assertEqual(state.chapter, index)
        self.assertEqual(config.state(3).chapter_progress, 0)
        self.assertEqual(config.state(10).chapter_progress, 1)

    def test_nonfinite_time_rejected(self):
        for value in (float("nan"), float("inf"), True):
            with self.assertRaises(r.ConfigError):
                self.config().state(value)

    def test_rgba_all_styles_all_boundaries(self):
        for style in r.STYLE_NAMES:
            renderer = r.Renderer(self.config(style=style))
            for time in (0, 2.999, 3, 6.999, 7, 10):
                with self.subTest(style=style, time=time):
                    frame = renderer.frame(time)
                    self.assertEqual(frame.mode, "RGBA")
                    self.assertEqual(frame.size, (1280, 320))
                    self.assertEqual(frame.getchannel("A").getextrema(), (0, 255))
                    self.assertEqual(frame.getpixel((0, 0))[3], 0)

    def test_deterministic_pixels(self):
        for style in r.STYLE_NAMES:
            renderer = r.Renderer(self.config(style=style))
            self.assertEqual(renderer.frame(3.75).tobytes(), renderer.frame(3.75).tobytes())

    def test_none_never_opens_asset(self):
        with mock.patch.object(r.Image, "open", side_effect=AssertionError("no character image should be loaded")):
            renderer = r.Renderer(self.config())
            self.assertEqual(renderer.assets, [])
            self.assertEqual(renderer.frame(4).mode, "RGBA")

    def test_none_rejects_hidden_character(self):
        for character in ({"mode": "none", "path": "missing.png"}, {"mode": "none", "frames": []}, {"mode": "none", "approved": True}):
            with self.assertRaises(r.ConfigError):
                self.config(character=character)

    def test_gaps_overlap_out_of_bounds_zero_rejected(self):
        for patch in ({"start": .01}, {"end": 0}, {"end": 3.1}, {"start": -1}):
            data = copy.deepcopy(self.raw)
            data["chapters"][0].update(patch)
            with self.assertRaises(r.ConfigError):
                r.validate_config(data)
        for start in (2.99, 3.01):
            data = copy.deepcopy(self.raw)
            data["chapters"][1]["start"] = start
            with self.assertRaises(r.ConfigError):
                r.validate_config(data)
        data = copy.deepcopy(self.raw)
        data["chapters"][-1]["end"] = 9.9
        with self.assertRaises(r.ConfigError):
            r.validate_config(data)

    def test_small_timing_noise_normalized(self):
        data = copy.deepcopy(self.raw)
        data["chapters"][1]["start"] += .00001
        data["chapters"][-1]["end"] -= .00001
        config = r.validate_config(data)
        self.assertEqual(config.chapters[1].start, config.chapters[0].end)
        self.assertEqual(config.chapters[-1].end, config.duration)

    def test_bad_numeric_and_size_fields(self):
        for field, value in (("fps", 0), ("fps", float("nan")), ("fps", True), ("duration", float("inf")), ("duration", -1), ("width", 100), ("width", 1280.0), ("height", 1), ("height", True), ("width", 100000)):
            with self.subTest(field=field, value=value), self.assertRaises(r.ConfigError):
                self.config(**{field: value})
        with self.assertRaises(r.ConfigError):
            self.config(width=7680, height=4320)

    def test_unknown_fields_and_styles_rejected(self):
        for changes in ({"chapter": []}, {"style": "custom"}, {"schemaVersion": 2}, {"demoLabel": "false"}):
            with self.assertRaises(r.ConfigError):
                self.config(**changes)

    def test_titles_and_chapter_keys(self):
        for title in ("", "\n", "A\nB", "a" * 201, 12):
            data = copy.deepcopy(self.raw)
            data["chapters"][0]["title"] = title
            with self.assertRaises(r.ConfigError):
                r.validate_config(data)
        data = copy.deepcopy(self.raw)
        data["chapters"][0]["extra"] = True
        with self.assertRaises(r.ConfigError):
            r.validate_config(data)

    def test_palette_requires_explicit_contrasting_tokens(self):
        for palette in ({}, {**self.raw["palette"], "active": "pink"}, {**self.raw["palette"], "text": "#FFFFFF"}, {**self.raw["palette"], "active-text": "#FFFFFF"}, {**self.raw["palette"], "surface": "#FFFFFF00"}):
            with self.assertRaises(r.ConfigError):
                self.config(palette=palette)

    def test_s3_progress_color_is_independent_of_text(self):
        palette = dict(self.raw["palette"], progress="#CC2244", **{"progress-inactive": "#CCDDEE"})
        renderer = r.Renderer(self.config(style="S3", palette=palette))
        self.assertEqual(renderer.palette["progress"], (204, 34, 68, 255))
        self.assertNotEqual(renderer.palette["progress"], renderer.palette["text"])
        frame = renderer.frame(4.5)
        self.assertGreater(sum(n for n, px in frame.getcolors(frame.width * frame.height) if px[0] > 180 and px[1] < 80 and 40 < px[2] < 110 and px[3] > 200), 10)
        default = self.config(style="S3")
        self.assertEqual(default.palette["progress"], default.palette["active"])
        self.assertEqual(default.palette["progress-inactive"], default.palette["inactive"])

    def test_palette_is_not_hardcoded_pink(self):
        p = dict(self.raw["palette"], active="#0044AA", **{"active-text": "#FFFFFF"})
        config = self.config(palette=p)
        frame = r.Renderer(config).frame(4)
        self.assertGreater(sum(n for n, px in frame.getcolors(frame.width * frame.height) if px[:3] == (0, 68, 170)), 500)

    def test_long_cjk_wraps_or_ellipsizes(self):
        renderer = r.Renderer(self.config())
        title = "这是一个很长的中文章节名称，需要保留足够大的字号和完整的章节数据"
        lines = renderer.fit_lines(title, 160, 28, 2)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[-1].endswith("…"))
        self.assertTrue(all(renderer.text_width(line, 28) <= 160 for line in lines))
        self.assertEqual(renderer.ellipsis("Short", 200, 28), "Short")

    def test_unreadable_band_fails_helpfully(self):
        chapters = [{"start": 0, "end": .1, "title": "开场"}, {"start": .1, "end": 10, "title": "内容"}]
        with self.assertRaisesRegex(r.ConfigError, "S4 segment"):
            r.Renderer(self.config(style="S4", chapters=chapters))
        self.assertEqual(r.Renderer(self.config(style="S5", chapters=chapters)).frame(0).mode, "RGBA")

    def test_approved_single_pose_retains_progress(self):
        path = self.asset()
        character = {"mode": "single-pose", "approved": True, "path": path.name, "height": 50}
        renderer = r.Renderer(self.config(character=character))
        self.assertEqual(len(renderer.assets), 1)
        for t in (0, 3, 10):
            self.assertEqual(renderer.frame(t).getchannel("A").getextrema(), (0, 255))
        self.assertNotEqual(renderer.frame(0).tobytes(), renderer.frame(5).tobytes())

    def test_single_pose_all_styles_and_offcenter_contact(self):
        path = self.asset(contact_x=5)
        character = {"mode": "single-pose", "approved": True, "path": path.name, "height": 40}
        for style in r.STYLE_NAMES:
            renderer = r.Renderer(self.config(style=style, character=character))
            for t in (0, 2.999, 3, 5, 7, 9.999, 10):
                self.assertEqual(renderer.frame(t).mode, "RGBA")

    def test_unapproved_missing_or_opaque_asset_rejected(self):
        path = self.asset()
        for character in ({"mode": "single-pose", "path": path.name}, {"mode": "single-pose", "approved": True, "path": "missing.png"}):
            with self.assertRaises(r.ConfigError):
                self.config(character=character)
        Image.new("RGBA", (30, 30), "blue").save(self.base / "opaque.png")
        with self.assertRaises(r.ConfigError):
            r.Renderer(self.config(character={"mode": "single-pose", "approved": True, "path": "opaque.png"}))

    def test_real_four_frame_cycle_uses_given_order(self):
        names = [self.asset(f"frame-{i}.png", contact_x=5+i*6).name for i in range(4)]
        character = {"mode": "walk-cycle", "approved": True, "frames": names, "height": 45, "cadence": 6}
        renderer = r.Renderer(self.config(character=character))
        self.assertEqual(len(renderer.assets), 4)
        for i in range(4):
            self.assertEqual(renderer.frame(i / 6).mode, "RGBA")
        with self.assertRaises(r.ConfigError):
            self.config(character=dict(character, frames=names[:3]))

    def test_extremely_wide_asset_rejected_before_resize_allocation(self):
        image = Image.new("RGBA", (10000, 3))
        ImageDraw.Draw(image).line((1, 1, 9998, 1), fill="#26416E", width=1)
        path = self.base / "wide-visible-row.png"
        image.save(path)
        config = self.config(character={"mode": "single-pose", "approved": True, "path": path.name, "height": 100})
        with mock.patch.object(Image.Image, "resize", side_effect=AssertionError("must reject before allocating")) as resize:
            with self.assertRaisesRegex(r.ConfigError, "too wide"):
                r.Renderer(config)
            resize.assert_not_called()

    def test_invalid_contact_rejected(self):
        path = self.asset()
        for point in ([0, 0], [999, 999]):
            with self.assertRaises(r.ConfigError):
                r.Renderer(self.config(character={"mode": "single-pose", "approved": True, "path": path.name, "height": 40, "contacts": [point]}))

    def test_ring_zero_has_no_accent_arc_and_full_is_closed(self):
        renderer = r.Renderer(self.config(style="S6"))
        active = renderer.palette["active"][:3]
        start = renderer.frame(0)
        end = renderer.frame(10)
        self.assertEqual(sum(n for n, px in start.getcolors(start.width * start.height) if px[:3] == active and px[3] == 255), 0)
        self.assertGreater(sum(n for n, px in end.getcolors(end.width * end.height) if all(abs(px[j] - active[j]) < 8 for j in range(3)) and px[3] == 255), 200)

    def test_explicit_portrait_dimensions_are_preserved(self):
        renderer = r.Renderer(self.config(width=1080, height=1920))
        self.assertEqual(renderer.frame(4).size, (1080, 1920))
        self.assertLess(renderer.frame(4).getbbox()[3], 1920)

    def test_no_silent_overwrite(self):
        path = self.base / "preview.png"
        r.save_image(r.Renderer(self.config()).frame(0), path)
        with self.assertRaises(r.ConfigError):
            r.save_image(r.Renderer(self.config()).frame(1), path)

    def test_cli_final_gate_and_sample_duration_gate(self):
        path = self.base / "config.json"
        path.write_text(json.dumps(self.raw))
        for args in (["mov", str(path), str(self.base / "final.mov"), "--purpose", "final"],
                     ["mov", str(path), str(self.base / "sample.mov"), "--purpose", "sample", "--seconds", "20"],
                     ["demo-video", str(path), str(self.base / "out.mp4"), "--purpose", "sample"]):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn("ERROR:", result.stderr)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
    def test_single_frame_export_uses_zero_pts_not_timeline_endpoint(self):
        chapters = [{"start": 0, "end": .5, "title": "First"}, {"start": .5, "end": 1, "title": "Last"}]
        renderer = r.Renderer(self.config(duration=1, fps=1, width=640, height=160, style="S5", chapters=chapters))
        with mock.patch.object(renderer, "frame", wraps=renderer.frame) as frame:
            report = r.export_video(renderer, self.base / "one-frame.mov", 0, 1)
        self.assertEqual(report["frameCount"], 1)
        frame.assert_called_once_with(0)
        self.assertEqual(renderer.config.state(frame.call_args.args[0]).chapter, 0)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
    def test_tiny_prores_has_decoded_alpha_and_correct_frames(self):
        config = self.config(width=640, height=160, fps=12, style="S5")
        path = self.base / "sample.mov"
        report = r.export_video(r.Renderer(config), path, 2.8, .5)
        self.assertEqual(report["frameCount"], 6)
        self.assertEqual(report["codec"], "prores")
        self.assertIn("4444", report["profile"])
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-frames:v", "1", "-pix_fmt", "rgba", "-f", "rawvideo", "pipe:1"], check=True, capture_output=True).stdout
        self.assertEqual(len(raw), 640 * 160 * 4)
        decoded = Image.frombytes("RGBA", (640, 160), raw)
        self.assertEqual(decoded.getchannel("A").getextrema(), (0, 255))
        with self.assertRaises(r.ConfigError):
            r.export_video(r.Renderer(config), path, 2.8, .5)


    def test_palette_presets_and_explicit_overrides(self):
        for name in r.PALETTE_PRESETS:
            raw = copy.deepcopy(self.raw)
            raw.pop("palette")
            raw["palettePreset"] = name
            config = r.validate_config(raw)
            self.assertEqual(config.palette["surface"], r.color(r.PALETTE_PRESETS[name]["surface"]))
            for style in r.STYLE_NAMES:
                config.style = style
                self.assertEqual(r.Renderer(config).frame(4).mode, "RGBA")
        raw["palette"] = {"progress": "#AA4466"}
        self.assertEqual(r.validate_config(raw).palette["progress"], (170, 68, 102, 255))
        for bad in ("unknown", 1, [], {}):
            with self.assertRaises(r.ConfigError):
                self.config(palettePreset=bad)

    def test_s2_rejects_tiny_timed_segments_before_drawing(self):
        for end in (.01, .1, .5):
            chapters = [{"start": 0, "end": end, "title": "First"},
                        {"start": end, "end": 7, "title": "Second"},
                        {"start": 7, "end": 10, "title": "Last"}]
            with self.assertRaisesRegex(r.ConfigError, "timed S2 segment"):
                r.Renderer(self.config(style="S2", chapters=chapters))

    def test_s2_labels_align_with_true_time_sections(self):
        chapters = [{"start": 0, "end": 1, "title": "A"},
                    {"start": 1, "end": 7, "title": "B"},
                    {"start": 7, "end": 10, "title": "C"}]
        renderer = r.Renderer(self.config(style="S2", chapters=chapters))
        with mock.patch.object(renderer, "label", wraps=renderer.label) as label:
            renderer.frame(4)
        self.assertEqual(label.call_count, 3)
        for chapter, call in zip(chapters, label.call_args_list):
            box = call.args[2]
            expected = renderer.x0 + (chapter["start"] + chapter["end"]) / 20 * (renderer.x1 - renderer.x0)
            self.assertAlmostEqual((box[0] + box[2]) / 2, expected)

    def test_s3_has_no_solid_background_or_long_underline(self):
        renderer = r.Renderer(self.config(style="S3"))
        for time in (0, 2.999, 3, 5, 7, 10):
            alpha = renderer.frame(time).getchannel("A")
            opaque = sum(1 for a in alpha.getdata() if a > 200)
            self.assertLess(opaque, 1280 * renderer.row_h * .13)
            # A pill or long filled baseline would create a large solid run.
            longest = 0
            for y in range(int(renderer.body_y), int(renderer.bottom) + 1):
                run = 0
                for a in alpha.crop((0, y, 1280, y + 1)).getdata():
                    run = run + 1 if a > 200 else 0
                    longest = max(longest, run)
            self.assertLessEqual(longest, 60)

    def test_s4_single_slim_band_and_true_time_fill(self):
        renderer = r.Renderer(self.config(style="S4"))
        self.assertLessEqual(renderer.body_h, 48)
        frame = renderer.frame(4.5)
        y = int(renderer.body_y + 5)
        edge = renderer.x0 + .45 * (renderer.x1 - renderer.x0)
        self.assertEqual(frame.getpixel((int(edge - 8), y))[:3], renderer.palette["active"][:3])
        self.assertEqual(frame.getpixel((int(edge + 8), y))[:3], renderer.palette["surface"][:3])
        self.assertEqual(frame.getpixel((int(renderer.x0 + 30), int(renderer.body_y - 8)))[3], 0)

    def test_s7_active_tab_changes_at_exact_boundary(self):
        renderer = r.Renderer(self.config(style="S7"))
        slot = (renderer.x1 - renderer.x0) / len(renderer.config.chapters)
        y = int(renderer.tab_h + renderer.tab_extra / 2)
        for time, expected in ((0, 0), (2.999, 0), (3, 1), (6.999, 1), (7, 2), (10, 2)):
            frame = renderer.frame(time)
            for i in range(3):
                x = int(renderer.x0 + (i + .5) * slot)
                self.assertEqual(frame.getpixel((x, y))[3] > 200, i == expected)
            self.assertLess(frame.getbbox()[3], renderer.config.height)

    def test_s7_long_bilingual_labels_remain_inside_each_tab(self):
        raw = copy.deepcopy(self.raw)
        raw["style"] = "S7"
        for c in raw["chapters"]:
            c["title"] = "很长的中文标题必须省略而不能覆盖隔壁章节" * 3
            c["subtitle"] = "A very long English secondary label that must remain inside its own tab"
        renderer = r.Renderer(r.validate_config(raw))
        for time in (0, 3, 7, 10):
            frame = renderer.frame(time)
            slot = (renderer.x1 - renderer.x0) / 3
            for boundary in (1, 2):
                x = round(renderer.x0 + boundary * slot)
                self.assertEqual(frame.getchannel("A").crop((x-2, 0, x+2, frame.height)).getextrema(), (0, 0))

    def test_s7_cjk_subtitles_require_a_cjk_capable_font(self):
        raw = copy.deepcopy(self.raw)
        raw["style"] = "S7"
        for chapter in raw["chapters"]:
            chapter["title"] = "English title"
            chapter["subtitle"] = "中文副标题"
        with mock.patch.object(r, "choose_font", wraps=r.choose_font) as choose:
            r.validate_config(raw)
        self.assertTrue(choose.call_args.args[2])

    def test_s7_rejects_short_canvas_and_invalid_subtitle(self):
        with self.assertRaisesRegex(r.ConfigError, "hanging tabs"):
            r.Renderer(self.config(style="S7", height=96))
        for subtitle in (None, 12, "a\nb", "a" * 121):
            raw = copy.deepcopy(self.raw)
            raw["chapters"][0]["subtitle"] = subtitle
            with self.assertRaises(r.ConfigError):
                r.validate_config(raw)
        raw = copy.deepcopy(self.raw)
        raw["chapters"][-1]["subtitle"] = "Last chapter"
        self.assertEqual(r.validate_config(raw).chapters[-1].subtitle, "Last chapter")

    def test_contact_sheet_includes_seventh_style_without_clipping(self):
        sheet = r.contact_sheet(self.config())
        self.assertGreater(sheet.height, 1100)
        self.assertEqual(sheet.mode, "RGB")


if __name__ == "__main__":
    unittest.main()
