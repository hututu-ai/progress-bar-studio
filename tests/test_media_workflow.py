#!/usr/bin/env python3
"""End-to-end regression coverage for Progress Bar Studio guardrails."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY / "skill" / "progress-bar-studio" / "scripts"
PREFLIGHT = SCRIPTS / "preflight.py"
ESTIMATOR = SCRIPTS / "estimate_export_size.py"
PREPARE_DELIVERY = SCRIPTS / "prepare_delivery.py"
PROBE_VIDEO = SCRIPTS / "probe_video.sh"
VERIFY_ALPHA = SCRIPTS / "verify_alpha_mov.sh"


def run(*command: str, expected: int | None = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True)
    if expected is not None and result.returncode != expected:
        raise AssertionError(
            f"Expected exit {expected}, got {result.returncode}: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def json_output(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)


class ProgressBarStudioRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for command in ("ffmpeg", "ffprobe"):
            if not shutil.which(command):
                raise RuntimeError(f"Regression tests require {command}.")
        encoders = run("ffmpeg", "-hide_banner", "-encoders").stdout
        if "prores_ks" not in encoders:
            raise RuntimeError("Regression tests require FFmpeg's prores_ks encoder.")

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="progress-bar-tests-")
        self.root = Path(self.temp_dir.name)
        self.output_dir = self.root / "output"
        self.output_dir.mkdir()
        self.wide_no_audio = self.root / "wide-no-audio.mp4"
        self.portrait_no_audio = self.root / "portrait-no-audio.mp4"
        self.broken_video = self.root / "broken.mp4"
        self._make_video(self.wide_no_audio, "1280x720")
        self._make_video(self.portrait_no_audio, "720x1280")
        self.broken_video.write_text("not a media file", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _make_video(self, destination: Path, size: str) -> None:
        run(
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s={size}:r=30:d=0.4",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(destination),
        )

    def test_no_audio_warns_but_allows_manual_chapter_path(self) -> None:
        result = run(
            sys.executable,
            str(PREFLIGHT),
            "--source-video",
            str(self.wide_no_audio),
            "--output-dir",
            str(self.output_dir),
            "--json",
        )
        payload = json_output(result)
        self.assertTrue(payload["ok"])
        self.assertIn("SOURCE_AUDIO_MISSING", payload["warnings"])
        self.assertTrue(any("timestamped chapter list" in action for action in payload["nextActions"]))

    def test_portrait_video_is_probed_and_estimated(self) -> None:
        probe = run(str(PROBE_VIDEO), str(self.portrait_no_audio))
        metadata, _ = json.JSONDecoder().raw_decode(probe.stdout)
        video_stream = next(
            stream for stream in metadata["streams"] if stream["codec_type"] == "video"
        )
        self.assertEqual((video_stream["width"], video_stream["height"]), (720, 1280))

        estimate = run(
            sys.executable,
            str(ESTIMATOR),
            str(self.portrait_no_audio),
            "--output-dir",
            str(self.output_dir),
            "--json",
        )
        payload = json_output(estimate)
        self.assertEqual([item["width"] for item in payload["estimates"]], [1920, 2560, 3840])

    def test_broken_video_blocks_preflight(self) -> None:
        result = run(
            sys.executable,
            str(PREFLIGHT),
            "--source-video",
            str(self.broken_video),
            "--output-dir",
            str(self.output_dir),
            "--json",
            expected=2,
        )
        self.assertIn("SOURCE_VIDEO_UNREADABLE", json_output(result)["blockers"])

    def test_unwritable_output_directory_blocks_preflight(self) -> None:
        read_only = self.root / "read-only"
        read_only.mkdir()
        read_only.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            result = run(
                sys.executable,
                str(PREFLIGHT),
                "--source-video",
                str(self.wide_no_audio),
                "--output-dir",
                str(read_only),
                "--json",
                expected=2,
            )
        finally:
            read_only.chmod(stat.S_IRWXU)
        self.assertIn("OUTPUT_DIRECTORY_NOT_WRITABLE", json_output(result)["blockers"])

    def test_insufficient_disk_blocks_preflight(self) -> None:
        result = run(
            sys.executable,
            str(PREFLIGHT),
            "--source-video",
            str(self.wide_no_audio),
            "--output-dir",
            str(self.output_dir),
            "--required-bytes",
            str(10**18),
            "--json",
            expected=2,
        )
        self.assertIn("DISK_INSUFFICIENT", json_output(result)["blockers"])

    def test_alpha_verifier_rejects_opaque_mov(self) -> None:
        opaque = self.root / "opaque.mov"
        run(
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=white:s=64x32:r=30:d=0.4",
            "-c:v",
            "prores_ks",
            "-profile:v",
            "4",
            "-pix_fmt",
            "yuv444p10le",
            str(opaque),
        )
        result = run(str(VERIFY_ALPHA), str(opaque), expected=2)
        self.assertIn("Alpha verification failed", result.stderr)

    def test_alpha_verifier_accepts_transparent_prores_4444(self) -> None:
        transparent = self.root / "transparent.mov"
        run(
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=white:s=64x32:r=30:d=0.4",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x32:r=30:d=0.4,drawbox=x=0:y=0:w=32:h=32:color=white:t=fill",
            "-filter_complex",
            "[0:v][1:v]alphamerge",
            "-c:v",
            "prores_ks",
            "-profile:v",
            "4",
            "-pix_fmt",
            "yuva444p10le",
            str(transparent),
        )
        result = run(str(VERIFY_ALPHA), str(transparent))
        self.assertIn("Alpha verification passed", result.stdout)

    def test_versioned_delivery_and_no_character_path(self) -> None:
        first = run(
            sys.executable,
            str(PREPARE_DELIVERY),
            "--source-video",
            str(self.wide_no_audio),
            "--output-dir",
            str(self.output_dir),
            "--character-mode",
            "none",
            "--json",
        )
        second = run(
            sys.executable,
            str(PREPARE_DELIVERY),
            "--source-video",
            str(self.wide_no_audio),
            "--output-dir",
            str(self.output_dir),
            "--character-mode",
            "none",
            "--json",
        )
        first_payload = json_output(first)
        second_payload = json_output(second)
        self.assertTrue(Path(first_payload["deliveryDirectory"]).is_dir())
        self.assertTrue(Path(second_payload["deliveryDirectory"]).is_dir())
        self.assertNotEqual(first_payload["deliveryDirectory"], second_payload["deliveryDirectory"])
        self.assertEqual(first_payload["characterOutputs"], [])
        self.assertEqual(first_payload["nextCheckpoint"], "chapter-analysis")


if __name__ == "__main__":
    unittest.main(verbosity=2)
