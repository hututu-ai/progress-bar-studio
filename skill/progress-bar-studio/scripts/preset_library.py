#!/usr/bin/env python3
"""Create and inspect explicit, reusable ElleFlow brand presets."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path

from asset_validation import (AssetError, contained_file, read_object, read_image,
                              cycle_files, sha256, config_sha256)


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
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?", color):
            raise PresetError(f"Palette color must be #RRGGBB or #RRGGBBAA: {color}")
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


def copy_cycle_bundle(source: Path, assets_dir: Path) -> dict:
    """Validate and copy only files named by an approved four-frame cycle."""
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise PresetError(f"Walk-cycle directory not found: {source}")
    manifests = sorted(source.glob("*-cycle.json"))
    if len(manifests) != 1:
        raise PresetError("Walk-cycle directory must contain exactly one *-cycle.json manifest.")
    manifest, required = cycle_files(source, manifests[0].name)
    destination = assets_dir / "walk-cycle"
    for relative in required:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(contained_file(source, relative), target)
    relative_root = destination.relative_to(assets_dir.parent)
    return {
        "manifest": str(relative_root / manifests[0].name),
        "frames": [str(relative_root / frame) for frame in manifest["frames"]],
        "fps": manifest["fps"],
        "playbackOrder": manifest["playbackOrder"],
    }


def validate_assets(preset: dict, root: Path) -> list[str]:
    """Decode all referenced assets without reading outside this preset."""
    character, style = preset.get("character"), preset.get("style")
    if not isinstance(character, dict) or not isinstance(style, dict):
        raise PresetError("Preset requires character and style objects.")
    variant = style.get("variant")
    if not isinstance(variant, str) or not variant.strip():
        raise PresetError("Verified presets require the approved --style-variant.")
    palette = preset.get("palette")
    if not isinstance(palette, dict) or not palette:
        raise PresetError("Verified presets require at least one approved --palette token.")
    parse_palette([f"{key}={value}" for key, value in palette.items()])
    placement = preset.get("placement")
    if not isinstance(placement, dict):
        raise PresetError("Verified presets require the approved placement and scale.")
    scale = placement.get("overlayScale")
    if (isinstance(scale, bool) or not isinstance(scale, (int, float))
            or not math.isfinite(scale) or scale <= 0):
        raise PresetError("Verified presets require a positive finite --overlay-scale.")
    label = placement.get("label")
    if not isinstance(label, str) or not label.strip():
        raise PresetError("Verified presets require the approved --placement.")
    for axis in ("x", "y"):
        position = placement.get(axis)
        if (isinstance(position, bool) or not isinstance(position, (int, float))
                or not math.isfinite(position)):
            raise PresetError(f"Verified presets require finite --position-{axis}.")
    mode, asset, cycle = character.get("mode"), character.get("asset"), character.get("cycle")
    required = []
    if mode == "none":
        if asset or cycle:
            raise PresetError("No-character mode cannot contain character assets.")
    elif mode == "single-pose":
        if cycle:
            raise PresetError("Single-pose mode cannot contain a walk cycle.")
        read_image(contained_file(root, asset), transparent=True, image_format="PNG")
        required.append(asset)
    elif mode == "walk-cycle":
        if asset or not isinstance(cycle, dict):
            raise PresetError("Walk-cycle mode requires a complete cycle and no single character asset.")
        manifest_path = contained_file(root, cycle.get("manifest"))
        manifest, files = cycle_files(manifest_path.parent, manifest_path.name)
        relative_root = manifest_path.parent.relative_to(root)
        expected_frames = [str(relative_root / frame) for frame in manifest["frames"]]
        if (cycle.get("frames") != expected_frames or cycle.get("fps") != manifest["fps"]
                or cycle.get("playbackOrder") != manifest["playbackOrder"]):
            raise PresetError("Preset cycle metadata does not match its manifest.")
        required.extend(str(relative_root / item) for item in files)
    else:
        raise PresetError("Unknown character mode.")
    if style.get("route") not in ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "custom"):
        raise PresetError("Unknown style route.")
    reference = style.get("reference")
    if style.get("route") == "custom" and not reference:
        raise PresetError("Custom style requires a reference image.")
    if reference:
        read_image(contained_file(root, reference))
        required.append(reference)
    return required


def save_preset(args: argparse.Namespace) -> dict:
    library = args.library_dir.expanduser().resolve()
    preset_dir = library / slugify(args.name)
    if preset_dir.exists():
        raise PresetError(
            f"Preset already exists: {preset_dir}. Choose a different name; existing presets are never overwritten."
        )
    if args.character_mode == "none" and (args.character_image or args.character_cycle_dir):
        raise PresetError("No-character mode cannot save character assets.")
    if args.character_mode == "single-pose" and args.character_cycle_dir:
        raise PresetError("Single-pose mode cannot save a walk-cycle directory.")
    if args.character_mode == "single-pose" and not args.character_image:
        raise PresetError("Single-pose mode requires --character-image.")
    if args.character_mode == "walk-cycle" and not args.character_cycle_dir:
        raise PresetError("Walk-cycle mode requires --character-cycle-dir with four approved transparent frames.")
    if args.character_mode == "walk-cycle" and args.character_image:
        raise PresetError("Walk-cycle mode saves the approved cycle directory, not one character image.")
    if args.resolution or args.canvas_width or args.canvas_height:
        raise PresetError(
            "Output resolution and canvas belong to the current delivery; choose them again for each video."
        )
    if args.style == "custom" and not args.style_reference:
        raise PresetError("Custom style requires --style-reference.")

    if not args.sample_approved or not args.final_export_approved:
        raise PresetError("Saving a verified preset requires --sample-approved and --final-export-approved.")
    palette = parse_palette(args.palette)
    for label, value in (("overlay scale", args.overlay_scale), ("position x", args.position_x), ("position y", args.position_y)):
        if value is not None and (not math.isfinite(value) or (label == "overlay scale" and value <= 0)):
            raise PresetError(f"Invalid {label}; use a finite value and a positive scale.")
    if args.character_image:
        read_image(args.character_image.expanduser().resolve(), transparent=True, image_format="PNG")
    if args.style_reference:
        read_image(args.style_reference.expanduser().resolve())

    assets_dir = preset_dir / "assets"
    assets_dir.mkdir(parents=True)
    try:
        character_asset = (
            copy_asset(args.character_image, assets_dir, "character")
            if args.character_image
            else None
        )
        cycle_bundle = (
            copy_cycle_bundle(args.character_cycle_dir, assets_dir)
            if args.character_cycle_dir
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
        preset = {
            "schemaVersion": 4,
            "status": "verified",
            "sampleApproved": True,
            "finalExportApproved": True,
            "name": args.name,
            "character": {
                "mode": args.character_mode,
                "asset": character_asset,
                "cycle": cycle_bundle,
            },
            "style": {
                "route": args.style,
                "variant": args.style_variant,
                "reference": style_reference,
                "chapterCountPolicy": "content-adaptive",
            },
            "palette": palette,
            "placement": placement,
        }
        required = validate_assets(preset, preset_dir)
        preset["assetChecksums"] = {item: sha256(contained_file(preset_dir, item)) for item in sorted(required)}
        preset["configSha256"] = config_sha256(preset)
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
        "status": "verified",
        "reuseEligible": True,
        "characterMode": args.character_mode,
        "style": args.style,
        "palette": preset["palette"],
        "placement": preset["placement"],
    }


def show_preset(path: Path, require_verified: bool = False) -> dict:
    preset_path = path.expanduser().resolve()
    if not preset_path.is_file():
        raise PresetError(f"Preset not found: {preset_path}")
    preset = read_object(preset_path)
    version = preset.get("schemaVersion")
    if version not in (1, 2, 3, 4) or not isinstance(preset.get("name"), str):
        raise PresetError(f"Unsupported preset format: {preset_path}")
    issues = []
    if version != 4:
        # Legacy layouts remain inspectable. Neither a name nor old metadata
        # proves sample approval, and older bundles lack integrity records.
        status = "unverified"
        issues.append("Legacy preset: recheck assets and obtain sample/final-export approval before saving a new verified preset.")
    else:
        status = "verified"
        try:
            if (preset.get("status") != "verified" or preset.get("sampleApproved") is not True
                    or preset.get("finalExportApproved") is not True):
                raise PresetError("Preset lacks sample and final-export approval records.")
            if preset.get("configSha256") != config_sha256(preset):
                raise PresetError("Preset configuration changed or lacks its integrity checksum.")
            required = validate_assets(preset, preset_path.parent)
            checksums = preset.get("assetChecksums")
            if not isinstance(checksums, dict) or set(checksums) != set(required):
                raise PresetError("Asset checksum list does not match the required bundle files.")
            for relative, expected in checksums.items():
                if sha256(contained_file(preset_path.parent, relative)) != expected:
                    raise PresetError(f"Asset checksum mismatch: {relative}")
        except (AssetError, PresetError, OSError, TypeError, ValueError) as exc:
            status = "invalid"
            issues.append(str(exc))
    if require_verified and status != "verified":
        raise PresetError("Preset is not eligible for verified reuse: " + "; ".join(issues))
    return {**preset, "preset": str(preset_path), "status": status,
            "reuseEligible": status == "verified", "inspectionIssues": issues}


def show_default(library_dir: Path, require_verified: bool = False) -> dict:
    library = library_dir.expanduser().resolve()
    pointer = library / "default-preset.json"
    if not pointer.exists():
        return {"status": "not_found", "reuseEligible": False, "defaultPreset": str(pointer),
                "inspectionIssues": [], "nextAction": "Continue with a new project; no default preset is saved."}
    data = read_object(pointer)
    target = data.get("preset")
    if not isinstance(target, str) or not target:
        raise PresetError("Default preset pointer is incomplete; select an existing preset instead.")
    path = Path(target).expanduser()
    path = path if path.is_absolute() else library / path
    path = path.resolve()
    if not path.is_relative_to(library):
        raise PresetError("Default preset points outside its library; select the intended local preset explicitly.")
    return show_preset(path, require_verified) | {"defaultPreset": str(pointer)}


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
    save.add_argument(
        "--character-cycle-dir",
        type=Path,
        help="Directory containing an approved four-frame cycle, manifest, sprite sheet, and preview.",
    )
    save.add_argument("--style", choices=("S1", "S2", "S3", "S4", "S5", "S6", "S7", "custom"), required=True)
    save.add_argument("--style-variant")
    save.add_argument("--style-reference", type=Path)
    save.add_argument("--palette", action="append", default=[], metavar="KEY=#RRGGBB[AA]")
    save.add_argument("--resolution", choices=("1080p", "2K", "4K"))
    save.add_argument("--canvas-width", type=int)
    save.add_argument("--canvas-height", type=int)
    save.add_argument("--overlay-scale", type=float)
    save.add_argument("--placement")
    save.add_argument("--position-x", type=float)
    save.add_argument("--position-y", type=float)
    save.add_argument("--sample-approved", action="store_true", help="Record explicit approval of the rendered sample; a waiver is not approval.")
    save.add_argument("--final-export-approved", action="store_true", help="Record the creator's explicit permission to render the final master.")
    save.add_argument("--set-default", action="store_true")
    save.add_argument("--json", action="store_true")

    show = subparsers.add_parser("show", help="Read one saved preset.")
    target = show.add_mutually_exclusive_group(required=True)
    target.add_argument("--preset", type=Path)
    target.add_argument("--default", action="store_true", help="Inspect the library's default pointer without guessing a preset.")
    show.add_argument("--library-dir", type=Path, help="Required with --default; use the creator's known preset library.")
    show.add_argument("--require-verified", action="store_true", help="Fail unless approval and asset-integrity checks pass.")
    show.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "save":
            result = save_preset(args)
        elif args.default:
            if args.library_dir is None:
                raise PresetError("Use --library-dir with --default.")
            result = show_default(args.library_dir, args.require_verified)
        else:
            result = show_preset(args.preset, args.require_verified)
    except (PresetError, AssetError, OSError) as exc:
        print(f"Preset error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Preset: {result.get('preset', 'none saved')}")
        print(f"Status: {result['status']} | Reuse eligible: {result['reuseEligible']}")
        for issue in result.get("inspectionIssues", []):
            print(f"Warning: {issue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
