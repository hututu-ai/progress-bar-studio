#!/usr/bin/env python3
"""Split an aligned transparent walk-cycle sheet and make a loop preview."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image


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
    return image.getchannel("A").getbbox()


def main() -> int:
    args = parse_args()
    frame_count = 4
    source_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.out_dir).expanduser().resolve()

    try:
        source = Image.open(source_path).convert("RGBA")
        width, height = source.size
        if width < frame_count or height < 2:
            raise ValueError("Sprite sheet is too small.")
        if width % frame_count != 0:
            raise ValueError(
                f"Sheet width {width} is not divisible by {frame_count}; use four equal-width cells."
            )

        cell_width = width // frame_count
        output_dir.mkdir(parents=True, exist_ok=True)
        frames: list[Image.Image] = []
        frame_files: list[str] = []
        visible_bottoms: list[int] = []
        warnings: list[str] = []

        for index in range(frame_count):
            frame = source.crop(
                (index * cell_width, 0, (index + 1) * cell_width, height)
            )
            bounds = alpha_bounds(frame)
            if bounds is None:
                raise ValueError(f"Frame {index + 1} is fully transparent.")
            if frame.getpixel((0, 0))[3] > 8:
                warnings.append(f"Frame {index + 1} top-left corner is not transparent.")
            visible_bottoms.append(bounds[3])
            filename = f"{args.prefix}-frame-{index + 1:02d}.png"
            frame.save(output_dir / filename, "PNG")
            frames.append(frame)
            frame_files.append(filename)

        bottom_spread = max(visible_bottoms) - min(visible_bottoms)
        if bottom_spread > max(4, round(height * 0.04)):
            warnings.append(
                f"Visible ground line varies by {bottom_spread}px; inspect for foot sliding."
            )

        sequence = [0, 1, 2, 3]
        duration_ms = max(40, round(1000 / max(args.fps, 0.1)))
        preview_frames = [frames[index] for index in sequence]
        preview_path = output_dir / f"{args.prefix}-preview.webp"
        preview_frames[0].save(
            preview_path,
            "WEBP",
            save_all=True,
            append_images=preview_frames[1:],
            duration=duration_ms,
            loop=0,
            lossless=True,
            method=6,
        )

        sheet_path = output_dir / f"{args.prefix}-spritesheet.png"
        source.save(sheet_path, "PNG")
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
        }
        manifest_path = output_dir / f"{args.prefix}-cycle.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
