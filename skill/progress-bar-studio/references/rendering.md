# Deterministic overlay renderer

`scripts/render_progress.py` turns approved chapter/style/color choices and optional approved PNG character assets into actual RGBA frames. The same renderer makes the PNG preview and ProRes 4444 MOV. It never analyzes a video, generates a character, approves an asset, saves a reusable preset, or publishes a file.

## Approval boundary

Continue to follow `guided-conversation.md` and `confirmation-gates.md`. The caller must verify real chapter, character, palette and design approval before a project sample, and full-export permission before a full export. A CLI flag or a JSON `approved: true` is an operator attestation, not evidence of a user response. Never fabricate approval to satisfy the tool.

0.7 adds a separate pending-review route through style_router.py: set envelope reviewState=draft,
create with new-config --draft and export mov --purpose draft. It accepts technically valid unapproved
four-frame assets without changing character.approved, is limited to 15 seconds, and always marks
the output 待审方案 / DRAFT. Draft configs cannot use sample/final or save as a verified visual profile.
After actual combined review, record the user's decision and create an approved config; do not rerun
the same approval question merely because the draft label is removed. A real short-draft approval
can satisfy the sample gate for the same content; full export and saving still need actual authorization.
Do not route real review through debug or label a real source as synthetic to bypass approval.
For static pending checks, use style_router.py validate --draft or preview --draft; these keep the
marked draft route rather than requiring fake approval. Both classic and gallery support it.

- `preview` is a static design check; `validate` checks config/layout only.
- `mov --purpose sample` makes at most 15 seconds after design approval. Select `--start` so the sample crosses an actual chapter boundary; use the whole clip if it is shorter than 15 seconds.
- `mov --purpose final --final-approved` exports the complete timeline only after the caller checks full-export authorization. It does not create a delivery folder or bypass `prepare_delivery.py`.
- `--purpose debug` permits at most 30 seconds for explicit development/test work. It does not count as creator approval.
- `demo-video` produces an opaque MP4 solely for a labeled synthetic demonstration. It is never an alternative final delivery, an editor-import test, or a composite of the user's original video.
- The bundled example is invented content with `demoLabel: true`. It cannot be exported with `--purpose final`.

A development board is not a final visual approval. If the creator rejects any style or sends references, keep those choices pending and regenerate only the relevant previews after revising them.

## Requirements

Python 3.10+, Pillow, and a local CJK font such as Noto Sans CJK or Source Han Sans. MOV/MP4 commands also require `ffmpeg` and `ffprobe`. The script detects installed Noto Sans CJK, PingFang and Microsoft YaHei, including known regular-font filenames in macOS user and system Library/Fonts directories; supply `font` for another font path. Unloadable automatic candidates are skipped, while an invalid explicit font remains an error. It does not download fonts or install dependencies. For Linux CI with Chinese examples, install `fonts-noto-cjk` in the approved environment setup.

## JSON contract

Start from `assets/examples/demo-render.json` or run `demo-config` below, then replace invented chapters and explicitly confirm every creative choice. Paths in the config resolve relative to the config file, never relative to a guessed task folder.

Required fields:

- `duration`: finite seconds, greater than zero, at most 43,200.
- `fps`: finite frames per second from 1 to 120; use the analyzed video's real rate, including fractional rates.
- `width`, `height`: integer output-canvas pixels. Width 320–7680, height 96–4320; maximum 16,777,216 pixels and 432,000 output frames.
- `style`: `S1` / `capsule`, `S2` / `runway`, `S3` / `text`, `S4` / `band`, `S5` / `current-card`, `S6` / `ring`, or `S7` / `hanging-tabs`.
- `chapters`: 1–24 objects containing `start`, `end`, `title`, plus optional `subtitle`. They must be ordered, positive-length and contiguous from zero to duration. Gaps/overlaps above `min(0.001, 0.01/fps)` seconds fail; smaller serialization noise is normalized. Titles are 1–200 printable characters. Optional subtitles are at most 120 printable characters and are displayed only by S7; no control characters are allowed. The exact boundary belongs to the new chapter; the timeline endpoint belongs to the last chapter.
- `palette` or `palettePreset`: without a preset, supply all seven tokens `surface`, `active`, `inactive`, `text`, `active-text`, `outline`, `shadow` as `#RRGGBB` or `#RRGGBBAA`. The first five must be opaque. Text/surface and active-text/active must each pass 4.5:1 contrast. Transparent output means the canvas outside the graphic is transparent, not that label surfaces have to be translucent.

