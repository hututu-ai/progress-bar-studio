#!/usr/bin/env python3
"""Split an aligned transparent walk-cycle sheet and make a loop preview."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

from PIL import Image

from asset_validation import read_image, require_transparency, validate_frames, visible_bounds, image_bytes, publish_new_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split a horizontal 4-frame RGBA walk-cycle sheet."
    )
    parser.add_argument("--input", required=True, help="Transparent horizontal sprite sheet.")
    parser.add_argument("--out-dir", required=True, help="Directory for frames and preview.")
    parser.add_argument("--fps", type=float, default=8.0)
    parser.add_argument(
        "--prefix", default="character-walk", help="Output filename prefix."
    )
    return parser.parse_args()


def alpha_bounds(image: Image.Image) -> tuple[int, int, int, int] | None:
    return visible_bounds(image)


def main() -> int:
    args = parse_args()
    frame_count = 4
    source_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.out_dir).expanduser().resolve()

    try:
        if not math.isfinite(args.fps) or args.fps <= 0:
            raise ValueError("--fps must be a finite positive number.")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.prefix):
            raise ValueError("--prefix must be a plain filename prefix, without directories.")
        source = read_image(source_path, transparent=True, image_format="PNG")
        width, height = source.size
        if width < frame_count or height < 2:
            raise ValueError("Sprite sheet is too small.")
        if width % frame_count != 0:
            raise ValueError(
                f"Sheet width {width} is not divisible by {frame_count}; use four equal-width cells."
            )

        cell_width = width // frame_count
        frames: list[Image.Image] = []
        frame_files: list[str] = []
        visible_bottoms: list[int] = []
        warnings: list[str] = []

        for index in range(frame_count):
            frame = source.crop(
                (index * cell_width, 0, (index + 1) * cell_width, height)
            )
            require_transparency(frame, f"Frame {index + 1}")
            bounds = alpha_bounds(frame)
            if bounds is None:
                raise ValueError(f"Frame {index + 1} is fully transparent.")
            if frame.getpixel((0, 0))[3] > 8:
                warnings.append(f"Frame {index + 1} top-left corner is not transparent.")
            visible_bottoms.append(bounds[3])
            filename = f"{args.prefix}-frame-{index + 1:02d}.png"
            frames.append(frame)
            frame_files.append(filename)

        validate_frames(frames)
        bottom_spread = max(visible_bottoms) - min(visible_bottoms)
        if bottom_spread > max(2, round(height * 0.005)):
            warnings.append(
                f"Visible ground line varies by {bottom_spread}px; inspect for foot sliding."
            )

        # Validate every cell before creating any output, so an opaque or empty
        # later cell cannot leave a partial bundle that looks reusable.
        files = {filename: image_bytes(frame) for frame, filename in zip(frames, frame_files)}

        sequence = [0, 1, 2, 3]
        duration_ms = max(1, round(1000 / args.fps))
        preview_frames = [frames[index] for index in sequence]
        preview_path = output_dir / f"{args.prefix}-preview.webp"
        preview_data = image_bytes(
            preview_frames[0], "WEBP",
            save_all=True,
            append_images=preview_frames[1:],
            duration=duration_ms,
            loop=0,
            lossless=True,
            method=6,
            # Independent keyframes retain canvas Alpha even when poses share
            # an identical silhouette and only interior pixels change.
            kmin=1,
            kmax=1,
        )

        sheet_path = output_dir / f"{args.prefix}-spritesheet.png"
        import io
        with Image.open(io.BytesIO(preview_data)) as preview:
            if preview.n_frames != 4:
                raise ValueError("WebP collapsed the cycle; inspect for repeated poses before retrying.")
            for index in range(4):
                preview.seek(index)
                preview.load()
                actual = require_transparency(preview, f"Preview frame {index + 1}")
                blank = Image.new("RGBA", frames[index].size)
                if Image.alpha_composite(blank, actual).tobytes() != Image.alpha_composite(blank, frames[index]).tobytes():
                    raise ValueError("WebP preview changed the saved frame content or transparency.")
        files[preview_path.name] = preview_data
        files[sheet_path.name] = image_bytes(source)
        manifest = {
            "schemaVersion": 1,
            "frameCount": frame_count,
            "frameSize": {"width": cell_width, "height": height},
            "fps": args.fps,
            "playbackOrder": [index + 1 for index in sequence],
            "frames": frame_files,
            "spriteSheet": sheet_path.name,
            "preview": preview_path.name,
            "visibleBottoms": visible_bottoms,
            "warnings": warnings,
            "technicalValidation": "passed",
            "identityReview": "pending",
            "gaitReview": "pending",
            "userApproved": False,
        }
        manifest_path = output_dir / f"{args.prefix}-cycle.json"
        files[manifest_path.name] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        publish_new_files(output_dir, files)

        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
