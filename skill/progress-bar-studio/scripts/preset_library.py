#!/usr/bin/env python3
"""Create and inspect explicit, reusable ElleFlow brand presets."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


class PresetError(Exception):
    """A preset-library issue that can be shown directly to the user."""


def slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip(".-")
    return slug.lower() or "elleflow-preset"


def parse_palette(values: list[str]) -> dict[str, str]:
    palette: dict[str, str] = {}
    for value in values:
        key, separator, color = value.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", key):
            raise PresetError("Palette values must use key=#RRGGBB, for example primary=#E89AB3.")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise PresetError(f"Palette color must be a six-digit HEX value: {color}")
        palette[key] = color.upper()
    return palette


def copy_asset(source: Path, assets_dir: Path, stem: str) -> str:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise PresetError(f"Asset file not found: {source}")
    extension = source.suffix.lower() or ".bin"
    destination = assets_dir / f"{stem}{extension}"
    shutil.copy2(source, destination)
    return str(destination.relative_to(assets_dir.parent))


def save_preset(args: argparse.Namespace) -> dict:
    library = args.library_dir.expanduser().resolve()
    preset_dir = library / slugify(args.name)
    if preset_dir.exists():
        raise PresetError(
            f"Preset already exists: {preset_dir}. Choose a different name; existing presets are never overwritten."
        )
    if args.character_mode == "none" and args.character_image:
        raise PresetError("A character image requires single-pose or walk-cycle mode.")
    if args.style == "custom" and not args.style_reference:
        raise PresetError("Custom style requires --style-reference.")

    assets_dir = preset_dir / "assets"
    assets_dir.mkdir(parents=True)
    try:
        character_asset = (
            copy_asset(args.character_image, assets_dir, "character")
            if args.character_image
            else None
        )
        style_reference = (
            copy_asset(args.style_reference, assets_dir, "style-reference")
            if args.style_reference
            else None
        )
        placement = {
            key: value
            for key, value in {
                "label": args.placement,
                "x": args.position_x,
                "y": args.position_y,
                "overlayScale": args.overlay_scale,
            }.items()
            if value is not None
        }
        render = {
            key: value
            for key, value in {
                "resolution": args.resolution,
                "canvasWidth": args.canvas_width,
                "canvasHeight": args.canvas_height,
            }.items()
            if value is not None
        }
        preset = {
            "schemaVersion": 2,
            "name": args.name,
            "character": {"mode": args.character_mode, "asset": character_asset},
            "style": {
                "route": args.style,
                "variant": args.style_variant,
                "reference": style_reference,
                "chapterCountPolicy": "content-adaptive",
            },
            "palette": parse_palette(args.palette),
            "render": render,
            "placement": placement,
        }
        preset_path = preset_dir / "preset.json"
        preset_path.write_text(json.dumps(preset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.set_default:
            library.mkdir(parents=True, exist_ok=True)
            (library / "default-preset.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": 2,
                        "preset": str(preset_path),
                        "name": args.name,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
    except Exception:
        if preset_dir.exists():
            shutil.rmtree(preset_dir)
        raise

    return {
        "preset": str(preset_path),
        "defaultPreset": str(library / "default-preset.json") if args.set_default else None,
        "characterMode": args.character_mode,
        "style": args.style,
        "palette": preset["palette"],
        "render": preset["render"],
        "placement": preset["placement"],
    }


def show_preset(path: Path) -> dict:
    preset_path = path.expanduser().resolve()
    if not preset_path.is_file():
        raise PresetError(f"Preset not found: {preset_path}")
    try:
        preset = json.loads(preset_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PresetError(f"Cannot read preset: {preset_path}") from exc
    if preset.get("schemaVersion") not in (1, 2) or not isinstance(preset.get("name"), str):
        raise PresetError(f"Unsupported preset format: {preset_path}")
    preset["preset"] = str(preset_path)
    return preset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save or inspect reusable ElleFlow brand presets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    save = subparsers.add_parser(
        "save", help="Save one confirmed character and complete visual configuration."
    )
    save.add_argument("--name", required=True)
    save.add_argument("--library-dir", type=Path, required=True)
    save.add_argument("--character-mode", choices=("none", "single-pose", "walk-cycle"), required=True)
    save.add_argument("--character-image", type=Path)
    save.add_argument("--style", choices=("S1", "S2", "S3", "S4", "custom"), required=True)
    save.add_argument("--style-variant")
    save.add_argument("--style-reference", type=Path)
    save.add_argument("--palette", action="append", default=[], metavar="KEY=#RRGGBB")
    save.add_argument("--resolution", choices=("1080p", "2K", "4K"))
    save.add_argument("--canvas-width", type=int)
    save.add_argument("--canvas-height", type=int)
    save.add_argument("--overlay-scale", type=float)
    save.add_argument("--placement")
    save.add_argument("--position-x", type=float)
    save.add_argument("--position-y", type=float)
    save.add_argument("--set-default", action="store_true")
    save.add_argument("--json", action="store_true")

    show = subparsers.add_parser("show", help="Read one saved preset.")
    show.add_argument("--preset", type=Path, required=True)
    show.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = save_preset(args) if args.command == "save" else show_preset(args.preset)
    except PresetError as exc:
        print(f"Preset error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Preset: {result['preset']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