Optional fields:

- `visualRevision`: omit or `legacy` to preserve older pixels; `refined-20261030` selects the older 01/02/07 geometry revision. New configs use the per-style values from selected-styles.json, not this old shared default.
- For 0.7.4 new work, obtain each style's exact revision with `style_router.py new-config`.
  Classic S1/S2 and gallery S1 support `readable-20261030` full-label auto-grid layouts.
  Height is derived once from all chapters and stays fixed for the entire clip; report that actual height.
- The current 07 preview uses `editorial-20261030` on S7 only: a single progress rail, all numbered chapter labels, and a small current-ordinal highlight. Previous S7 appearances remain available through their original revision values. New geometry is pending the creator's visual review, not an approved saved preset.
- `fontBold`: optional local bold font file; relative to the config like `font`. Used for refined main labels. Keep the exact revision and font references when reusing a project.
- `progressMode`: defaults to `time-linear`. Equal-slot S1/S7 also accept `chapter-weighted`; their track, foot anchor and active slot then share the same chapter mapping. S2/S4 duration-proportional geometry does not accept this mode. Preserve old project values; do not silently change them.

- `schemaVersion`: integer `1`.
- `font`: local font path. Both regular and bold cmap coverage are checked against actual labels; a loadable Latin-only font is rejected for Chinese labels. This check does not install fonts.
- `character`: defaults to `{"mode":"none"}`. See below.
- `demoLabel`: defaults to false; true visibly marks synthetic demonstration frames.
- `palettePreset`: `cream-tea`, `sage`, `lavender`, or `navy-cream`. A named preset supplies a complete editable starting palette; any explicit `palette` keys override it. The caller still needs the creator's project-specific palette approval.
- `palette.progress` and `palette.progress-inactive`: optional independent short-underline colors. They default to `active` and `inactive` unless a preset specifies one. Progress is never silently assigned the text color.
  These tokens affect S3 short underlines, not every style's main track. S1/S2 main rails use active/inactive; change those tokens when customizing their fill. Do not promise ignored tokens will recolor a rail.
- `palette.muted-text` and `palette.accent-text`: optional text-only/inactive and current-chapter text colors. Both fall back to `text`. These are independent of block fill colors.

The default demonstration is warm cream and milk-tea brown. The other starting palettes are muted sage, soft lavender with a restrained magenta text accent, and navy/cream. They are options, not a permanent preference or a ban on dark colors. No user's brand palette is inferred. All tokens remain explicitly overridable. See `assets/palettes/reference-palettes.json` and `references/style-grammar.md`.

Example using a preset and a single independent override:

```json
{"palettePreset": "lavender", "palette": {"progress": "#A64077"}}
```

The existing required-pair contrast checks remain in place. Since S2/S3 text floats on a transparent canvas, legibility against the actual video still needs a composite check; `surface` contrast cannot certify an unseen background.

### Canvas and readability

`width`/`height` are explicit output dimensions, not a promise to auto-fit an editing project. A `1280×320` strip remains a strip. A `1080×1920` full canvas remains portrait, with S1–S6 near its bottom and S7 attached to its top edge. Establish the original aspect ratio, final canvas, strip placement and scale in the workflow first. Do not treat the old width-only export-size estimate as a portrait-layout instruction.

S1/S3 labels use evenly spaced semantic slots while their track uses real elapsed time. S2 runway sections and their labels use the same true-time bounds. S4 partitions its band by real chapter duration. Tiny timed S2/S4 segments fail with a readable error instead of silently shrinking text or changing chapter timing. S5/S6 show just the current title and are useful when all chapter labels cannot fit. S7 adds an optional top-edge hanging-tab form, with a deeper current tab and optional secondary English labels. S7 is numbered as a built-in optional style. It is not the custom-reference route. These are seven classic renderer routes. The full creator catalog 01–15 also includes eight gallery routes; use style_router.py for the mapping. A creator-supplied custom reference remains a distinct route.

S1 preserves low-profile chapter capsules below a thin total-progress track. S2 uses one runway segment per chapter with quiet unboxed labels. S3 renders only text, thin vertical separators, and one short active underline; it never draws a filled chapter background or full-width text-color baseline. S4 is a single slim band whose fill advances along the true timeline; label colors are clipped across the moving fill for legibility. It does not stack an active pill on top of a second track. Approved S4 character assets may require a taller band and retain their original collision checks. S5/S6 stay compact. S7 remains attached to the top edge with rounded lower corners.

