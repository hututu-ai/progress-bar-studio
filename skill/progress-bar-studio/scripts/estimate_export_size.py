#!/usr/bin/env python3
"""Estimate transparent ProRes 4444 progress-bar master sizes from a source video."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

PRESETS = (("1080p", 1920), ("2K (2560px wide)", 2560), ("4K", 3840))
# Planning range for a graphical ProRes 4444 overlay. A final 15-second sample
# replaces this range before the full-duration render is authorized.
BITS_PER_PIXEL_RANGE = (0.65, 1.75)


class EstimationError(Exception):
    """An input or environment problem the user can resolve."""


def parse_fraction(value: str) -> float:
    try:
        parsed = float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return 0.0
    return parsed if math.isfinite(parsed) and parsed > 0 else 0.0


def probe_video(video: Path) -> tuple[float, float]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=avg_frame_rate,r_frame_rate",
        "-select_streams",
        "v:0",
        "-of",
        "json",
        str(video),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise EstimationError(
            "ffprobe is unavailable. Install FFmpeg, then run the estimate again."
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip().splitlines()[-1] if exc.stderr.strip() else "unknown media error"
        raise EstimationError(
            f"Cannot read '{video.name}' as a video: {detail}. Choose a readable video file."
        ) from exc

    try:
        payload = json.loads(result.stdout)
        stream = payload["streams"][0]
        duration = float(payload["format"]["duration"])
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise EstimationError(
            f"Cannot find a usable video stream and duration in '{video.name}'. "
            "Choose a video file with one video track."
        ) from exc

    if not math.isfinite(duration) or duration <= 0:
        raise EstimationError(
            f"'{video.name}' has no usable duration. Export or repair the video, then try again."
        )

    fps = parse_fraction(stream.get("avg_frame_rate", "0/0"))
    if fps == 0:
        fps = parse_fraction(stream.get("r_frame_rate", "0/0"))
    if fps == 0:
        raise EstimationError(
            f"Cannot determine frame rate for '{video.name}'. Export it with a standard frame rate first."
        )
    return duration, fps


def output_directory(path: Path) -> tuple[Path, int]:
    directory = path.expanduser().resolve()
    if not directory.exists():
        raise EstimationError(
            f"Output folder does not exist: {directory}. Choose an existing folder first."
        )
    if not directory.is_dir():
        raise EstimationError(f"Output path is not a folder: {directory}.")
    if not os.access(directory, os.W_OK | os.X_OK):
        raise EstimationError(
            f"Output folder is not writable: {directory}. Choose a folder you can write to."
        )
    try:
        return directory, shutil.disk_usage(directory).free
    except OSError as exc:
        raise EstimationError(
            f"Cannot inspect free space in output folder: {directory}. {exc.strerror or exc}"
        ) from exc


def format_bytes(value: float) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def estimate_bytes(width: int, height: int, fps: float, duration: float, bpp: float) -> float:
    return width * height * fps * duration * bpp / 8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate 1080p, 2K (2560px wide), and 4K ProRes 4444 overlay sizes."
    )
    parser.add_argument("video", type=Path, help="Source video used for duration and fps")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Approved delivery folder; defaults to the source video's folder",
    )
    parser.add_argument(
        "--height-ratio",
        type=float,
        default=0.115,
        help="Planning strip height as a fraction of width; recalibrate after style approval",
    )
    parser.add_argument(
        "--strip-height",
        type=int,
        help="Use the approved final strip height instead of --height-ratio",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable output for a material brief",
    )
    args = parser.parse_args()
    if not args.video.is_file():
        parser.error(f"Video not found: {args.video}")
    if args.height_ratio <= 0:
        parser.error("--height-ratio must be positive")
    if args.strip_height is not None and args.strip_height <= 0:
        parser.error("--strip-height must be positive")
    return args


def main() -> int:
    args = parse_args()
    try:
        duration, fps = probe_video(args.video)
        destination, free_bytes = output_directory(args.output_dir or args.video.parent)
    except EstimationError as exc:
        print(f"Cannot estimate output size: {exc}", file=sys.stderr)
        return 2

    estimates = []
    for label, width in PRESETS:
        height = args.strip_height or round(width * args.height_ratio / 2) * 2
        low = estimate_bytes(width, height, fps, duration, BITS_PER_PIXEL_RANGE[0])
        high = estimate_bytes(width, height, fps, duration, BITS_PER_PIXEL_RANGE[1])
        estimates.append(
            {
                "label": label,
                "width": width,
                "height": height,
                "minBytes": round(low),
                "maxBytes": round(high),
            }
        )

    result = {
        "source": str(args.video.resolve()),
        "durationSeconds": duration,
        "fps": fps,
        "outputDirectory": str(destination),
        "freeBytes": free_bytes,
        "estimates": estimates,
        "note": (
            "Planning range only. Encode a 15-second sample after style approval "
            "to calculate the final full-duration estimate before rendering."
        ),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"Source: {args.video.name}")
    print(f"Duration: {duration:.2f}s | FPS: {fps:.3f}")
    print(f"Output folder: {destination}")
    print(f"Free space in output folder: {format_bytes(free_bytes)}")
    print("Planning estimate for a transparent ProRes 4444 strip:")
    for estimate in estimates:
        print(
            f"- {estimate['label']}: {estimate['width']}x{estimate['height']}px | "
            f"about {format_bytes(estimate['minBytes'])} to "
            f"{format_bytes(estimate['maxBytes'])}"
        )
    print(result["note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
