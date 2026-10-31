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

PRESETS = (("1080p", 1920), ("2K (2160px wide)", 2160), ("4K", 3840))
# Heuristic planning range, not an upper bound. Actual encodes may exceed it.
# Measure an encoded short draft/sample to calibrate the full-duration estimate.
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
        "format=duration:stream=duration,avg_frame_rate,r_frame_rate",
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
        raw_duration = stream.get('duration')
        if raw_duration in (None, 'N/A'):
            raw_duration = payload['format']['duration']
        duration = float(raw_duration)
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
        description="Estimate exact planned overlay dimensions; this project's 2K preset is 2160px wide."
    )
    parser.add_argument("video", type=Path, help="Source video used for duration and fps")
    parser.add_argument('--width',type=int,help='Exact selected strip width, including explicit 2560 if requested')
    parser.add_argument('--config',type=Path,help='Current routed config; use its actual derived height, width and target fps')
    parser.add_argument('--draft',action='store_true',help='Explicitly estimate a pending draft, including its DRAFT band; grants no approval')
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
    if args.width is not None and not 240<=args.width<=7680:
        parser.error('--width must be 240–7680 pixels')
    if args.draft and not args.config:
        parser.error('--draft requires --config')
    return args


def main() -> int:
    args = parse_args()
    try:
        duration, fps = probe_video(args.video)
        destination, free_bytes = output_directory(args.output_dir or args.video.parent)
        actual=None
        if args.config:
            import style_router as router
            actual=router.build_renderer(router.load(args.config),args.config.resolve().parent,draft=args.draft).config
            if abs(actual.duration-duration)>1/fps+.001:
                raise EstimationError('Config duration differs from the current video; do not reuse an old timeline.')
            if args.width is not None and args.width!=actual.width or args.strip_height is not None and args.strip_height!=actual.height:
                raise EstimationError('Explicit dimensions conflict with the render config.')
            fps=actual.fps
    except (EstimationError,ValueError,OSError) as exc:
        print(f"Cannot estimate output size: {exc}", file=sys.stderr)
        return 2

    estimates = []
    dimensions=[(f'{actual.width}px actual render',actual.width)] if actual else [(f'{args.width}px selected',args.width)] if args.width else PRESETS
    for label, width in dimensions:
        height = actual.height if actual else args.strip_height or round(width * args.height_ratio / 2) * 2
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
        "estimateBasis": "uncalibrated-planning-range",
        "upperBoundGuaranteed": False,
        "reviewState": "draft" if args.draft else "unchanged",
        "note": (
            "Uncalibrated planning range, not a guaranteed upper bound. Actual files may be larger. "
            "Measure a short encoded draft/sample made with the same render settings to calibrate "
            "the full-duration estimate; estimating or encoding a draft grants no approval."
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