Fonts do not shrink indefinitely. Older revisions retain their historical one-line ellipsis behavior.
Current selected 01/02/08 preserve full labels, selecting an automatic multi-row chapter area when needed.
Current 07 rejects a title that cannot fit; offer an accurate shorter name or one of those multi-row layouts.
Do not change semantic chapter boundaries merely for layout. Inspect the actual smallest publishing size
and a real-video composite before approval; a geometry check cannot locate subtitles or faces in an unseen video.

### Approved character inputs

No character:

```json
{"mode":"none"}
```

This mode rejects hidden asset/path fields and never opens an image file.

Legacy single pose (read old projects only; new projects choose none or four frames):

```json
{"mode":"single-pose","approved":true,"path":"assets/my-approved-pose.png","height":64}
```

Four-frame cycle, in the already approved playback order:

```json
{"mode":"walk-cycle","approved":true,"frames":["f1.png","f2.png","f3.png","f4.png"],"height":64,"cadence":6}
```

All assets must be RGBA PNGs containing transparent and opaque pixels. Height is in output-canvas pixels. One common scale preserves proportions across a cycle; the renderer never flips, recolors, rotates, deforms or rewrites source assets. `single-pose` means no gait animation, while total progress still advances.

Optional `contacts` supplies one `[x,y]` planted-foot coordinate per source frame. Every point must be inside visible alpha. Without it, the renderer uses the median visible pixel of the lowest visible row. Cropping transparent padding is internal only. It binds the visible foot to the elapsed-time edge and checks canvas bounds. S4 reserves a moving quiet zone in all intersected label sections, including transition frames. S5/S6 characters use a separate horizontal lane above the card; S7 uses a lower horizontal lane that must clear all hanging tabs; they never orbit the ring. Wide characters or tight bands may fail readability checks; do not silently distort the asset to make it fit.

0.6.1 shares four-frame validation across splitter, bundle reader and both renderers:
equal canvases, genuine transparent/opaque pixels, no duplicate or translation-only copied poses.
This is technical validation, not automatic gait/identity approval. Foot anchors require Alpha>32;
default geometry ignores near-invisible specks without rewriting source PNGs.
For newly aligned frames, optional character.bodyPivotX is one constant source-cell X for the head/torso;
contacts still supply visible physical foot Y. This prevents alternating foot X from shaking the body.
The gallery equivalent uses the same bodyPivotX plus anchors. It does not accept transparent foot anchors.
Omit bodyPivotX to preserve legacy explicit-foot positioning; review any change on a short sample.

Synthetic labels reserve a separate fixed header band in both engines. Actual output height includes it;
the marker never covers the track or character. Synthetic output remains ineligible for final delivery.
Use prepare_walk_sheet.py for explicit horizontal/2x2 preparation and make_multibg_preview.py for
portable six-background review. Both refuse existing output names; neither grants approval.

Cycle cadence is fixed playback of the four approved frames. This first renderer does not synthesize gait, physical foot-locking or long-video chapter-burst choreography. The sample approval must check that motion reads naturally at the actual travel speed.

## Commands

Run from `skill/progress-bar-studio` (choose new output paths; existing files are never overwritten):

```bash
python3 scripts/render_progress.py demo-config /tmp/elleflow-demo.json
python3 scripts/render_progress.py validate /tmp/elleflow-demo.json
python3 scripts/render_progress.py preview /tmp/elleflow-demo.json /tmp/preview.png --time 4.5
python3 scripts/render_progress.py contact-sheet /tmp/elleflow-demo.json /tmp/seven-styles.png --time 4.5
python3 scripts/render_progress.py mov /tmp/elleflow-demo.json /tmp/sample-transparent.mov \
  --purpose sample --start 2 --seconds 3
python3 scripts/render_progress.py demo-video /tmp/elleflow-demo.json /tmp/style-demo.mp4 \
  --purpose debug --seconds 10 --all-styles
```

After actual sample approval and full-export authorization, with a real project config and a newly reserved delivery directory:

```bash
python3 scripts/render_progress.py mov /path/to/approved-project.json \
  /path/to/new-delivery/progress_bar.mov --purpose final --final-approved
```

