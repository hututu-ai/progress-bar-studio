#!/usr/bin/env python3
"""Regressions for analysis-only preflight and explicit sample decisions."""

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
PREPARE_DELIVERY = SCRIPTS / "prepare_delivery.py"


class DeliveryPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for command in ("ffmpeg", "ffprobe"):
            if not shutil.which(command):
                raise RuntimeError(f"Regression tests require {command}.")
        encoders = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if "prores_ks" not in encoders:
            raise RuntimeError("Regression tests require FFmpeg's prores_ks encoder.")

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="delivery-preflight-tests-")
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.source_dir = self.root / "source"
        self.source_dir.mkdir()
        self.source = self.source_dir / "analysis.mp4"
        self.output = self.root / "output"
        self.output.mkdir()
        self.run_command(
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            "color=c=black:s=64x32:r=10:d=0.2",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(self.source),
        )

    def run_command(self, *command: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(
            result.returncode,
            expected,
            f"{' '.join(command)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def preflight(self, *options: str, expected: int = 0) -> dict:
        result = self.run_command(
            sys.executable, str(PREFLIGHT), "--source-video", str(self.source),
            *options, "--json", expected=expected,
        )
        return json.loads(result.stdout)

    def reserve(self, *options: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        return self.run_command(
            sys.executable, str(PREPARE_DELIVERY), "--source-video", str(self.source),
            "--output-dir", str(self.output), "--character-mode", "none",
            *options, expected=expected,
        )

    def make_read_only(self, directory: Path) -> None:
        original_mode = stat.S_IMODE(directory.stat().st_mode)
        directory.chmod(stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(directory.chmod, original_mode)
        if os.access(directory, os.W_OK | os.X_OK):
            self.skipTest("This host bypasses directory write permissions.")

    def test_analysis_of_read_only_source_needs_no_output_folder(self) -> None:
        original_bytes = self.source.read_bytes()
        self.make_read_only(self.source_dir)

        payload = self.preflight()

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["blockers"], [])
        self.assertIn("OUTPUT_DIRECTORY_NOT_SELECTED", payload["warnings"])
        self.assertIsNone(payload["outputDirectory"])
        self.assertIsNone(payload["freeBytes"])
        self.assertEqual(payload["sourceVideo"], str(self.source.resolve()))
        self.assertEqual(self.source.read_bytes(), original_bytes)
        self.assertEqual(list(self.source_dir.iterdir()), [self.source])
        self.assertEqual(list(self.output.iterdir()), [])

    def test_unspecified_output_does_not_inherit_source_disk_space(self) -> None:
        payload = self.preflight("--required-bytes", str(10**18))

        self.assertTrue(payload["ok"])
        self.assertIn("OUTPUT_DIRECTORY_NOT_SELECTED", payload["warnings"])
        self.assertNotIn("DISK_INSUFFICIENT", payload["blockers"])
        self.assertIsNone(payload["outputDirectory"])
        self.assertIsNone(payload["freeBytes"])
        self.assertTrue(any("Choose an output folder" in action for action in payload["nextActions"]))

    def test_explicit_read_only_output_still_blocks(self) -> None:
        self.make_read_only(self.output)

        payload = self.preflight("--output-dir", str(self.output), expected=2)

        self.assertFalse(payload["ok"])
        self.assertIn("OUTPUT_DIRECTORY_NOT_WRITABLE", payload["blockers"])
        self.assertNotIn("OUTPUT_DIRECTORY_NOT_SELECTED", payload["warnings"])
        self.assertEqual(payload["outputDirectory"], str(self.output.resolve()))
        self.assertIsNone(payload["freeBytes"])

    def test_selected_writable_output_is_checked(self) -> None:
        payload = self.preflight("--output-dir", str(self.output))

        self.assertTrue(payload["ok"])
        self.assertNotIn("OUTPUT_DIRECTORY_NOT_SELECTED", payload["warnings"])
        self.assertEqual(payload["outputDirectory"], str(self.output.resolve()))
        self.assertIsInstance(payload["freeBytes"], int)
        self.assertGreaterEqual(payload["freeBytes"], 0)

    def test_selected_missing_output_is_not_created_by_preflight(self) -> None:
        missing = self.output / "not-created"

        payload = self.preflight("--output-dir", str(missing), expected=2)

        self.assertIn("OUTPUT_DIRECTORY_MISSING", payload["blockers"])
        self.assertFalse(missing.exists())

    def test_approved_sample_advances_to_final_render(self) -> None:
        payload = json.loads(self.reserve("--sample-approved", "--json").stdout)

        self.assertTrue(payload["sampleApproved"])
        self.assertFalse(payload["sampleWaived"])
        self.assertEqual(payload["sampleArtifacts"], ["sample_progress_bar.mov"])
        self.assertEqual(payload["nextCheckpoint"], "final-render")
        self.assertTrue(Path(payload["deliveryDirectory"]).is_dir())

    def test_explicit_waiver_does_not_claim_sample_approval(self) -> None:
        payload = json.loads(self.reserve("--sample-waived", "--json").stdout)

        self.assertFalse(payload["sampleApproved"])
        self.assertTrue(payload["sampleWaived"])
        self.assertEqual(payload["sampleArtifacts"], [])
        self.assertEqual(payload["nextCheckpoint"], "final-render")
        self.assertEqual(payload["creatorArtifacts"], ["progress_bar.mov"])
        self.assertTrue(Path(payload["deliveryDirectory"]).is_dir())

    def test_sample_decision_is_required_before_reserving_folder(self) -> None:
        result = self.reserve("--json", expected=2)

        self.assertIn("--sample-approved", result.stderr)
        self.assertIn("--sample-waived", result.stderr)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_sample_cannot_be_both_approved_and_waived(self) -> None:
        result = self.reserve("--sample-approved", "--sample-waived", "--json", expected=2)

        self.assertIn("not allowed with argument", result.stderr)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_text_output_identifies_sample_waiver(self) -> None:
        result = self.reserve("--sample-waived")

        self.assertIn("Sample: explicitly waived by creator", result.stdout)
        self.assertIn("Next checkpoint: final-render", result.stdout)
        self.assertNotIn("Sample: approved", result.stdout)

    def test_waived_reservation_preserves_existing_delivery(self) -> None:
        first = json.loads(self.reserve("--sample-waived", "--json").stdout)
        first_dir = Path(first["deliveryDirectory"])
        existing_master = first_dir / "progress_bar.mov"
        existing_master.write_bytes(b"existing master must be preserved")

        second = json.loads(self.reserve("--sample-waived", "--json").stdout)
        second_dir = Path(second["deliveryDirectory"])

        self.assertEqual(first_dir.name, "analysis-progress-bar")
        self.assertEqual(second_dir.name, "analysis-progress-bar-v2")
        self.assertEqual(existing_master.read_bytes(), b"existing master must be preserved")
        self.assertEqual(list(second_dir.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
