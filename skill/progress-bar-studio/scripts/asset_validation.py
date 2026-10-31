#!/usr/bin/env python3
"""Shared, read-only checks for self-contained transparent character assets."""
from __future__ import annotations

import hashlib
import json
import math
import io
from pathlib import Path, PurePosixPath

try:
    from PIL import Image
except ImportError:
    Image = None  # No-character presets do not require image processing.


class AssetError(ValueError):
    """An invalid or unsafe character asset."""


def contained_file(root: Path, relative: str) -> Path:
    """Resolve only ordinary files inside root; never follow asset symlinks."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise AssetError("Asset paths must be nonempty, relative POSIX paths.")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or any(part in (".", "..") for part in relative.split("/")):
        raise AssetError(f"Unsafe asset path: {relative}")
    root = root.resolve()
    candidate = root
    for part in parts.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise AssetError(f"Asset symlinks are not allowed: {relative}")
    if not candidate.resolve().is_relative_to(root) or not candidate.is_file():
        raise AssetError(f"Asset file is missing or outside its bundle: {relative}")
    return candidate


def read_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssetError(f"Cannot read JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise AssetError(f"JSON must contain an object: {path.name}")
    return value


def require_transparency(image: Image.Image, label: str) -> Image.Image:
    if "A" not in image.getbands() and "transparency" not in image.info:
        raise AssetError(f"{label} has no Alpha channel; remove its background first.")
    rgba = image.convert("RGBA")
    low, high = rgba.getchannel("A").getextrema()
    if high == 0:
        raise AssetError(f"{label} is fully transparent.")
    if low != 0:
        raise AssetError(f"{label} has no fully transparent pixels; remove its background first.")
    if high != 255:
        raise AssetError(f"{label} has no opaque pixels; inspect for a translucent body.")
    return rgba


def visible_bounds(image):
    """Geometry only: ignore near-invisible specks, without rewriting source Alpha."""
    box = image.getchannel("A").point(lambda a: 255 if a > 32 else 0).getbbox()
    if box is None:
        raise AssetError("Character has no substantial visible pixels.")
    return box


def visible_contact(image, point):
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        raise AssetError("Each foot anchor must have two coordinates.")
    x, y = point
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in point):
        raise AssetError("Foot anchors must be finite coordinates.")
    if not (0 <= x < image.width and 0 <= y < image.height) or image.getpixel((int(x), int(y)))[3] <= 32:
        raise AssetError("Foot anchor must be on a visible character pixel, not transparent padding or Alpha noise.")
    return float(x), float(y)


def default_contact(image):
    left, top, right, bottom = visible_bounds(image)
    y = bottom - 1
    xs = [x for x in range(left, right) if image.getpixel((x, y))[3] > 32]
    return xs[len(xs) // 2], y


def interior_alpha_stats(image):
    """Diagnostic only: translucent artwork may be intentional; require visual review."""
    from PIL import ImageFilter
    from statistics import median
    alpha=image.getchannel('A')
    interior=alpha.point(lambda a:255 if a>32 else 0).filter(ImageFilter.MinFilter(5))
    values=[a for a,m in zip(alpha.getdata(),interior.getdata()) if m]
    return {'pixels':len(values),'median':median(values) if values else None,
            'fractionBelow240':sum(a<240 for a in values)/len(values) if values else None}


def validate_frames(images):
    """Technical checks only. Four distinct images do NOT certify a real gait."""
    if len(images) != 4:
        raise AssetError("A walk cycle requires exactly four frames.")
    if len({im.size for im in images}) != 1:
        raise AssetError("All four frames must have the same canvas size.")
    signatures = []
    for i, im in enumerate(images):
        if im.mode != "RGBA":
            raise AssetError("Walk frames must be real RGBA images.")
        require_transparency(im, f"Frame {i + 1}")
        # Ignore invisible RGB and translation-only copies of an identical pose.
        visible_bounds(im)
        canonical = Image.alpha_composite(Image.new("RGBA", im.size), im)
        cropped = canonical.crop(canonical.getchannel("A").getbbox())
        signatures.append((cropped.size, hashlib.sha256(cropped.tobytes()).hexdigest()))
    if len(set(signatures)) != 4:
        raise AssetError("Repeated/translated copies of the same pose cannot form a four-frame walk cycle.")
    return images


def publish_new_files(directory, files):
    """Reserve every filename before writing; never replace existing user assets."""
    directory = Path(directory)
    targets = [directory / name for name in files]
    if any(Path(name).name != name for name in files):
        raise AssetError("Output names must be plain filenames.")
    if any(p.exists() or p.is_symlink() for p in targets):
        raise AssetError("Output already exists; choose a new version directory or prefix.")
    directory.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for target in targets:
            with target.open("xb"):
                pass
            created.append(target)
        for target, payload in zip(targets, files.values()):
            with target.open("wb") as handle:
                handle.write(payload)
    except BaseException:
        # Roll back only files exclusively created by this call, never pre-existing files.
        for target in created:
            target.unlink(missing_ok=True)
        raise


def image_bytes(image, format="PNG", **kwargs):
    stream = io.BytesIO()
    image.save(stream, format, **kwargs)
    return stream.getvalue()


def read_image(path: Path, *, transparent: bool = False, image_format: str | None = None) -> Image.Image:
    if Image is None:
        raise AssetError("Pillow is required to validate character/reference images.")
    try:
        with Image.open(path) as image:
            if image_format and image.format != image_format:
                raise AssetError(f"{path.name} must be a real {image_format} image.")
            image.load()
            return require_transparency(image, path.name) if transparent else image.copy()
    except (OSError, Image.DecompressionBombError) as exc:
        raise AssetError(f"Cannot decode image: {path.name}") from exc


def cycle_files(source: Path, manifest_name: str) -> tuple[dict, list[str]]:
    manifest = read_object(contained_file(source, manifest_name))
    frames = manifest.get("frames")
    if manifest.get("frameCount") != 4 or not isinstance(frames, list) or len(frames) != 4:
        raise AssetError("Walk-cycle manifest must describe exactly four frames.")
    if any(not isinstance(frame, str) for frame in frames) or len(set(frames)) != 4:
        raise AssetError("Walk-cycle frames must be four distinct relative paths.")
    order, fps = manifest.get("playbackOrder"), manifest.get("fps")
    if (not isinstance(order, list) or any(type(item) is not int for item in order)
            or sorted(order) != [1, 2, 3, 4]):
        raise AssetError("Walk-cycle playbackOrder must contain 1, 2, 3, and 4 once each.")
    if isinstance(fps, bool) or not isinstance(fps, (float, int)) or not math.isfinite(fps) or fps <= 0:
        raise AssetError("Walk-cycle fps must be a finite positive number.")
    required = [manifest_name, *frames, manifest.get("spriteSheet"), manifest.get("preview")]
    paths = [contained_file(source, item) for item in required]
    if len(set(paths)) != len(paths):
        raise AssetError("Walk-cycle bundle files must have distinct paths.")
    images = [read_image(path, transparent=True, image_format="PNG") for path in paths[1:5]]
    validate_frames(images)
    width, height = images[0].size
    if "frameSize" in manifest and manifest["frameSize"] != {"width": width, "height": height}:
        raise AssetError("Walk-cycle frameSize does not match decoded frames.")
    sheet = read_image(paths[5], transparent=True, image_format="PNG")
    if sheet.size != (width * 4, height):
        raise AssetError("Sprite sheet must contain four equal-width frame cells.")
    for index, frame in enumerate(images):
        if sheet.crop((index * width, 0, (index + 1) * width, height)).tobytes() != frame.tobytes():
            raise AssetError("Sprite sheet does not match the four saved frames.")
    try:
        with Image.open(paths[6]) as preview:
            if preview.format != "WEBP" or preview.n_frames != 4 or preview.info.get("loop") != 0:
                raise AssetError("Walk-cycle preview must be a looping four-frame WebP.")
            for index in range(4):
                preview.seek(index)
                preview.load()
                if preview.size != (width, height):
                    raise AssetError("Preview canvas does not match the frames.")
                actual = require_transparency(preview, f"Preview frame {index + 1}")
                expected = images[order[index] - 1]
                # Invisible RGB values may be discarded by WebP; compare visible
                # pixels and Alpha after canonicalizing fully transparent pixels.
                blank = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                if (Image.alpha_composite(blank, actual).tobytes()
                        != Image.alpha_composite(blank, expected).tobytes()):
                    raise AssetError("Preview frame content/order does not match the manifest.")
                if preview.info.get("duration") != max(1, round(1000 / fps)):
                    raise AssetError("Preview timing does not match the manifest fps.")
    except (OSError, Image.DecompressionBombError) as exc:
        raise AssetError("Cannot decode walk-cycle preview.") from exc
    return manifest, required


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def config_sha256(preset: dict) -> str:
    data = {key: value for key, value in preset.items() if key != "configSha256"}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
