#!/usr/bin/env python3
"""Source-qualified style selection and conservative config migration.

The original renderers keep their own schemas and geometry. This module never
imports a private profile, copies character assets, or infers project approval.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace
from fractions import Fraction
from selected_styles import selected_styles, selected_style, check_new_chapters

import render_progress as classic
from compat_gallery.render_overlay import Overlay, DEFAULT, STYLE_ALIASES, STYLES

INSTALLED_ORIGIN = "installed-20260922"
CLASSIC_ORIGIN = "classic-0.5"
REGISTRY = {}
for code, (_, name, _) in classic.STYLE_NAMES.items():
    REGISTRY[f"classic:{code}"] = {"engine": "classic", "nativeStyle": code, "name": name}
for code, native in STYLE_ALIASES.items():
    REGISTRY[f"gallery:{code}"] = {"engine": "gallery", "nativeStyle": native, "name": STYLES[native]}
for native in ("S1", "S2", "S3", "S5", "S6", "S7", "S8", "S9"):
    REGISTRY[f"legacy:{native}"] = {"engine": "gallery", "nativeStyle": native, "name": STYLES[native]}

GALLERY_FIELDS = {"style", "outputWidth", "displayWidth", "fontRegular", "fontBold",
                  "labelSize", "kickerSize", "progressMode", "character", "palette", "visualRevision"}


def resolve_style(value, origin=None):
    if not isinstance(value, str):
        raise classic.ConfigError("style must be a string")
    if value in REGISTRY:
        if origin is not None:
            expected = {INSTALLED_ORIGIN: "gallery", CLASSIC_ORIGIN: "classic"}.get(origin)
            if expected != REGISTRY[value]["engine"]:
                raise classic.ConfigError("style namespace conflicts with origin")
        return value
    if ":" in value:
        raise classic.ConfigError("unknown stable style key: " + value)
    if origin == INSTALLED_ORIGIN:
        normalized = value.zfill(2) if value.isdigit() else value
        if normalized in STYLE_ALIASES:
            return "gallery:" + normalized
        for code, native in STYLE_ALIASES.items():
            if value == native and value.startswith("R"):
                return "gallery:" + code
        if "legacy:" + value in REGISTRY:
            return "legacy:" + value
        raise classic.ConfigError("installed style is not implemented; legacy S4 cannot be remapped")
    if origin == CLASSIC_ORIGIN:
        normalized = {v[0]: k for k, v in classic.STYLE_NAMES.items()}.get(value, value)
        if "classic:" + normalized in REGISTRY:
            return "classic:" + normalized
        raise classic.ConfigError("unknown classic style")
    raise classic.ConfigError("unqualified style requires explicit origin; never guess S5/S6/S7")


def catalog(include_legacy=False):
    return [{"styleKey": key, **value} for key, value in REGISTRY.items()
            if include_legacy or not key.startswith("legacy:")]


def creator_catalog():
    # Retired from new-project selection; stable numbers and old files still resolve.
    return [{**item, 'option': int(item['id']), 'label': item['name']} for item in selected_styles()]


def with_timeline(template, timeline):
    """Bind NEW timing to a visual template, without copying source/approval records."""
    result = copy.deepcopy(template)
    result.pop('provenance', None)
    result.pop('synthetic', None)
    cfg = result['rendererConfig']
    for field in ('duration','fps','chapters'):
        cfg.pop(field,None)
    cfg.pop('demoLabel',None)
    result.pop('timeline',None)
    chapters = timeline['chapters']
    if result['styleKey'].startswith('classic:'):
        cfg.update(duration=timeline['duration'],fps=float(Fraction(str(timeline['fps']))),chapters=[
            {'start':ch['start'],'end':ch.get('end',chapters[i+1]['start'] if i+1<len(chapters) else timeline['duration']),
             'title':ch.get('label',ch.get('title','')),
             **({'subtitle':ch['kicker']} if ch.get('kicker') and result['styleKey']=='classic:S7' and cfg.get('visualRevision')=='legacy' else {})}
            for i,ch in enumerate(chapters)])
    else:
        result['timeline']={'duration':timeline['duration'],'fps':timeline['fps'],'chapters':[
            {'start':ch['start'],'label':ch.get('label',ch.get('title','')),'kicker':ch.get('kicker','')} for ch in chapters]}
    return result


def new_config(option, timeline, font_regular, font_bold, width=2160, palette=None, character=None):
    check_new_chapters(timeline)
    spec = selected_style(option)
    if not palette:
        raise classic.ConfigError('new config requires an explicitly chosen palette')
    cfg = {'visualRevision':spec['visualRevision'],'progressMode':spec['progressMode'],
           'style':spec['styleKey'].split(':')[1], 'palette':copy.deepcopy(palette),
           'character':copy.deepcopy(character or {'mode':'none'})}
    if spec['styleKey'].startswith('classic:'):
        height=math.ceil(width/960*((100 if cfg['character']['mode']=='none' else 164) if spec['id']=='07' else (120 if cfg['character']['mode']=='none' else 184)))
        cfg.update(width=width,height=height,
                   font=str(font_regular),fontBold=str(font_bold))
    else:
        cfg.update(outputWidth=width,displayWidth=480,fontRegular=str(font_regular),fontBold=str(font_bold),labelSize=18,kickerSize=11)
    return with_timeline({'schemaVersion':1,'styleKey':spec['styleKey'],'rendererConfig':cfg},timeline)


def load(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise classic.ConfigError("config must be a JSON object")
    return value


def inspect_historical_profile(data, base_dir):
    """Diagnostic only: a historical approved profile is not a render config."""
    character = data.get("character", {})
    paths = character.get("assetPaths", []) if isinstance(character, dict) else []
    if not isinstance(paths, list):
        paths = []
    missing = sum(not (Path(base_dir) / p).is_file() for p in paths if isinstance(p, str))
    mode = character.get("mode", "unknown") if isinstance(character, dict) else "unknown"
    style = data.get("style", {})
    known = []
    for name in ("style", "output", "placement", "palette", "typography"):
        if isinstance(data.get(name), dict) and data[name]:
            known.append(name + " (recorded values; exact render equivalence not yet verified)")
    if isinstance(style, dict):
        for name in ("palette", "typography"):
            if isinstance(style.get(name), dict) and style[name]:
                known.append("style." + name)
    if mode != "unknown":
        known.append("character.mode")
    if paths:
        known.append("character.assetPaths (references only)")
    conflicts = []
    if isinstance(style, dict) and isinstance(data.get("palette"), dict) and isinstance(style.get("palette"), dict):
        if data["palette"] != style["palette"]:
            conflicts.append("top-level palette and style.palette differ; compare prior preview before choosing either")
    recover = ["identify the exact renderer/variant from prior preview evidence",
               "locate recorded font family and verify display-to-output scaling",
               "derive chapters/fps and check placement against the current video",
               "map palette tokens without changing recorded colors"]
    not_applicable = []
    if mode == "none":
        not_applicable = ["character asset preparation", "per-frame foot anchors", "walk cadence"]
    else:
        recover.append("measure visible contact anchors and scale from the approved character assets")
    return {"automaticMigration": False, "ready": False, "kind": "historical-profile",
            "reason": "historical profile has no complete render contract",
            "characterAssetCount": len(paths), "missingCharacterAssets": missing,
            "knownFields": known, "conflicts": conflicts, "recoverableByAgent": recover, "notApplicable": not_applicable,
            "manualFields": ["current-video render contract", "exact renderer/variant and font mapping"]
                            + ([] if mode == "none" else ["character contact anchors and scale"]),
            "needsCreatorChoice": ["reuse or changes not already authorized",
                                   "appearance alternatives only if the original cannot be recovered",
                                   "new-video visual review and approvals not already supplied"],
            "nextActions": ["Keep the source profile unchanged and retain its known values in a private project.",
                            "Agent resolves the recoverable fields and shows a before/after preview; do not ask the creator to measure coordinates.",
                            "Create a new routed render config only after the missing contract is resolved; never relabel this profile as verified."],
            "approvalCopied": False, "assetsCopied": False}


def migrate_config(data, origin, source_dir, destination_dir, timeline=None):
    if not isinstance(data, dict) or isinstance(data.get("style"), dict):
        raise classic.ConfigError("historical profile needs manual review; not a render config")
    key = resolve_style(data.get("style"), origin)
    config = copy.deepcopy(data)
    additions = []
    if REGISTRY[key]["engine"] == "gallery":
        unknown = set(config) - GALLERY_FIELDS
        if unknown:
            raise classic.ConfigError("unmapped installed fields: " + ", ".join(sorted(unknown)))
        supplied = config.get("palette", {})
        if not isinstance(supplied, dict) or set(supplied) - set(DEFAULT):
            raise classic.ConfigError("unmapped installed palette tokens")
        # Freeze the old effective palette only for an explicit installed import.
        # Direct gallery selections must always supply all their chosen tokens.
        config["palette"] = dict(DEFAULT) | supplied
        additions = sorted(set(DEFAULT) - set(supplied))
    envelope = {"schemaVersion": 1, "styleKey": key, "rendererConfig": config,
                "assetBase": os.path.relpath(Path(source_dir).resolve(), Path(destination_dir).resolve()),
                "provenance": {"origin": origin,
                               "sourceConfigSha256": hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                               "expandedLegacyPaletteTokens": additions}}
    if timeline is not None:
        if REGISTRY[key]["engine"] != "gallery":
            raise classic.ConfigError("classic configs already contain their timeline")
        envelope["timeline"] = copy.deepcopy(timeline)
    return envelope


def _envelope(data):
    known = {"schemaVersion", "styleKey", "rendererConfig", "assetBase", "timeline", "synthetic", "provenance", "reviewState"}
    if not isinstance(data, dict) or set(data) - known:
        raise classic.ConfigError("unknown routed config fields")
    if type(data.get("schemaVersion")) is not int or data["schemaVersion"] != 1:
        raise classic.ConfigError("routed schemaVersion must be 1")
    key = resolve_style(data.get("styleKey"))
    cfg = data.get("rendererConfig")
    if not isinstance(cfg, dict):
        raise classic.ConfigError("rendererConfig must be an object")
    spec = REGISTRY[key]
    origin = INSTALLED_ORIGIN if spec["engine"] == "gallery" else CLASSIC_ORIGIN
    provenance = data.get("provenance", {})
    if not isinstance(provenance, dict) or provenance.get("origin", origin) != origin:
        raise classic.ConfigError("provenance origin conflicts with style namespace")
    if "style" in cfg:
        native = REGISTRY[resolve_style(cfg["style"], origin)]["nativeStyle"]
        if native != spec["nativeStyle"]:
            raise classic.ConfigError("styleKey conflicts with rendererConfig.style")
    if not isinstance(data.get("assetBase", "."), str):
        raise classic.ConfigError("assetBase must be a directory path")
    if type(data.get("synthetic", False)) is not bool:
        raise classic.ConfigError("synthetic must be boolean")
    if data.get('reviewState') not in (None,'draft','approved'):
        raise classic.ConfigError('reviewState must be draft or approved')
    return key, spec, copy.deepcopy(cfg)


def inspect_config(data, base_dir):
    if isinstance(data, dict) and isinstance(data.get("style"), dict):
        return inspect_historical_profile(data, base_dir)
    key, spec, cfg = _envelope(data)
    assets = Path(base_dir) / data.get("assetBase", ".")
    missing = []
    if spec["engine"] == "gallery":
        paths = [cfg.get("fontRegular"), cfg.get("fontBold")]
        character = cfg.get("character", {"mode": "none"})
        if isinstance(character, dict) and character.get("mode", "none") != "none":
            paths += character.get("frames", [])
        for p in paths:
            if not isinstance(p, str) or not (assets / p).is_file():
                missing.append(p or "unspecified font")
        if "timeline" not in data:
            missing.append("current-video timeline")
    else:
        paths = [cfg["font"]] if cfg.get("font") is not None else []
        character = cfg.get("character", {"mode": "none"})
        if isinstance(character, dict):
            if character.get("mode") == "single-pose":
                paths.append(character.get("path"))
            elif character.get("mode") == "walk-cycle":
                paths += character.get("frames", [])
        for p in paths:
            if not isinstance(p, str) or not (assets / p).is_file():
                missing.append(p or "unspecified character asset")
    return {"styleKey": key, **spec, "ready": not missing, "missing": missing,
            "approvalCopied": False, "assetsCopied": False,
            "note": "ready means referenced inputs exist; run validate for layout and asset checks"}


class GalleryRenderer:
    def __init__(self, envelope, cfg, base_dir, key, native):
        unknown = set(cfg) - GALLERY_FIELDS
        if unknown:
            raise classic.ConfigError("unmapped installed fields: " + ", ".join(sorted(unknown)))
        palette = cfg.get("palette")
        if not isinstance(palette, dict) or set(palette) != set(DEFAULT):
            raise classic.ConfigError("gallery requires all nine explicit palette tokens; migrate to capture old defaults")
        timeline = envelope.get("timeline")
        if not isinstance(timeline, dict) or set(timeline) != {"duration", "fps", "chapters"}:
            raise classic.ConfigError("gallery needs current-video timeline: duration, fps, chapters")
        duration = classic.finite_number(timeline["duration"], "duration", .01, 43_200)
        fps_value = timeline["fps"]
        if isinstance(fps_value, str):
            try:
                fps_value = float(Fraction(fps_value))
            except (ValueError, ZeroDivisionError, OverflowError) as exc:
                raise classic.ConfigError("fps must be numeric or a valid fraction") from exc
        fps = classic.finite_number(fps_value, "fps", 1, 120)
        width = classic.integer(cfg.get("outputWidth", 2160), "outputWidth", 240, 7680)
        classic.finite_number(cfg.get("displayWidth", 480), "displayWidth", 240, 7680)
        classic.finite_number(cfg.get("labelSize", 18), "labelSize", 16, 120)
        classic.finite_number(cfg.get("kickerSize", 11), "kickerSize", 1, 80)
        if math.ceil(duration * fps - 1e-9) > classic.MAX_FRAMES:
            raise classic.ConfigError("gallery output exceeds frame limit")
        chapters = timeline["chapters"]
        if not isinstance(chapters, list) or not 1 <= len(chapters) <= 24:
            raise classic.ConfigError("gallery needs 1–24 current chapters")
        previous = -1
        for chapter in chapters:
            if not isinstance(chapter, dict):
                raise classic.ConfigError("chapter must be an object")
            start = classic.finite_number(chapter.get("start"), "chapter start", 0, duration)
            if start <= previous or start >= duration:
                raise classic.ConfigError("chapter starts must increase before duration")
            if not isinstance(chapter.get("label"), str) or not chapter["label"].strip():
                raise classic.ConfigError("gallery chapter label is required")
            previous = start
        if chapters[0]["start"] != 0:
            raise classic.ConfigError("chapters must start at zero")
        char = cfg.get("character", {"mode": "none"})
        if not isinstance(char, dict):
            raise classic.ConfigError("character must be an object")
        if set(char) - {"mode", "frames", "anchors", "visibleHeight", "cycleFps", "bodyPivotX"}:
            raise classic.ConfigError("unmapped installed character fields; review manually")
        if char.get("mode", "none") == "none" and set(char) - {"mode"}:
            raise classic.ConfigError("none must not contain hidden character fields; review migration explicitly")
        effective = cfg | {"style": native}
        self.overlay = Overlay(effective, chapters, duration, base_dir)
        self.demo_band=math.ceil(28*self.overlay.scale) if envelope.get('synthetic') else 0
        if self.demo_band and (self.overlay.h+self.demo_band)%2:self.demo_band+=1
        if self.demo_band:
            classic.require_glyphs(self.overlay.reg,'合成示意 / SAMPLE')
        if self.overlay.w * self.overlay.h > classic.MAX_PIXELS or self.overlay.h > 4320:
            raise classic.ConfigError("gallery canvas exceeds size limit")
        self.config = SimpleNamespace(width=width, height=self.overlay.h+self.demo_band, duration=duration,
                                      fps=fps, style=key, character=copy.deepcopy(char),
                                      demo_label=envelope.get("synthetic", False))

    def frame(self, time):
        time = classic.finite_number(time, "time")
        content=self.overlay.frame(min(self.config.duration, max(0., time)))
        if not self.demo_band:return content
        from PIL import Image, ImageDraw
        out=Image.new('RGBA',(self.config.width,self.config.height))
        out.alpha_composite(content,(0,self.demo_band))
        ImageDraw.Draw(out).text((round(18*self.overlay.scale),self.demo_band//2),'合成示意 / SAMPLE',
            font=classic.font_at(str(self.overlay.reg),max(12,round(12*self.overlay.scale))),fill=self.overlay.p['text'],anchor='lm')
        return out


def build_renderer(data, base_dir, *, draft=False):
    key, spec, cfg = _envelope(data)
    if (data.get('reviewState')=='draft') != bool(draft):
        raise classic.ConfigError('Pending draft requires the explicit draft route; never relabel it as an approved sample/final')
    base = (Path(base_dir) / data.get("assetBase", ".")).resolve()
    if spec["engine"] == "classic":
        if "timeline" in data:
            raise classic.ConfigError("classic timeline must stay inside rendererConfig")
        cfg["style"] = spec["nativeStyle"]
        if data.get("synthetic"):
            cfg["demoLabel"] = True
        renderer=classic.Renderer(classic.validate_config(cfg, base,allow_unapproved=draft))
    else:renderer=GalleryRenderer(data, cfg, base, key, spec["nativeStyle"])
    if draft:
        from draft_review import DraftRenderer
        return DraftRenderer(renderer)
    return renderer


def export_mov(data, base_dir, output, purpose, start=0., seconds=None, final_approved=False):
    renderer = build_renderer(data, base_dir,draft=purpose=='draft')
    c = renderer.config
    start = classic.finite_number(start, "start", 0, c.duration)
    if start >= c.duration:
        raise classic.ConfigError("start must be before duration")
    if purpose == "final":
        if not final_approved or c.demo_label or start != 0 or seconds is not None:
            raise classic.ConfigError("final requires actual approval, a non-synthetic full timeline and no range")
        duration = c.duration
    elif purpose in ("sample", "debug", "draft"):
        if final_approved:
            raise classic.ConfigError("final approval flag is only valid for final")
        limit = 30 if purpose == "debug" else 15
        duration = classic.finite_number(seconds if seconds is not None else min(limit, c.duration-start), "seconds", .01, limit)
        if start + duration > c.duration + 1e-9:
            raise classic.ConfigError("range exceeds source duration")
    else:
        raise classic.ConfigError("unknown export purpose")
    if Path(output).suffix.lower() != ".mov":
        raise classic.ConfigError("transparent output must use .mov")
    result = classic.export_video(renderer, output, start, duration)
    return result | {"styleKey": resolve_style(data["styleKey"]), "purpose": purpose,
                     "syntheticDemo": c.demo_label,
                     "reviewState":'draft' if purpose=='draft' else data.get('reviewState','unspecified'),
                     "userApproved":False if purpose=='draft' else 'caller evidence required',
                     "finalDelivery":purpose=='final'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cat = sub.add_parser("catalog")
    cat.add_argument("--include-legacy", action="store_true")
    cat.add_argument("--creator-facing", action="store_true", help="Return visible option numbers with internal route mappings for the host.")
    fresh = sub.add_parser('new-config', help='Use the exact current creator catalog, never guess old S IDs.')
    fresh.add_argument('output')
    fresh.add_argument('--option',required=True)
    fresh.add_argument('--timeline',required=True)
    fresh.add_argument('--font-regular',required=True)
    fresh.add_argument('--font-bold',required=True)
    fresh.add_argument('--width',type=int,default=2160)
    fresh.add_argument('--palette',required=True)
    fresh.add_argument('--character')
    fresh.add_argument('--draft',action='store_true',help='Pending marked review; does not approve assets or final export')
    migrate = sub.add_parser("migrate-config")
    migrate.add_argument("input")
    migrate.add_argument("output")
    migrate.add_argument("--origin", choices=(INSTALLED_ORIGIN, CLASSIC_ORIGIN), required=True)
    migrate.add_argument("--timeline")
    for name in ("inspect", "validate", "preview", "mov"):
        cmd = sub.add_parser(name)
        cmd.add_argument("config")
        if name in ("preview", "mov"):
            cmd.add_argument("output")
        if name == "preview":
            cmd.add_argument("--time", type=float, default=0)
        if name in ('preview','validate'):
            cmd.add_argument('--draft',action='store_true',help='Explicit marked pending-review route; grants no approval')
        if name == "mov":
            cmd.add_argument("--purpose", choices=("debug", "draft", "sample", "final"), required=True)
            cmd.add_argument("--start", type=float, default=0)
            cmd.add_argument("--seconds", type=float)
            cmd.add_argument("--final-approved", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            result = creator_catalog() if args.creator_facing else catalog(args.include_legacy)
        elif args.command == 'new-config':
            target=Path(args.output).resolve()
            result=new_config(args.option,load(args.timeline),Path(args.font_regular).resolve(),Path(args.font_bold).resolve(),
                              args.width,load(args.palette),load(args.character) if args.character else None)
            if args.draft:result['reviewState']='draft'
            renderer=build_renderer(result,target.parent,draft=args.draft)
            classic.ensure_new_output(target).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            result={'output':str(target),'styleKey':result['styleKey'],'width':renderer.config.width,'height':renderer.config.height}
        elif args.command == "migrate-config":
            source, target = Path(args.input).resolve(), Path(args.output).resolve()
            data = load(source)
            if isinstance(data.get("style"), dict):
                print(json.dumps(inspect_historical_profile(data, source.parent), ensure_ascii=False, indent=2))
                return 2
            result = migrate_config(data, args.origin, source.parent, target.parent,
                                    load(args.timeline) if args.timeline else None)
            classic.ensure_new_output(target).write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            result = inspect_config(result, target.parent) | {"output": str(target)}
        else:
            path = Path(args.config).resolve()
            data = load(path)
            if args.command == "inspect":
                result = inspect_config(data, path.parent)
            elif args.command == "mov":
                result = export_mov(data, path.parent, args.output, args.purpose, args.start, args.seconds, args.final_approved)
            else:
                renderer = build_renderer(data, path.parent,draft=getattr(args,'draft',False))
                if args.command == "preview":
                    classic.save_image(renderer.frame(args.time), args.output)
                    result = {"output": str(Path(args.output).resolve()), "styleKey": data["styleKey"]}
                else:
                    c = renderer.config
                    times = {0., c.duration}
                    content=getattr(renderer,'renderer',renderer)
                    if isinstance(content, GalleryRenderer):
                        times.update(content.overlay.starts)
                    else:
                        times.update(ch.start for ch in c.chapters)
                    for t in times:
                        renderer.frame(t)
                    result = {"valid": True, "styleKey": data["styleKey"], "width": c.width, "height": c.height}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (classic.ConfigError, ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, str(exc)+"\n")


if __name__ == "__main__":
    raise SystemExit(main())
