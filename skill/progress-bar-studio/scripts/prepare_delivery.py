#!/usr/bin/env python3
"""Reserve a versioned Progress Bar Studio delivery directory."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


class DeliveryError(Exception):
    """A destination setup error the user can resolve."""


def directory_stem(source: Path) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", source.stem).strip(".-")
    return normalized or "progress-bar"


def reserve_delivery_directory(output_dir: Path, source: Path) -> Path:
    if not output_dir.exists():
        raise DeliveryError(f"Output folder does not exist: {output_dir}")
    if not output_dir.is_dir():
        raise DeliveryError(f"Output path is not a folder: {output_dir}")

    base = f"{directory_stem(source)}-progress-bar"
    for version in range(1, 10_000):
        suffix = "" if version == 1 else f"-v{version}"
        candidate = output_dir / f"{base}{suffix}"
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            continue
        except OSError as exc:
            raise DeliveryError(
                f"Cannot create delivery folder '{candidate}': {exc.strerror or exc}"
            ) from exc
    raise DeliveryError("Could not reserve a versioned delivery folder.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reserve a versioned delivery folder without overwriting an existing job."
    )
    parser.add_argument("--source-video", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--character-mode",
        choices=("none", "single-pose", "walk-cycle"),
        required=True,
        help="The user-approved character path.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_video.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not source.is_file():
        print(f"Cannot reserve delivery folder: Source video not found: {source}", file=sys.stderr)
        return 2

    try:
        delivery_dir = reserve_delivery_directory(output_dir, source)
    except DeliveryError as exc:
        print(f"Cannot reserve delivery folder: {exc}", file=sys.stderr)
        return 2

    character_outputs = {
        "none": [],
        "single-pose": ["character.png"],
        "walk-cycle": [
            "character.png",
            "walk-01.png",
            "walk-02.png",
            "walk-03.png",
            "walk-04.png",
            "walk-preview.webp",
        ],
    }[args.character_mode]
    result = {
        "deliveryDirectory": str(delivery_dir),
        "sourceVideo": str(source),
        "characterMode": args.character_mode,
        "characterOutputs": character_outputs,
        "nextCheckpoint": "chapter-analysis"
        if args.character_mode == "none"
        else "character-confirmation",
        "artifacts": [
            "progress_bar.mov",
            "preview.mp4",
            "chapters.json",
            "style.json",
            "qc/",
        ],
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Reserved: {delivery_dir}")
        print(f"Character mode: {args.character_mode}")
        print(f"Next checkpoint: {result['nextCheckpoint']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
