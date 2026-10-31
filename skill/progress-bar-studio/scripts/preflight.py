#!/usr/bin/env python3
"""Check whether the current host can run a Progress Bar Studio project."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def encoder_available() -> bool:
    if not command_available("ffmpeg"):
        return False
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return "prores_ks" in result.stdout


def pillow_capabilities() -> tuple[bool, bool]:
    try:
        from PIL import features
    except ImportError:
        return False, False
    return True, bool(features.check("webp"))


def check_output_folder(directory: Path) -> tuple[list[str], list[str], int | None]:
    blockers: list[str] = []
    next_actions: list[str] = []
    expanded = directory.expanduser().resolve()
    if not expanded.exists():
        blockers.append("OUTPUT_DIRECTORY_MISSING")
        next_actions.append(f"Choose or create an existing output folder: {expanded}")
        return blockers, next_actions, None
    if not expanded.is_dir():
        blockers.append("OUTPUT_PATH_NOT_DIRECTORY")
        next_actions.append(f"Choose a folder instead of a file: {expanded}")
        return blockers, next_actions, None
    if not os.access(expanded, os.W_OK | os.X_OK):
        blockers.append("OUTPUT_DIRECTORY_NOT_WRITABLE")
        next_actions.append(f"Choose an output folder you can write to: {expanded}")
        return blockers, next_actions, None
    return blockers, next_actions, shutil.disk_usage(expanded).free


def source_media_streams(source: Path) -> tuple[bool, bool] | None:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "json",
                str(source),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        streams = json.loads(result.stdout).get("streams", [])
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError):
        return None
    stream_types = {stream.get("codec_type") for stream in streams}
    return "video" in stream_types, "audio" in stream_types


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Progress Bar Studio dependencies and delivery-folder readiness."
    )
    parser.add_argument("--source-video", type=Path, help="Optional source video to inspect")
    parser.add_argument("--output-dir", type=Path, help="Approved delivery folder")
    parser.add_argument("--required-bytes", type=int, help="Estimated final master size in bytes")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    parser.add_argument('--font',type=Path,help='Chosen local font; validate actual label glyphs with --text')
    parser.add_argument('--text',default='章节进度开场总结',help='Actual chapter/kicker text to check')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    blockers: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []

    ffmpeg = command_available("ffmpeg")
    ffprobe = command_available("ffprobe")
    prores4444 = encoder_available()
    pillow, webp = pillow_capabilities()
    font_result='unverified: Pillow required'
    if pillow:
        try:
            from render_progress import choose_font
            from font_validation import require_glyphs
            font=choose_font(str(args.font) if args.font else None,Path.cwd(),any(ord(c)>127 for c in args.text))
            require_glyphs(font,args.text)
            font_result={'path':str(font),'glyphCoverage':'passed','testedText':args.text}
        except ValueError as exc:
            blockers.append('FONT_GLYPHS_UNAVAILABLE')
            next_actions.append(str(exc))

    if not ffmpeg:
        blockers.append("FFMPEG_MISSING")
        next_actions.append("Install FFmpeg before exporting a transparent MOV or preview MP4.")
    if not ffprobe:
        blockers.append("FFPROBE_MISSING")
        next_actions.append("Install FFmpeg before probing video duration, frame rate, and audio.")
    if ffmpeg and not prores4444:
        blockers.append("PRORES_4444_ENCODER_MISSING")
        next_actions.append("Use an FFmpeg build with the prores_ks encoder for transparent MOV export.")
    if not pillow:
        blockers.append("PILLOW_MISSING")
        next_actions.append("Install Pillow in this Python environment before any local preview or MOV render; no-character mode also requires it. Chapter planning can continue independently.")
    elif not webp:
        warnings.append("WEBP_UNAVAILABLE")
        next_actions.append("Use a Pillow build with WebP support to export walk-cycle previews.")

    source = args.source_video.expanduser().resolve() if args.source_video else None
    if source is None:
        warnings.append("SOURCE_VIDEO_NOT_PROVIDED")
    elif not source.is_file():
        blockers.append("SOURCE_VIDEO_MISSING")
        next_actions.append(f"Choose an existing source video: {source}")
    elif ffprobe:
        streams = source_media_streams(source)
        if streams is None or not streams[0]:
            blockers.append("SOURCE_VIDEO_UNREADABLE")
            next_actions.append(
                f"Choose or re-export a readable video with a video track: {source}"
            )
        elif not streams[1]:
            warnings.append("SOURCE_AUDIO_MISSING")
            next_actions.append(
                "Provide an editable timestamped chapter list, or choose a version with audio for automatic chapter analysis."
            )

    # Analysis can use read-only source media before a delivery folder is chosen.
    # Never infer an approved output destination from the source video's location.
    output = args.output_dir
    free_bytes: int | None = None
    if output is None:
        warnings.append("OUTPUT_DIRECTORY_NOT_SELECTED")
        next_actions.append("Choose an output folder before rendering the final master.")
    else:
        output_blockers, output_actions, free_bytes = check_output_folder(output)
        blockers.extend(output_blockers)
        next_actions.extend(output_actions)

    if args.required_bytes is not None:
        if args.required_bytes <= 0:
            blockers.append("INVALID_REQUIRED_SIZE")
            next_actions.append("Pass a positive final-size estimate in --required-bytes.")
        elif free_bytes is not None and free_bytes < args.required_bytes * 2:
            blockers.append("DISK_INSUFFICIENT")
            next_actions.append(
                "Free at least twice the estimated master size for the output, temporary files, and QC."
            )

    warnings.append("TRANSCRIPTION_HOST_DEPENDENT")
    warnings.append("IMAGE_EDITING_HOST_DEPENDENT")
    result = {
        "ok": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "capabilities": {
            "ffmpeg": ffmpeg,
            "ffprobe": ffprobe,
            "prores4444": prores4444,
            "pillow": pillow,
            "walkWebp": webp,
            "font": font_result,
            "python": {'executable':sys.executable,'version':sys.version.split()[0]},
            "transcription": "unknown: host tool evidence required",
            "imageEditing": "unknown: reference-image editing tool evidence required",
        },
        "sourceVideo": str(source) if source else None,
        "outputDirectory": str(output.expanduser().resolve()) if output else None,
        "freeBytes": free_bytes,
        "nextActions": next_actions,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Progress Bar Studio preflight")
        print(f"Status: {'ready' if result['ok'] else 'blocked'}")
        print("Blockers: " + (", ".join(blockers) if blockers else "none"))
        print("Warnings: " + (", ".join(warnings) if warnings else "none"))
        if output:
            print(f"Output folder: {result['outputDirectory']}")
        if free_bytes is not None:
            print(f"Free bytes: {free_bytes}")
        for action in next_actions:
            print(f"Next: {action}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
