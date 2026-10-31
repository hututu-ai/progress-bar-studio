#!/usr/bin/env python3
"""Deterministic RGBA chapter overlays. No source-video or asset-generation side effects."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from asset_validation import validate_frames, visible_bounds, visible_contact, default_contact
from font_validation import require_glyphs

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:
    raise SystemExit("Pillow is required. Install it in the chosen task environment first.") from exc

STYLE_NAMES = {
    "S1": ("capsule", "章节胶囊", "Chapter capsules"),
    "S2": ("runway", "分段跑道", "Segmented runway"),
    "S3": ("text", "文字推进", "Text progress"),
    "S4": ("band", "标签分栏带", "Divided label band"),
    "S5": ("current-card", "当前章节卡", "Current chapter card"),
    "S6": ("ring", "角落圆环", "Corner ring"),
    "S7": ("hanging-tabs", "顶部悬挂签", "Hanging chapter tabs"),
}
TOKENS = ("surface", "active", "inactive", "text", "active-text", "outline", "shadow")
OPTIONAL_TOKENS = ("progress", "progress-inactive", "muted-text", "accent-text")
PALETTE_PRESETS = {
    "cream-tea": {"surface": "#FBF7F0", "active": "#C4A38A", "inactive": "#EDE6DE",
                  "text": "#55463D", "active-text": "#382B24", "outline": "#DAD0C5", "shadow": "#493D2E08",
                  "muted-text": "#82766D", "accent-text": "#825B42"},
    "sage": {"surface": "#F5F6EE", "active": "#A2B28D", "inactive": "#E3E7D9",
             "text": "#35483B", "active-text": "#263729", "outline": "#CBD3BF", "shadow": "#283B2A08",
             "muted-text": "#6E796A", "accent-text": "#405D45"},
    "lavender": {"surface": "#F6F2FC", "active": "#C4B4D9", "inactive": "#E9E2F0",
                 "text": "#51455E", "active-text": "#392F45", "outline": "#D9CEE4", "shadow": "#43305208",
                 "muted-text": "#82758E", "accent-text": "#A64077", "progress": "#A64077"},
    "navy-cream": {"surface": "#172541", "active": "#E7DCC5", "inactive": "#35445F",
                   "text": "#F6F0E3", "active-text": "#172541", "outline": "#58667E", "shadow": "#111A2A10",
                   "muted-text": "#C0C7D4", "accent-text": "#F1DEB6"},
}
DEMO_PALETTE = dict(PALETTE_PRESETS["cream-tea"])
FONT_CANDIDATES = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "C:/Windows/Fonts/msyh.ttc",
)
MAC_FONT_NAMES = (
    "SourceHanSansCN-Regular.otf",
    "SourceHanSansSC-Regular.otf",
    "NotoSansCJK-Regular.ttc",
    "NotoSansCJKsc-Regular.otf",
    "NotoSansSC-Regular.ttf",
    "Noto Sans SC Regular.ttf",
    "PingFang.ttc",
)
MAX_PIXELS = 16_777_216
MAX_FRAMES = 432_000


class ConfigError(ValueError):
    """The requested output is invalid or cannot remain legible."""


def finite_number(value, name, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ConfigError(f"{name} must be a finite number")
    if low is not None and value < low or high is not None and value > high:
        raise ConfigError(f"{name} must be between {low} and {high}")
    return float(value)


def integer(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ConfigError(f"{name} must be an integer from {low} to {high}")
    return value


def color(value):
    if not isinstance(value, str) or len(value) not in (7, 9) or not value.startswith("#"):
        raise ConfigError("palette colors must be #RRGGBB or #RRGGBBAA")
    try:
        parts = tuple(int(value[i:i + 2], 16) for i in range(1, len(value), 2))
    except ValueError as exc:
        raise ConfigError("palette colors must be hexadecimal") from exc
    return parts + (255,) if len(parts) == 3 else parts


def luminance(rgba):
    rgb = [c / 255 for c in rgba[:3]]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
    return .2126 * linear[0] + .7152 * linear[1] + .0722 * linear[2]


def contrast(a, b):
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + .05) / (dark + .05)


@dataclass(frozen=True)
class Chapter:
    start: float
    end: float
    title: str
    subtitle: str = ""


@dataclass(frozen=True)
class State:
    time: float
    progress: float
    chapter: int
    chapter_progress: float


@dataclass
class Config:
    duration: float
    fps: float
    width: int
    height: int
    style: str
    chapters: list[Chapter]
    palette: dict
    character: dict
    font_path: Path
    base_dir: Path
    demo_label: bool = False
    visual_revision: str = "legacy"
    font_bold_path: Path | None = None
    progress_mode: str = "time-linear"

    def state(self, time):
        time = finite_number(time, "time")
        t = min(self.duration, max(0., time))
        index = len(self.chapters) - 1
        for i, chapter in enumerate(self.chapters):
            # Boundaries are half-open; the exact end of the clip belongs to the last chapter.
            if t < chapter.end:
                index = i
                break
        c = self.chapters[index]
        local = min(1., max(0., (t - c.start) / (c.end - c.start)))
        progress = (index+local)/len(self.chapters) if self.progress_mode == "chapter-weighted" else t/self.duration
        return State(t, progress, index, local)


def choose_font(value, base_dir, needs_cjk=True):
    if value is not None:
        if not isinstance(value, str) or not value:
            raise ConfigError("font must be a local font-file path")
        candidate = Path(value).expanduser()
        candidate = candidate if candidate.is_absolute() else base_dir / candidate
        if not candidate.is_file():
            raise ConfigError(f"font does not exist: {candidate}")
        try:
            ImageFont.truetype(str(candidate), 24)
        except OSError as exc:
            raise ConfigError(f"font is not loadable: {candidate}") from exc
        return candidate.resolve()
    candidates = [Path(candidate) for candidate in FONT_CANDIDATES]
    # User-installed CJK fonts are common on Macs without the old PingFang path.
    # Use known font filenames only; never download fonts or scan unrelated files.
    for directory in (Path.home() / "Library/Fonts", Path("/Library/Fonts")):
        candidates.extend(directory / name for name in MAC_FONT_NAMES)
    for candidate in candidates:
        if candidate.is_file():
            try:
                ImageFont.truetype(str(candidate), 24)
            except OSError:
                continue
            return candidate.resolve()
    if not needs_cjk:
        candidate = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        if candidate.is_file():
            return candidate
    raise ConfigError("No CJK font found. Set font to a local Noto Sans CJK / Source Han Sans font file.")


def validate_config(data, base_dir=None, *, allow_unapproved=False):
    if not isinstance(data, dict):
        raise ConfigError("config must be a JSON object")
    base_dir = Path(base_dir or ".").resolve()
    known = {"schemaVersion", "duration", "fps", "width", "height", "style", "chapters", "palette", "palettePreset", "character", "font", "fontBold", "demoLabel", "visualRevision", "progressMode"}
    unknown = set(data) - known
    if unknown:
        raise ConfigError("unknown config field(s): " + ", ".join(sorted(unknown)))
    if type(data.get("schemaVersion", 1)) is not int or data.get("schemaVersion", 1) != 1:
        raise ConfigError("schemaVersion must be 1")
    duration = finite_number(data.get("duration"), "duration", .01, 43_200)
    fps = finite_number(data.get("fps"), "fps", 1, 120)
    width = integer(data.get("width"), "width", 320, 7680)
    height = integer(data.get("height"), "height", 96, 4320)
    if width * height > MAX_PIXELS:
        raise ConfigError(f"canvas exceeds {MAX_PIXELS:,} pixels; use a smaller overlay canvas")
    if math.ceil(duration * fps - 1e-9) > MAX_FRAMES:
        raise ConfigError(f"output exceeds {MAX_FRAMES:,} frames; split the export deliberately")
    style = data.get("style")
    aliases = {v[0]: k for k, v in STYLE_NAMES.items()}
    style = aliases.get(style, style) if isinstance(style, str) else None
    if style not in STYLE_NAMES:
        raise ConfigError("style must be S1–S7 or capsule/runway/text/band/current-card/ring/hanging-tabs")
    preset = data.get("palettePreset")
    if preset is not None and (not isinstance(preset, str) or preset not in PALETTE_PRESETS):
        raise ConfigError("palettePreset must be cream-tea, sage, lavender or navy-cream")
    palette = data.get("palette", {} if preset else None)
    if preset and isinstance(palette, dict):
        palette = {**PALETTE_PRESETS[preset], **palette}
    if not isinstance(palette, dict) or not set(TOKENS) <= set(palette) or set(palette) - set(TOKENS) - set(OPTIONAL_TOKENS):
        raise ConfigError("palette must supply: " + ", ".join(TOKENS) + "; optional: " + ", ".join(OPTIONAL_TOKENS))
    palette = {key: color(value) for key, value in palette.items()}
    palette.setdefault("progress", palette["active"])
    palette.setdefault("progress-inactive", palette["inactive"])
    palette.setdefault("muted-text", palette["text"])
    palette.setdefault("accent-text", palette["text"])
    if any(palette[k][3] != 255 for k in ("surface", "active", "inactive", "text", "active-text")):
        raise ConfigError("surface, active, inactive, text and active-text must be opaque for predictable contrast")
    if contrast(palette["text"], palette["surface"]) < 4.5:
        raise ConfigError("text/surface contrast must be at least 4.5:1; revise the palette")
    if contrast(palette["active-text"], palette["active"]) < 4.5:
        raise ConfigError("active-text/active contrast must be at least 4.5:1; revise the palette")
    raw = data.get("chapters")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 24:
        raise ConfigError("chapters must contain 1–24 entries")
    chapters = []
    # Tolerance only admits floating-point/serialization noise, never an entire frame.
    tolerance = min(.001, .01 / fps)
    previous = 0.
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict) or not {"start", "end", "title"} <= set(entry) or set(entry) - {"start", "end", "title", "subtitle"}:
            raise ConfigError(f"chapter {i + 1} must contain start, end and title; subtitle is optional")
        start = finite_number(entry["start"], f"chapter {i + 1} start", 0, duration)
        end = finite_number(entry["end"], f"chapter {i + 1} end", 0, duration)
        if abs(start - previous) > tolerance:
            raise ConfigError(f"chapter {i + 1} has an overlap or gap; chapters must continuously cover 0..duration")
        start = previous
        if end <= start:
            raise ConfigError(f"chapter {i + 1} must have positive duration")
        title = entry["title"]
        if not isinstance(title, str) or not title.strip() or len(title) > 200 or any(ord(c) < 32 for c in title):
            raise ConfigError(f"chapter {i + 1} title must be 1–200 printable characters")
        subtitle = entry.get("subtitle", "")
        if not isinstance(subtitle, str) or len(subtitle) > 120 or any(ord(c) < 32 for c in subtitle):
            raise ConfigError(f"chapter {i + 1} subtitle must be at most 120 printable characters")
        chapters.append(Chapter(start, end, title.strip(), subtitle.strip()))
        previous = end
    if abs(previous - duration) > tolerance:
        raise ConfigError("the last chapter must end at duration")
    last = chapters[-1]
    chapters[-1] = Chapter(last.start, duration, last.title, last.subtitle)
    character = data.get("character", {"mode": "none"})
    if not isinstance(character, dict) or character.get("mode") not in ("none", "single-pose", "walk-cycle"):
        raise ConfigError("character.mode must be none, single-pose or walk-cycle")
    character = copy.deepcopy(character)
    if character["mode"] == "none":
        if set(character) != {"mode"}:
            raise ConfigError("none mode must not contain assets, paths or character options")
    else:
        allowed = {"mode", "approved", "path", "frames", "contacts", "height", "cadence", "bodyPivotX"}
        if set(character) - allowed:
            raise ConfigError("unknown character field")
        if character.get("approved") is not True and not allow_unapproved:
            raise ConfigError("character assets must already be approved; this renderer never creates or approves them")
        character["height"] = finite_number(character.get("height", min(width * .09, height * .32)), "character.height", 12, min(width * .3, height * .55))
        if character["mode"] == "single-pose":
            if "frames" in character or "cadence" in character:
                raise ConfigError("single-pose accepts path, not frames or cadence")
            paths = [character.get("path")]
        else:
            if "path" in character:
                raise ConfigError("walk-cycle accepts frames, not path")
            paths = character.get("frames")
            if not isinstance(paths, list) or len(paths) != 4:
                raise ConfigError("walk-cycle requires exactly four approved PNG frames in playback order")
            character["cadence"] = finite_number(character.get("cadence", 6), "character.cadence", 1, 12)
        resolved = []
        for value in paths:
            if not isinstance(value, str) or not value:
                raise ConfigError("each character asset must be a local PNG path")
            path = Path(value).expanduser()
            path = path if path.is_absolute() else base_dir / path
            if path.suffix.lower() != ".png" or not path.is_file():
                raise ConfigError(f"character PNG missing: {path}")
            resolved.append(str(path.resolve()))
        character["resolved_frames"] = resolved
        if "bodyPivotX" in character:
            finite_number(character["bodyPivotX"], "character.bodyPivotX", 0, 16_384)
        contacts = character.get("contacts")
        if contacts is not None:
            if not isinstance(contacts, list) or len(contacts) != len(resolved):
                raise ConfigError("contacts must have one [x,y] source-pixel foot anchor per frame")
            for point in contacts:
                if not isinstance(point, list) or len(point) != 2:
                    raise ConfigError("each contact must be [x,y]")
                for value in point:
                    finite_number(value, "contact coordinate", 0, 16_384)
    if not isinstance(data.get("demoLabel", False), bool):
        raise ConfigError("demoLabel must be true or false")
    font_path = choose_font(data.get("font"), base_dir, any(ord(c) > 127 for chapter in chapters for c in chapter.title + chapter.subtitle))
    revision = data.get("visualRevision", "legacy")
    if revision not in ("legacy", "refined-20261030", "editorial-20261030", "readable-20261030"):
        raise ConfigError("unknown visualRevision")
    if revision == "editorial-20261030" and style != "S7":
        raise ConfigError("editorial-20261030 is an explicit S7 navigation revision")
    if revision == "readable-20261030" and style not in ("S1", "S2"):
        raise ConfigError("readable-20261030 supports chapter capsules and segmented runway")
    bold = choose_font(data["fontBold"], base_dir) if data.get("fontBold") else None
    actual_text = ''.join(ch.title + ch.subtitle for ch in chapters) + ('合成示意 / SAMPLE' if data.get('demoLabel') else '')
    try:
        require_glyphs(font_path, actual_text)
        if bold:
            require_glyphs(bold, actual_text)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    progress_mode = data.get("progressMode", "time-linear")
    if progress_mode not in ("time-linear", "chapter-weighted") or progress_mode == "chapter-weighted" and style not in ("S1", "S7"):
        raise ConfigError("chapter-weighted classic progress is supported only by equal-slot S1/S7")
    return Config(duration, fps, width, height, style, chapters, palette, character, font_path, base_dir, data.get("demoLabel", False), revision, bold, progress_mode)


def load_config(path):
    path = Path(path)
    try:
        return validate_config(json.loads(path.read_text(encoding="utf-8")), path.parent)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Cannot read JSON config: {exc}") from exc


@lru_cache(maxsize=128)
def font_at(path, size):
    return ImageFont.truetype(path, size)


class Renderer:
    def __init__(self, config):
        self.config = config
        self.scale = 2 if config.width * config.height <= 2_500_000 else 1
        self.palette = config.palette
        self.assets = []
        self.full_titles = [c.title for c in config.chapters]
        self.unit = config.width / 1280
        self.refined = config.visual_revision in ("refined-20261030", "editorial-20261030", "readable-20261030")
        self.readable = config.visual_revision == "readable-20261030"
        self.chapter_grid = False
        self.grid_bounds = []
        self.editorial_nav = config.visual_revision == "editorial-20261030"
        self.font_size = max(16, round(28 * self.unit))
        self.small_size = max(12, round(18 * self.unit))
        self.row_h = max(44, round(54 * self.unit))
        self.track_h = max(3, round(5 * self.unit))
        if self.refined and config.style in ("S1", "S2", "S7"):
            self.font_size = max(20, round(46 * self.unit))
            self.small_size = max(12, round(28 * self.unit))
            self.row_h = max(54, round(82 * self.unit))
        self.padding = max(12, round(24 * self.unit))
        self.char_h = config.character.get("height", 0)
        self.char_width = 0
        self.char_left = self.char_right = 0
        try:
            self._load_assets()
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc
        self.margin = round(config.width * .035)
        self.x0 = max(self.margin, math.ceil(self.char_left + 4))
        self.x1 = config.width - max(self.margin, math.ceil(self.char_right + 4))
        self.bottom = config.height - max(10, round(22 * self.unit))
        self.body_h = self.row_h if config.style not in ("S5", "S6") else max(72, round(90 * self.unit))
        self.body_y = self.bottom - self.body_h
        self.ground_y = self.body_y - max(14, round(25 * self.unit))
        if config.style == "S4":
            self.body_h = max(self.row_h, self.char_h + self.padding) if self.assets else max(38, round(44 * self.unit))
            self.body_y = self.bottom - self.body_h
            self.ground_y = self.bottom - self.padding / 2
        if config.style == "S7":
            self.tab_h = max(62, round(92 * self.unit))
            self.tab_extra = max(14, round(22 * self.unit))
            if self.refined:
                self.tab_h = max(70, round(110 * self.unit))
                self.tab_extra = max(10, round(16 * self.unit))
            if not self.editorial_nav and self.tab_h + self.tab_extra + 4 > config.height:
                raise ConfigError("canvas is too short for hanging tabs; increase height")
            self.ground_y = self.bottom - self.track_h
            if self.refined:
                # The single upper track is both the walk plane and the tag suspension rail.
                self.ground_y = self.char_h + max(12,12*self.unit)
                if not self.editorial_nav and self.ground_y + 124*self.unit > config.height-4:
                    raise ConfigError("canvas is too short for the hanging labels below the walk plane")
            if self.assets and not self.refined and self.ground_y - self.char_h < self.tab_h + self.tab_extra + 12:
                raise ConfigError("canvas is too short for hanging tabs and the approved character; increase height")
            if self.editorial_nav:
                self.ground_y = self.char_h + max(12, 16 * self.unit)
                if self.ground_y + 88 * self.unit > config.height - 4:
                    raise ConfigError("canvas is too short for the chapter navigation")
        # Ensure all pixels of approved assets and labels remain in the output canvas.
        if not self.readable and (self.body_y < 10 or self.ground_y - self.char_h < 4):
            raise ConfigError("canvas is too short for this style/character; increase height or use a shorter approved character")
        if self.readable:
            # New chapter counts must not move a reused rail to another vertical lane.
            self.ground_y = self.char_h+max(12,16*self.unit)
            self.body_y = self.ground_y+25*self.unit
            self.bottom = self.body_y+self.row_h
            if self.bottom+self.padding>config.height:
                config.height=math.ceil(self.bottom+self.padding)
            gap = max(8, 14*self.unit)
            available = [(self.x1-self.x0)/len(config.chapters)-gap-self.padding for _ in config.chapters]
            if config.style == 'S2':
                available = [(ch.end-ch.start)/config.duration*(self.x1-self.x0)-gap-self.padding for ch in config.chapters]
            self.chapter_grid = any(self.text_width(ch.title,self.font_size)+self.unit > space
                                    for ch,space in zip(config.chapters,available))
            if self.chapter_grid:
                widest = max(self.text_width(ch.title,self.font_size) for ch in config.chapters)+self.unit
                self.grid_columns = next((n for n in range(min(4,len(config.chapters)),0,-1)
                    if widest <= (self.x1-self.x0-gap*(n-1))/n-self.padding*2), 0)
                if not self.grid_columns:
                    raise ConfigError('完整章名超过整行宽度，请使用准确简称；不能截成单字省略号。')
                self.grid_rows = math.ceil(len(config.chapters)/self.grid_columns)
                self.ground_y = self.char_h + max(12,16*self.unit)
                self.grid_top = self.ground_y + 30*self.unit
                self.grid_pitch = (100 if config.style=='S1' else 120)*self.unit
                required = math.ceil(self.grid_top+self.grid_rows*self.grid_pitch+self.padding)
                config.height = max(config.height, required)
                if config.height > 4320 or config.width*config.height > MAX_PIXELS:
                    raise ConfigError('完整章节区超出安全画布，请缩短章名或分组，不缩小字号。')
                if self.scale == 2 and config.width*config.height > 2_500_000:
                    self.scale = 1
                    self.assets = []
                    self.char_width = self.char_left = self.char_right = 0
                    self._load_assets()
        if self.readable and (config.height>4320 or config.width*config.height>MAX_PIXELS):
            raise ConfigError('章节或角色超出安全画布，请调整版式或角色尺寸，不自动裁切。')
        if not self.chapter_grid and config.style in ("S1", "S2", "S3", "S7") and (self.x1 - self.x0) / len(config.chapters) < self.font_size * 2.7:
            raise ConfigError("chapter labels would be unreadably narrow; shorten/merge chapters or use S5/S6")
        if self.editorial_nav:
            available = (self.x1-self.x0) / len(config.chapters)
            for i, chapter in enumerate(config.chapters):
                required = (self.text_width(chapter.title, self.font_size) + self.unit
                            + self.text_width(f"{i+1:02}", self.small_size*.9) + 42*self.unit)
                if required > available:
                    raise ConfigError("chapter navigation title is too long; use an accurate shorter label or another layout")
        if config.style == "S2" and not self.chapter_grid:
            for c in config.chapters:
                available = (c.end - c.start) / config.duration * (self.x1 - self.x0)
                if available < self.font_size * 2.7 + self.padding:
                    raise ConfigError("a timed S2 segment is too narrow for a readable label; merge chapters or use S5/S6")
        if config.style == "S4":
            for c in config.chapters:
                available = (c.end - c.start) / config.duration * (self.x1 - self.x0)
                if available < (self.font_size * 2.7 + self.padding) * (2 if self.assets else 1) + self.char_width:
                    raise ConfigError("a timed S4 segment is too narrow for its label/character; merge chapters or use S5/S6")
        self.content_height = config.height
        self.demo_band = math.ceil(self.small_size + 18*self.unit) if config.demo_label else 0
        if self.demo_band and (config.height+self.demo_band)%2:
            self.demo_band+=1  # Synthetic MP4 previews need even height; do not resize artwork.
        config.height += self.demo_band
        if config.height>4320 or config.width*config.height>MAX_PIXELS:
            raise ConfigError('Synthetic label band exceeds safe canvas budget')

    def _load_assets(self):
        character = self.config.character
        if character["mode"] == "none":
            return
        raw_frames = []
        originals = []
        for i, path in enumerate(character["resolved_frames"]):
            try:
                with Image.open(path) as raw:
                    if raw.format != "PNG" or raw.mode != "RGBA":
                        raise ConfigError("approved character frames must be RGBA PNG files")
                    if raw.width * raw.height > MAX_PIXELS:
                        raise ConfigError("character image exceeds safe pixel budget")
                    rgba = raw.copy()
            except (OSError, Image.DecompressionBombError) as exc:
                raise ConfigError(f"Cannot load approved character frame: {path}") from exc
            alpha = rgba.getchannel("A")
            lo, hi = alpha.getextrema()
            bbox = visible_bounds(rgba)
            if bbox is None or lo != 0 or hi != 255:
                raise ConfigError("character frame needs both fully transparent and opaque pixels")
            contacts = character.get("contacts")
            if contacts:
                cx, cy = contacts[i]
                visible_contact(rgba, (cx, cy))
                # Preserve the approved legacy crop when explicit foot anchors are used.
                if 'bodyPivotX' not in character:
                    bbox = alpha.getbbox()
            else:
                cx, cy = default_contact(rgba)
            if 'bodyPivotX' in character:
                cx = character['bodyPivotX']
                if not 0 <= cx < rgba.width:
                    raise ConfigError('bodyPivotX must be inside the source canvas')
            originals.append(rgba)
            # Keep nearby antialiasing; distant near-invisible specks do not set scale/ground.
            if not contacts or 'bodyPivotX' in character:
                bbox = (max(0,bbox[0]-2),max(0,bbox[1]-2),min(rgba.width,bbox[2]+2),min(rgba.height,bbox[3]+2))
            cropped = rgba.crop(bbox)
            raw_frames.append((cropped, (cx - bbox[0], cy - bbox[1])))
        if character['mode'] == 'walk-cycle':
            validate_frames(originals)
        # One shared scale preserves proportions and cycle consistency; never stretch, flip or recolor.
        factor = self.char_h / max(frame.height for frame, _ in raw_frames)
        planned = []
        for frame, (cx, cy) in raw_frames:
            size = (max(1, round(frame.width * factor * self.scale)), max(1, round(frame.height * factor * self.scale)))
            # Validate projected allocation before Pillow allocates it. A nearly-flat PNG can
            # otherwise turn a modest approved height into a multi-gigabyte resampled image.
            if size[0] > self.config.width * .25 * self.scale:
                raise ConfigError("approved character is too wide at the requested height; choose a smaller height")
            if size[0] * size[1] > MAX_PIXELS:
                raise ConfigError("resized character exceeds the safe pixel budget")
            planned.append((frame, cx, cy, size))
        for frame, cx, cy, size in planned:
            self.assets.append((frame.resize(size, Image.Resampling.LANCZOS), (cx * factor, cy * factor)))
            self.char_width = max(self.char_width, size[0] / self.scale)
            self.char_left = max(self.char_left, cx * factor)
            self.char_right = max(self.char_right, size[0] / self.scale - cx * factor)
        if self.char_width > self.config.width * .25:
            raise ConfigError("approved character is too wide; choose a smaller height")

    def _coords(self, box):
        return tuple(round(v * self.scale) for v in box)

    def rounded(self, draw, box, fill, radius=12, outline=None, width=1):
        draw.rounded_rectangle(self._coords(box), radius=round(radius * self.scale), fill=fill,
                               outline=outline, width=max(1, round(width * self.scale)))

    def line(self, draw, coords, fill, width=1):
        draw.line(self._coords(coords), fill=fill, width=max(1, round(width * self.scale)))

    def text_width(self, text, size):
        f = font_at(str(self.font_path_for(size)), round(size * self.scale))
        return f.getlength(text) / self.scale

    def font_path_for(self, size):
        return self.config.font_bold_path if self.refined and self.config.font_bold_path and size >= self.font_size * .9 else self.config.font_path

    def ellipsis(self, text, max_width, size):
        if self.text_width(text, size) <= max_width:
            return text
        end = "…"
        if self.text_width(end, size) > max_width:
            return ""
        while text and self.text_width(text + end, size) > max_width:
            text = text[:-1]
        return text + end

    def fit_lines(self, text, max_width, size, max_lines=2):
        if max_width < self.text_width("…", size):
            raise ConfigError("label has no readable space; increase the canvas or choose S5/S6")
        lines, remainder = [], text
        while remainder and len(lines) < max_lines:
            if len(lines) == max_lines - 1:
                lines.append(self.ellipsis(remainder, max_width, size))
                break
            i = 0
            while i < len(remainder) and self.text_width(remainder[:i + 1], size) <= max_width:
                i += 1
            if i == len(remainder):
                lines.append(remainder)
                break
            # Prefer a word boundary for Latin labels without breaking CJK character wrapping.
            cut = remainder.rfind(" ", 0, i + 1)
            if cut > i // 2:
                i = cut
            lines.append(remainder[:i].rstrip())
            remainder = remainder[i:].lstrip()
        return lines

    def text(self, draw, text, x, y, size, fill, anchor="mm"):
        draw.text((round(x * self.scale), round(y * self.scale)), text,
                  font=font_at(str(self.font_path_for(size)), round(size * self.scale)), fill=fill, anchor=anchor)

    def label(self, draw, title, box, fill, lines=2, align="center", size=None):
        x0, y0, x1, y1 = box
        size = size or self.font_size
        if self.readable and self.text_width(title,size) > x1-x0+1e-6:
            raise ConfigError('完整章名放不下，请使用准确简称或新版多行章节布局，不能省略标题信息。')
        fitted = self.fit_lines(title, max(0, x1 - x0), size, lines)
        line_h = size * 1.3
        for i, item in enumerate(fitted):
            cy = (y0 + y1) / 2 + (i - (len(fitted) - 1) / 2) * line_h
            self.text(draw, item, (x0 + x1) / 2 if align == "center" else x0,
                      cy, size, fill, "mm" if align == "center" else "lm")

    def _track(self, draw, state, y=None, segmented=False):
        p = self.palette
        y = self.ground_y if y is None else y
        edge = self.x0 + state.progress * (self.x1 - self.x0)
        if segmented:
            count = max(12, round((self.x1 - self.x0) / max(16, 26 * self.unit)))
            slot = (self.x1 - self.x0) / count
            gap = max(2, slot * .24)
            for i in range(count):
                a, b = self.x0 + i * slot, self.x0 + (i + 1) * slot - gap
                self.rounded(draw, (a, y, b, y + self.track_h), p["inactive"], 2)
                if edge > a:
                    self.rounded(draw, (a, y, min(b, edge), y + self.track_h), p["active"], 2)
        else:
            self.rounded(draw, (self.x0, y, self.x1, y + self.track_h), p["inactive"], self.track_h / 2)
            if edge > self.x0:
                self.rounded(draw, (self.x0, y, edge, y + self.track_h), p["active"], self.track_h / 2)
        return edge

    def _card(self, draw, box, radius=18):
        p = self.palette
        x0, y0, x1, y1 = box
        if p["shadow"][3]:
            self.rounded(draw, (x0, y0 + 4 * self.unit, x1, y1 + 4 * self.unit), p["shadow"], radius)
        self.rounded(draw, box, p["surface"], radius, p["outline"])

    def navigation_items(self, state):
        """A fixed chapter map; the endpoint has no chapter still 'in progress'."""
        slot = (self.x1 - self.x0) / len(self.config.chapters)
        return [{"title": chapter.title, "ordinal": f"{i + 1:02d}",
                 "status": "completed" if state.time >= self.config.duration or i < state.chapter
                 else "current" if i == state.chapter else "upcoming",
                 "left": self.x0 + i * slot, "right": self.x0 + (i + 1) * slot}
                for i, chapter in enumerate(self.config.chapters)]

    def _editorial_navigation(self, draw, state):
        """One continuous progress rail, small ordinal, unboxed readable titles."""
        p = self.palette
        edge = self._track(draw, state)
        y = self.ground_y + 54 * self.unit
        for item in self.navigation_items(state):
            left, right = item["left"], item["right"]
            current = item["status"] == "current"
            ink = p["text"] if current else p["accent-text"] if item["status"] == "completed" else p["muted-text"]
            number_size = self.small_size * .9
            number_w = self.text_width(item["ordinal"], number_size)
            # One-pixel slack avoids accidental ellipsis from floating-point subtraction.
            title_w = min(self.text_width(item["title"], self.font_size) + self.unit,
                          right - left - number_w - 42 * self.unit)
            start = (left + right - number_w - 14 * self.unit - title_w) / 2
            if current:
                self.rounded(draw, (start - 7*self.unit, y - 18*self.unit,
                                    start + number_w + 7*self.unit, y + 18*self.unit),
                             p["active"], 4*self.unit)
            self.text(draw, item["ordinal"], start, y, number_size,
                      p["active-text"] if current else p["muted-text"], "lm")
            title_left = start + number_w + 14*self.unit
            self.label(draw, item["title"], (title_left, y-self.font_size,
                       title_left+title_w, y+self.font_size), ink, lines=1, align="left")
            if left > self.x0:
                self.line(draw, (left, self.ground_y-3*self.unit, left,
                                self.ground_y+self.track_h+3*self.unit), p["surface"], 2*self.unit)
        if not self.assets:
            radius = 5*self.unit
            self.rounded(draw, (edge-radius, self.ground_y-radius+self.track_h/2,
                               edge+radius, self.ground_y+radius+self.track_h/2),
                         p["text"], radius)

    def _draw_chapter_grid(self, draw, state):
        p, c = self.palette, self.config
        gap = max(8,14*self.unit)
        cell = (self.x1-self.x0-gap*(self.grid_columns-1))/self.grid_columns
        for i, chapter in enumerate(c.chapters):
            row,col = divmod(i,self.grid_columns)
            left = self.x0+col*(cell+gap)
            top = self.grid_top+row*self.grid_pitch
            done = state.time>=c.duration or i<state.chapter
            current = i==state.chapter and state.time<c.duration
            color = p['active-text'] if current and c.style=='S1' else p['text'] if current or done else p['muted-text']
            if c.style=='S1':
                self.rounded(draw,(left,top,left+cell,top+self.row_h),p['active'] if current else p['inactive'] if done else p['surface'],self.row_h/2,p['outline'])
                box = (left+self.padding,top,left+cell-self.padding,top+self.row_h)
            else:
                if current:
                    cx=left+cell/2;numw=self.text_width(f'{i+1:02}',self.small_size*.86)
                    self.rounded(draw,(cx-numw/2-6*self.unit,top+2*self.unit,cx+numw/2+6*self.unit,top+34*self.unit),p['active'],4*self.unit)
                self.text(draw,f'{i+1:02}',left+cell/2,top+18*self.unit,self.small_size*.86,p['muted-text'])
                box = (left+self.padding,top+38*self.unit,left+cell-self.padding,top+104*self.unit)
            self.label(draw,chapter.title,box,color,lines=1)
            self.grid_bounds.append({'title':chapter.title,'box':box,'status':'current' if current else 'completed' if done else 'upcoming'})

    def frame(self, time):
        c, p = self.config, self.palette
        state = c.state(time)
        out = Image.new("RGBA", (c.width * self.scale, self.content_height * self.scale), (0, 0, 0, 0))
        draw = ImageDraw.Draw(out)
        self.grid_bounds = []
        if c.style in ("S1", "S2", "S3"):
            slot = (self.x1 - self.x0) / len(c.chapters)
            gap = max(8, 14 * self.unit)
            if c.style == "S1":
                self._track(draw, state)
            elif c.style == "S2":
                # One quiet runway segment per chapter, not a row of decorative ticks.
                edge = self.x0 + state.progress * (self.x1 - self.x0)
                for chapter in c.chapters:
                    a = self.x0 + chapter.start / c.duration * (self.x1 - self.x0)
                    b = self.x0 + chapter.end / c.duration * (self.x1 - self.x0)
                    a, b = a + gap / 5, b - gap / 5
                    h = max(7, (14 if self.refined else 10) * self.unit)
                    self.rounded(draw, (a, self.ground_y, b, self.ground_y + h), p["inactive"], h / 2)
                    if edge > a:
                        self.rounded(draw, (a, self.ground_y, min(b, edge), self.ground_y + h), p["active"], h / 2)
            elif self.assets:
                self._track(draw, state)
            if self.chapter_grid:
                self._draw_chapter_grid(draw,state)
            for i, chapter in enumerate([] if self.chapter_grid else c.chapters):
                x0, x1 = self.x0 + i * slot + gap / 2, self.x0 + (i + 1) * slot - gap / 2
                if c.style == "S2":
                    x0 = self.x0 + chapter.start / c.duration * (self.x1 - self.x0) + gap / 2
                    x1 = self.x0 + chapter.end / c.duration * (self.x1 - self.x0) - gap / 2
                y0, y1 = self.body_y, self.bottom
                active = i == state.chapter and not (self.readable and state.time >= c.duration)
                fill = p["accent-text"] if active else p["muted-text"]
                if c.style == "S1":
                    # Preserve the capsule form, but remove stacked outlines and tall panels.
                    title_w = x1 - x0 if self.refined else min(x1 - x0, max(self.font_size * 3.2, self.text_width(chapter.title, self.font_size) + self.padding))
                    mid = (x0 + x1) / 2
                    background = p["active"] if active else p["inactive"] if self.refined and (i < state.chapter or self.readable and state.time>=c.duration) else p["surface"]
                    self.rounded(draw, (mid - title_w / 2, y0, mid + title_w / 2, y1), background, self.row_h / 2, p["outline"] if self.refined else None)
                    fill = p["active-text"] if active else p["text"]
                elif c.style == "S2" and self.refined:
                    # The timed runway stays distinct from the minimal short-underline style.
                    fill = p["text"] if i <= state.chapter else p["muted-text"]
                    self.text(draw, f"{i+1:02}", (x0+x1)/2, y0+self.row_h*.13, self.small_size*.86, p["muted-text"])
                    self.label(draw, chapter.title, (x0+self.padding/2,y0+self.row_h*.35,x1-self.padding/2,y1), fill, lines=1)
                    continue
                elif c.style == "S3":
                    # Text-only chapter navigation: no pill/card background, ever.
                    if i < len(c.chapters) - 1:
                        sx = self.x0 + (i + 1) * slot
                        self.line(draw, (sx, y0 + self.row_h * .34, sx, y0 + self.row_h * .66), p["outline"], 1)
                    if active:
                        mark_w = min(48 * self.unit, (x1 - x0) * .2)
                        mark_w = max(18, mark_w)
                        mx, my = (x0 + x1) / 2, y1 - max(2, 3 * self.unit)
                        self.line(draw, (mx - mark_w / 2, my, mx + mark_w / 2, my), p["progress-inactive"], 2)
                        if state.chapter_progress > 0:
                            self.line(draw, (mx - mark_w / 2, my, mx - mark_w / 2 + mark_w * state.chapter_progress, my), p["progress"], 2)
                self.label(draw, chapter.title, (x0 + self.padding / 2, y0, x1 - self.padding / 2, y1 - (8 * self.unit if c.style == "S3" else 0)), fill, lines=1)
        elif c.style == "S4":
            # One continuous slim band. Fill is elapsed time, never a large active pill.
            edge = self.x0 + state.progress * (self.x1 - self.x0)
            self.rounded(draw, (self.x0, self.body_y, self.x1, self.bottom), p["surface"], 3)
            if edge > self.x0:
                self.rounded(draw, (self.x0, self.body_y, edge, self.bottom), p["active"], 3)
            for i, chapter in enumerate(c.chapters):
                x0 = self.x0 + chapter.start / c.duration * (self.x1 - self.x0)
                x1 = self.x0 + chapter.end / c.duration * (self.x1 - self.x0)
                if i:
                    self.line(draw, (x0, self.body_y + 1, x0, self.bottom - 1), p["surface"], 2)
                tx0, tx1 = x0 + self.padding, x1 - self.padding
                if self.assets:
                    left, right = edge - self.char_left - self.padding / 2, edge + self.char_right + self.padding / 2
                    if right > tx0 and left < tx1:
                        if left - tx0 > tx1 - right:
                            tx1 = min(tx1, left)
                        else:
                            tx0 = max(tx0, right)
                # Two clipped copies preserve legibility on both sides of a moving fill.
                for filled, ink in ((False, p["text"]), (True, p["active-text"])):
                    layer = Image.new("RGBA", out.size)
                    layer_draw = ImageDraw.Draw(layer)
                    self.label(layer_draw, chapter.title, (tx0, self.body_y, tx1, self.bottom), ink, lines=1)
                    split = round(edge * self.scale)
                    if filled:
                        layer.paste((0, 0, 0, 0), (split, 0, layer.width, layer.height))
                    else:
                        layer.paste((0, 0, 0, 0), (0, 0, split, layer.height))
                    out.alpha_composite(layer)
            if self.assets:
                self._track(draw, state, self.ground_y)
        elif c.style == "S5":
            panel_w = min(self.x1 - self.x0, max(390 * self.unit, (self.x1 - self.x0) * .52))
            x1 = self.x0 + panel_w
            self._card(draw, (self.x0, self.body_y, x1, self.bottom), 12)
            pad = self.padding
            number_w = max(54 * self.unit, self.font_size * 2.2)
            self.text(draw, f"{state.chapter + 1:02d}", self.x0 + pad + number_w / 2,
                      (self.body_y + self.bottom) / 2 - 3 * self.unit, self.font_size, p["accent-text"])
            self.line(draw, (self.x0 + pad + number_w + pad / 3, self.body_y + self.body_h * .28,
                             self.x0 + pad + number_w + pad / 3, self.body_y + self.body_h * .65), p["outline"])
            self.label(draw, c.chapters[state.chapter].title,
                       (self.x0 + number_w + pad * 2, self.body_y, x1 - pad, self.bottom - 6 * self.unit), p["text"], lines=1, align="left")
            y = self.bottom - 5 * self.unit
            self.rounded(draw, (self.x0 + pad, y, x1 - pad, y + 3 * self.unit), p["inactive"], 2)
            if state.progress:
                self.rounded(draw, (self.x0 + pad, y, self.x0 + pad + (panel_w - 2 * pad) * state.progress, y + 3 * self.unit), p["active"], 2)
            if self.assets:
                self._track(draw, state)
        elif c.style == "S6":
            panel_w = min(self.x1 - self.x0, max(430 * self.unit, (self.x1 - self.x0) * .52))
            self._card(draw, (self.x0, self.body_y, self.x0 + panel_w, self.bottom), 14)
            radius = self.body_h * .29
            cx, cy = self.x0 + self.body_h * .55, (self.body_y + self.bottom) / 2
            box = self._coords((cx - radius, cy - radius, cx + radius, cy + radius))
            stroke = max(3, round(self.body_h * .04 * self.scale))
            draw.ellipse(box, outline=p["inactive"], width=stroke)
            if state.progress:
                draw.arc(box, -90, -90 + state.progress * 360, fill=p["active"], width=stroke)
            self.text(draw, f"{state.chapter + 1:02d}", cx, cy, self.font_size * .72, p["text"])
            tx0, tx1 = self.x0 + self.body_h * 1.1, self.x0 + panel_w - self.padding
            self.label(draw, c.chapters[state.chapter].title, (tx0, cy - self.font_size * .9, tx1, cy + self.font_size * .15), p["text"], lines=1, align="left")
            self.text(draw, f"{state.chapter + 1} / {len(c.chapters)}  CHAPTER", tx0, cy + self.font_size * .8, self.small_size * .8, p["muted-text"], "lm")
            if self.assets:
                self._track(draw, state)
        elif self.editorial_nav:
            self._editorial_navigation(draw, state)
        else:  # Historical S7 hanging tabs remain byte-compatible.
            slot = (self.x1 - self.x0) / len(c.chapters)
            gap = max(10, 20 * self.unit)
            if self.refined:
                self._track(draw,state)
            for i, chapter in enumerate(c.chapters):
                x0, x1 = self.x0 + i * slot + gap / 2, self.x0 + (i + 1) * slot - gap / 2
                active = i == state.chapter
                tab_bottom = self.tab_h + (self.tab_extra if active else 0)
                # Draw above the canvas to keep top corners square at the attachment edge.
                fill = p["active"] if active else p["inactive"] if i < state.chapter else p["surface"]
                ink = p["active-text"] if active else p["text"]
                if self.refined:
                    # Compact content-width tag, visibly attached to the ONE progress rail.
                    mx = (x0+x1)/2
                    top = self.ground_y + 20*self.unit
                    bottom = top + 104*self.unit
                    tag_width = min(x1-x0,self.text_width(chapter.title,self.font_size)+44*self.unit)
                    self.line(draw,(mx,self.ground_y+self.track_h,mx,top),p["text"] if active else p["outline"],1)
                    self.rounded(draw,(mx-3*self.unit,self.ground_y-1*self.unit,mx+3*self.unit,self.ground_y+5*self.unit),p["active"] if i<=state.chapter else p["outline"],3*self.unit)
                    if active:
                        self.rounded(draw,(mx-tag_width/2,top,mx+tag_width/2,bottom),p["active"],6*self.unit)
                    self.text(draw,f"{i+1:02}",mx,top+20*self.unit,self.small_size*.82,ink if active else p["muted-text"])
                    self.label(draw,chapter.title,(x0+self.padding/2,top+48*self.unit,x1-self.padding/2,bottom-12*self.unit),ink if active else p["text"] if i<state.chapter else p["muted-text"],lines=1)
                    continue
                self.rounded(draw, (x0, -self.tab_h, x1, tab_bottom), fill, min(14 * self.unit, (x1 - x0) / 6))
                has_subtitle = bool(chapter.subtitle)
                self.text(draw, f"{i + 1:02d}", (x0 + x1) / 2, tab_bottom * .23,
                          self.small_size * .82, ink if active else p["muted-text"])
                title_y = tab_bottom * (.53 if has_subtitle else .61)
                size = self.font_size * (1.05 if active else .94)
                self.label(draw, chapter.title, (x0 + self.padding / 2, title_y - size, x1 - self.padding / 2, title_y + size),
                           ink, lines=1, size=size)
                if has_subtitle:
                    self.label(draw, chapter.subtitle, (x0 + self.padding / 2, tab_bottom * .73, x1 - self.padding / 2, tab_bottom * .94),
                               ink if active else p["muted-text"], lines=1, size=self.small_size * .82)
                if active:
                    mw = (x1 - x0) * .40
                    mx = (x0 + x1) / 2
                    self.line(draw, (mx - mw / 2, tab_bottom - 3 * self.unit, mx - mw / 2 + mw * state.chapter_progress, tab_bottom - 3 * self.unit), ink, 2)
            if self.assets and not self.refined:
                self._track(draw, state)
        if self.assets:
            frame_index = 0 if c.character["mode"] == "single-pose" else int(state.time * c.character["cadence"] + 1e-9) % len(self.assets)
            asset, (cx, cy) = self.assets[frame_index]
            anchor_x = self.x0 + state.progress * (self.x1 - self.x0)
            # Contact-foot coordinate, not the padded image box, binds to the time edge.
            px, py = round((anchor_x - cx) * self.scale), round((self.ground_y - cy) * self.scale)
            if px < 0 or py < 0 or px + asset.width > out.width or py + asset.height > out.height:
                raise ConfigError("character would be clipped; adjust approved height or canvas")
            out.alpha_composite(asset, (px, py))
        if c.demo_label:
            labeled = Image.new('RGBA',(c.width*self.scale,c.height*self.scale))
            labeled.alpha_composite(out,(0,self.demo_band*self.scale))
            self.text(ImageDraw.Draw(labeled), "合成示意 / SAMPLE", self.x0, self.demo_band/2, self.small_size, p["text"], "lm")
            out=labeled
        if self.scale != 1:
            out = out.resize((c.width, c.height), Image.Resampling.LANCZOS)
        return out


def demo_config(style="S1"):
    return {"schemaVersion": 1, "duration": 10, "fps": 24, "width": 1280, "height": 320,
            "style": style, "palette": dict(DEMO_PALETTE), "character": {"mode": "none"},
            "demoLabel": True, "chapters": [{"start": 0, "end": 3, "title": "找到问题"},
                                           {"start": 3, "end": 7, "title": "动手实践"},
                                           {"start": 7, "end": 10, "title": "带走要点"}]}


def save_image(image, destination):
    destination = Path(destination)
    if destination.exists():
        raise ConfigError(f"Refusing to overwrite: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG")


def contact_sheet(config, time=4.5):
    # Catalog backgrounds are presentation-only. frame() always returns transparent RGBA.
    card_w, card_h = 980, 240
    margin, header, gutter = 32, 126, 22
    sheet = Image.new("RGB", (margin * 2 + card_w * 2 + gutter, header + math.ceil(len(STYLE_NAMES) / 2) * (card_h + gutter) + margin), "#F5F1EA")
    draw = ImageDraw.Draw(sheet)
    font_path = str(config.font_path)
    title_font = font_at(font_path, 37)
    small_font = font_at(font_path, 20)
    draw.text((margin, 24), "七种形式，一条真实时间线", font=title_font, fill="#26312A")
    draw.text((margin, 78), "4 款常用 + 3 款可选  ·  同一配色、同一章节、同一时间  ·  合成示意", font=small_font, fill="#586458")
    for index, (style, (_, chinese, english)) in enumerate(STYLE_NAMES.items()):
        col, row = index % 2, index // 2
        x, y = margin + col * (card_w + gutter), header + row * (card_h + gutter)
        draw.line((x, y + card_h, x + card_w, y + card_h), fill="#DDD4C9", width=1)
        draw.text((x + 24, y + 20), f"{style}  {chinese}", font=font_at(font_path, 28), fill="#26312A")
        tag = "常用" if index < 4 else "可选"
        draw.text((x + card_w - 78, y + 25), tag, font=small_font, fill="#586458")
        draw.text((x + 24, y + 61), english, font=small_font, fill="#798273")
        local = copy.deepcopy(config)
        local.style = style
        local.demo_label = False
        frame = Renderer(local).frame(time)
        # Trim only transparent catalog whitespace, never alter the actual exported canvas.
        frame = frame.crop(frame.getbbox())
        factor = min((card_w - 36) / config.width, (card_h - 98) / frame.height)
        frame = frame.resize((max(1, round(frame.width * factor)), max(1, round(frame.height * factor))), Image.Resampling.LANCZOS)
        sheet.paste(frame, (x + (card_w - frame.width) // 2, y + 90 + (card_h - 98 - frame.height) // 2), frame)
    return sheet


class CatalogRenderer:
    """Presentation-only animation of the seven actual RGBA renderers."""
    def __init__(self, config):
        self.source = config
        self.config = copy.deepcopy(config)
        size = contact_sheet(config, 0).size
        self.config.width, self.config.height = size
        self.config.style = "S1–S7 catalog"

    def frame(self, time):
        return contact_sheet(self.source, time).convert("RGBA")


def ensure_new_output(path):
    path = Path(path)
    if path.exists():
        raise ConfigError(f"Refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def export_video(renderer, path, start, duration, kind="mov", neutral="#EEF0E9"):
    c = renderer.config
    path = ensure_new_output(path)
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise ConfigError("ffmpeg and ffprobe must both be installed in the selected task environment")
    if kind == "mp4" and (c.width % 2 or c.height % 2):
        raise ConfigError("MP4 sample dimensions must both be even")
    frames = max(1, math.ceil(duration * c.fps - 1e-9))
    # Stream frames; never write a huge PNG sequence or hold the animation in RAM.
    handle, temp_name = tempfile.mkstemp(prefix=".progress-render-", suffix=path.suffix, dir=path.parent)
    os.close(handle)
    temp = Path(temp_name)
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgba",
               "-video_size", f"{c.width}x{c.height}", "-framerate", f"{c.fps:.12g}", "-i", "pipe:0", "-an"]
    if kind == "mov":
        command += ["-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-alpha_bits", "16", "-threads", "2"]
    else:
        command += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "veryfast", "-movflags", "+faststart", "-threads", "2"]
    command += ["-frames:v", str(frames), str(temp)]
    try:
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors)
            try:
                for i in range(frames):
                    time = min(c.duration, start + i / c.fps)
                    image = renderer.frame(time)
                    if kind == "mp4":
                        bg = Image.new("RGBA", image.size, neutral)
                        bg.alpha_composite(image)
                        image = bg
                    process.stdin.write(image.tobytes())
                process.stdin.close()
                returncode = process.wait(timeout=120)
            except BaseException:
                process.kill()
                process.wait()
                errors.seek(0)
                detail = errors.read().decode("utf-8", "replace")[-2000:]
                if detail:
                    print(detail, file=sys.stderr)
                raise
            if returncode:
                errors.seek(0)
                raise ConfigError("ffmpeg encode failed: " + errors.read().decode("utf-8", "replace")[-2000:])
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams", "-show_format", "-of", "json", str(temp)],
                               check=True, capture_output=True, text=True)
        metadata = json.loads(probe.stdout)
        stream = metadata["streams"][0]
        if kind == "mov" and (stream.get("codec_name") != "prores" or "4444" not in stream.get("profile", "") or not stream.get("pix_fmt", "").startswith("yuva")):
            raise ConfigError("encoded MOV did not retain expected ProRes 4444 alpha metadata")
        # os.link is atomic and refuses a destination that appeared during encoding.
        os.link(temp, path)
        temp.unlink()
        digest = hashlib.sha256()
        with path.open("rb") as encoded:
            for chunk in iter(lambda: encoded.read(1024 * 1024), b""):
                digest.update(chunk)
        return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest.hexdigest(),
                "sampleStart": start, "requestedDuration": duration, "encodedDuration": frames / c.fps,
                "frameCount": frames, "codec": stream.get("codec_name"), "profile": stream.get("profile"),
                "pixelFormat": stream.get("pix_fmt"), "width": stream.get("width"), "height": stream.get("height"),
                "fps": stream.get("r_frame_rate"), "characterMode": c.character["mode"], "style": c.style,
                "editorImport": "unverified", "alphaScan": "not_run_use_verify_alpha_mov.sh" if kind == "mov" else "not_applicable_opaque_demo"}
    finally:
        temp.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo-config", help="write a labeled, synthetic ten-second example config")
    demo.add_argument("output")
    demo.add_argument("--style", choices=list(STYLE_NAMES), default="S1")
    for name in ("validate", "preview", "contact-sheet", "mov", "demo-video"):
        command = sub.add_parser(name)
        command.add_argument("config")
        if name != "validate":
            command.add_argument("output")
        if name in ("preview", "contact-sheet"):
            command.add_argument("--time", type=float, default=0)
        if name == "demo-video":
            command.add_argument("--all-styles", action="store_true", help="animate a seven-style presentation board")
        if name in ("mov", "demo-video"):
            command.add_argument("--purpose", choices=("sample", "debug", "final"), required=True)
            command.add_argument("--start", type=float, default=0)
            command.add_argument("--seconds", type=float)
            command.add_argument("--final-approved", action="store_true", help="caller attests actual Step 8 permission was verified; never inferred")
    args = parser.parse_args(argv)
    try:
        if args.command == "demo-config":
            path = ensure_new_output(args.output)
            path.write_text(json.dumps(demo_config(args.style), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"config": str(path.resolve()), "syntheticDemo": True}))
            return 0
        config = load_config(args.config)
        renderer = Renderer(config)
        if args.command == "validate":
            # Render all transition edges as a bounded layout check, not animation or approval.
            for t in sorted({0., config.duration, *(c.start for c in config.chapters), *(max(0., c.end - 1 / config.fps) for c in config.chapters)}):
                renderer.frame(t)
            print(json.dumps({"valid": True, "style": config.style, "chapters": len(config.chapters), "characterMode": config.character["mode"], "font": str(config.font_path)}))
        elif args.command == "preview":
            save_image(renderer.frame(args.time), args.output)
            print(json.dumps({"preview": str(Path(args.output).resolve()), "mode": "RGBA", "time": config.state(args.time).time}))
        elif args.command == "contact-sheet":
            save_image(contact_sheet(config, args.time), args.output)
            print(json.dumps({"contactSheet": str(Path(args.output).resolve()), "coreStyles": 4, "optionalStyles": 3}))
        else:
            if args.command == "mov" and Path(args.output).suffix.lower() != ".mov":
                raise ConfigError("transparent output must use .mov")
            if args.command == "demo-video" and Path(args.output).suffix.lower() != ".mp4":
                raise ConfigError("opaque sample comparison must use .mp4")
            if args.command == "demo-video" and (args.purpose == "final" or not config.demo_label):
                raise ConfigError("MP4 is only for labeled synthetic demonstrations; final delivery is transparent MOV")
            start = finite_number(args.start, "start", 0, config.duration)
            if start >= config.duration:
                raise ConfigError("start must be before duration")
            if args.purpose == "final":
                if not args.final_approved:
                    raise ConfigError("full export requires --final-approved after the orchestrator verifies actual Step 8 user permission")
                if start != 0 or args.seconds is not None:
                    raise ConfigError("final export must cover the complete timeline")
                if config.demo_label:
                    raise ConfigError("synthetic labeled demo config cannot be exported as a user final")
                duration = config.duration
            else:
                duration = finite_number(args.seconds if args.seconds is not None else min(15, config.duration - start), "seconds", .01, 30 if args.purpose == "debug" else 15)
                if start + duration > config.duration + 1e-9:
                    raise ConfigError("sample ends after the timeline")
                if args.final_approved:
                    raise ConfigError("--final-approved is only valid with --purpose final")
            if args.command == "demo-video" and args.all_styles:
                renderer = CatalogRenderer(config)
            report = export_video(renderer, args.output, start, duration, "mov" if args.command == "mov" else "mp4")
            report.update({"purpose": args.purpose, "syntheticDemo": config.demo_label})
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (ConfigError, OSError, subprocess.SubprocessError, BrokenPipeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