The export streams RGBA frames into FFmpeg instead of saving a huge PNG sequence. It uses ProRes 4444, profile 4, alpha, and no audio. Frames use their actual presentation times (`start + frame_index/fps`). Do not force the final encoded frame to the timeline endpoint: that would display chapter changes early. A separately requested static preview at `duration` shows the completed state. Durations that are not an integral number of frames are rounded up to the next frame; the JSON report states both requested and encoded duration. Output is first written to a temporary file and atomically installed without overwriting another file.

## Validation and honest claims

The export report includes dimensions, fps, frame count, codec/profile/pixel format, size and SHA-256. Metadata alone is not an alpha test. Run the existing full-scan checker and real-video boundary previews:

```bash
bash scripts/verify_alpha_mov.sh /path/to/sample-transparent.mov
# From the repository root, not the skill directory:
python3 -m unittest discover -s tests -v
```

A decoded format of `yuva444p12le` is normal for ProRes 4444. Require every decoded frame to contain transparent and opaque pixels. Inspect contact, passing, start/end and every chapter boundary over the real video, then the smallest display size and multiple background colors. A successful encoder/alpha scan does not prove editor compatibility; the report keeps `editorImport: unverified` until an actual import is confirmed.

## Brand preset → render config: explicit manual adapter

This section applies only to older schema-4 preset.json files. New complete visual profiles
support automatic exact-config restore for all eight executable routes through visual_profile.py;
see [visual-profiles.md](visual-profiles.md). Do not downgrade a new profile to the old schema.

`preset_library.py` schema 4 and this renderer's schema 1 are different formats.
There is no automatic preset-import command. Never hand `preset.json` to the
renderer, rename its schema, copy its approval flags, or silently discard fields
that the renderer cannot represent. `reuseEligible: true` establishes bundle
integrity and the recorded earlier approvals; it does not establish renderer
compatibility or permission for a new final export.

Before offering unchanged quick reuse, inspect the preset with
`show --require-verified` and recover the approved visual design where needed.
Then build a fresh render config for the current video as follows:

- `style.route` maps directly only for S1–S7. Verify `style.variant` matches the
  corresponding built-in geometry in this version. An arbitrary variant name is
  descriptive, not executable. `custom` requires a separately implemented design
  or explicit agreement that a shown S1–S7 interpretation is acceptable.
- `palette` uses the same token names only if all seven required renderer tokens
  are present. Copy approved `progress`, `progress-inactive`, `muted-text` and
  `accent-text` values too. Expand a named palette to its actual approved values
  before saving it; the brand preset does not store `palettePreset`. Old
  `primary` tokens have no automatic alias. Derive missing tokens visibly and
  ask about the affected color choice instead of assuming an exact match.
- The 0.5 candidate accepts both #RRGGBB and #RRGGBBAA palette values, preserving
  alpha for shadows/outlines. Older 0.4 readers may reject eight-digit values.
  Preset storage validates syntax; renderer validation additionally enforces
  its supported tokens, opacity and contrast. Storage success is not render
  validation.
- `character.mode: none` becomes exactly `{"mode":"none"}`. Do not copy empty
  `asset` or `cycle` fields into the renderer's no-character object.
- `single-pose` maps `character.asset` to renderer `character.path`, resolved
  against the preset directory or copied into the new task with opt-in reuse.
  `walk-cycle` maps the verified `character.cycle.frames` in the manifest's
  playback order to renderer `frames`; its `fps` maps to `cadence` only when
  within the renderer's 1–12 range. Do not reorder or silently clamp it. Set
  `approved: true` only after checking the actual reuse/asset decision.
- Renderer `character.height`, optional foot `contacts`, and `font` are not
  saved by schema 4. Recover them from the approved design record, adjusting
  scale deliberately for the new explicit dimensions. If that record is
  unavailable, preview the proposed values and resolve only the missing choice.
  Do not promise pixel-identical or no-review reuse from the brand preset alone.
- `placement.label`, `x`, `y`, and `overlayScale` are placement intent for the
  host/editor. The renderer has no corresponding fields and draws each built-in
  at its fixed internal anchors. Apply verified editor placement/scale outside
  the config. If the approved intent requires a different internal anchor,
  choose a reviewed extension rather than silently ignoring it.
- `duration`, `fps`, `chapters`, output `width`/`height`, destination and current
  project approvals always come from this project. They are never inherited.

Run `validate`, render a real-video composite, and continue the original
combined-preview/sample/final-approval gates. Keep the original approved render
config as project evidence; it is not currently embedded in the portable brand
preset. Do not claim a preset-only export is a lossless renderer round trip.
