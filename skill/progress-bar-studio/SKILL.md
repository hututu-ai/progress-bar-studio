---
name: progress-bar-studio
description: "Create custom animated chapter progress bars through a five-step workflow: upload media, optionally generate a same-IP single walking pose or 4-frame walk cycle, derive semantic chapters, choose one of four presets or upload a favorite progress-bar reference for a custom style, edit colors, then preview and export transparent assets. Use for video chapter analysis, reference-led progress-bar reconstruction, character-led progress indicators, transparent PNG/WebP frames, sprite sheets, static style previews, and 4K ProRes 4444 MOV overlays for 剪映/CapCut, Premiere, Final Cut, or similar editors."
compatibility: "Requires local file access plus ffmpeg, ffprobe, and Python 3. Pillow is needed for four-frame character cycles. Transcription, image editing, and editor-import testing depend on the host."
metadata:
  version: "0.2.1"
---

# ElleFlow｜小人走路视频进度条动画

Create a reusable animated chapter progress bar that matches the source video,
keeps the user in control through one explicit confirmation at every step, and
exports a genuinely transparent editing asset.

## First-run onboarding

On the first turn after the Skill is invoked, when the user has not supplied a
usable source video or a concrete editing request, send a short welcome message
before explaining any workflow. Lead with what the user can send next. Do not
surface internal terms such as five-step workbench, Alpha, ProRes, manifests,
or QC in this message. Do not start media processing until a source video is
provided.

Reply in the user's language. For a Chinese-speaking user, use this message:

```text
ElleFlow｜小人走路视频进度条动画

直接把一段带声音的视频发给我，我会帮你把内容切成清晰章节，并做成可叠加到剪映、PR 等剪辑软件里的动态进度条。

你可以这样开始：
- 只发视频：我先帮你划分视频章节。
- 视频 + 角色图：让你的 IP 跟着进度条移动。
- 视频 + 参考图：按你喜欢的版式做一版。
- 视频 + 一个颜色：按你的品牌色设计。

最简单的方式：直接上传视频，然后说“给这个视频做进度条”。
```

When a source video is supplied, acknowledge the files and begin only the
Step 01 material brief. Keep technical implementation details out of the
opening response unless the user asks for them.

## Product contract

Use the approved five-step workbench as the canonical order:

1. upload material;
2. generate or skip a character;
3. derive chapters;
4. choose a preset or custom reference style and edit colors;
5. preview and export.

Before starting, read
[references/confirmation-gates.md](references/confirmation-gates.md). Treat
each step as a small agreement with the user: show what was understood, show the
current evidence or preview, ask one short confirmation question, and continue
only after approval. Never hide a costly generation or render behind a generic
"next" action.

When a webpage accompanies the Skill, treat it as the control surface for files,
choices, previews, and configuration. Codex performs the actual image editing,
transcription, frame preparation, rendering, and Alpha QC. Do not claim that a
prototype webpage directly generates or exports media unless its backend is
actually connected and tested.

## Environment preflight

At Step 01, run
`scripts/preflight.py --source-video <source-video> --output-dir <output-folder> --json`
before transcription, image generation, or rendering. Treat a reported blocker
as a stop condition and show the matching next action. `SOURCE_AUDIO_MISSING`
is a warning rather than a false promise: request an editable timestamped chapter
list, or ask for a version with audio before automatic chapter analysis. Do not
silently fall back from a transparent MOV request when FFmpeg or the ProRes
encoder is unavailable.

The preflight reports host-dependent transcription and image editing as warnings,
not guarantees. If transcription is unavailable, ask the user for an editable
timestamped chapter list; do not divide the video into equal durations. If image
editing is unavailable, offer no-character or the original single-pose path.

## Inputs and defaults

Collect or infer only what is needed:

- source video (required for a renderable project). If no source video is
  available, offer planning-only advice but do not enter the production workflow,
  derive speech-based chapters, render a preview, or claim a deliverable;
- optional chapter labels/timestamps; otherwise derive them from speech;
- character choice: uploaded character or no character;
- when a character is used, animation choice: single-pose light motion or one
  fixed 4-frame cycle;
- one of four preset styles or one uploaded progress-bar reference for a custom
  style, plus an editable palette, HEX value, or palette image;
- target editor, canvas orientation, output resolution, and output folder.

Do not ask the user to choose frame count or character placement. The only
animation choices are `single` and `four-frame`; the selected style determines
placement. Ask only for genuinely missing choices and infer technical defaults.

Treat delivery folder and output resolution as material-brief decisions. Ask for both
in the same Step 01 confirmation card. If the user has not specified a delivery
folder, default to the exact directory containing the source video; present that
path as an inferred default and never overwrite an existing output. If the user
has not chosen a resolution, show 1080p (1920 pixels wide), 2K (2560 pixels
wide), and 4K (3840 pixels wide), with a size-planning range for each. The user may approve one inferred recommendation, but do not silently default to
4K. A full-frame canvas is a separate explicit request, not the meaning of the
transparent-strip resolution presets.

Never invent, download, silently reuse, or package a character from another
task. Preserve the uploaded file unchanged. Codex owns same-IP pose generation,
background removal, transparent RGBA preparation, and Alpha verification. Read
[references/character-preparation.md](references/character-preparation.md).

Treat every palette value as editable. If the user supplies one color, derive
and show a compact four-swatch family: main, light surface, deep accent, and
text. Expand internally to inactive, active-text, outline, and shadow tokens as
needed. Do not silently default every project to pink; use the lime/black/white
catalog only as a neutral product example.

When a source video exists, probe it before designing. Transcribe speech when
timing is absent and prefer 4–7 semantic chapters with labels of 2–6 Chinese
characters. Never divide by equal duration when speech reveals real transitions.

Default delivery when the user approves the inferred material brief:

- the exact folder containing the source video, with versioned filenames if an
  output name already exists;
- a user-confirmed 1080p (1920 pixels wide), 2K (2560 pixels wide), or 4K
  (3840 pixels wide) transparent strip, with layout-derived height;
- source frame rate, otherwise 30 fps, and exact source duration;
- ProRes 4444 MOV master with no audio;
- lightweight MP4 composite preview with source audio;
- transparent character PNG or four PNG frames, sprite sheet, animated WebP,
  and cycle manifest when a character is used;
- chapter-transition and multi-background QC images.

Interpret 1080p, 2K, and 4K as 1920-, 2560-, and 3840-pixel-wide transparent
strips unless the user explicitly requests a full 1920x1080, 2560x1440,
3840x2160, or vertical canvas. Explain that the strip avoids encoding unused
transparent pixels.

## Canonical five-step workflow

### 1. Upload material

Preserve source files unchanged and probe the video with
`scripts/probe_video.sh`. Record dimensions, fps, duration, frame count, audio,
file size, and available disk space. Accept an optional original IP image and
optional palette/reference image in the same step.

Present one material brief containing the exact files, duration, dimensions,
fps, audio, character choice, intended editor, output folder, and all three
output resolutions: 1080p (1920 pixels wide), 2K (2560 pixels wide), and 4K
(3840 pixels wide). Run
`scripts/estimate_export_size.py <source-video> --output-dir <output-folder>`
to show a planning size range and available space in the actual delivery folder
for every resolution. State that the range is based on source duration, fps, and
a provisional strip height, and that a 15-second sample will produce the final
estimate after style approval.

Ask for one material-brief approval that includes the source, output folder, and
selected output resolution. If no folder was specified, the source-video
directory is the inferred default; if no resolution was specified, recommend one
based on the source but require approval before continuing. Immediately after
approval, run
`scripts/prepare_delivery.py --source-video <source-video> --output-dir <output-folder> --character-mode <none|single-pose|walk-cycle> --json`
to reserve a new versioned delivery directory. Use its returned directory for
all project files. Stop for **Step 01 material approval** before transcription,
image generation, or rendering. Label every inferred technical default as
inferred.

### 2. Generate or skip the character

If the user chooses no character, skip character generation cleanly and keep all
four styles usable without a mascot.

If a character is used:

1. record silhouette, proportions, facial markings, colors, clothing,
   accessories, outline, and texture as identity anchors;
2. create either one right-facing walking pose or one aligned four-frame cycle;
3. export a real RGBA PNG; for four frames, generate one shared sprite sheet,
   remove its background, and split it with `scripts/split_walk_cycle.py`;
4. verify Alpha, identity, visible foot baseline, edges, holes, and small details;
5. show source, output, loop preview, and multi-background QC together.

Use image editing with the uploaded source as the identity reference. Reject and
retry any result that redesigns the IP. Obtain explicit identity approval before
placing the character into progress-bar styles.

If the user explicitly chose `no-character` in Step 01, record it as approved
in the decision log and proceed directly to Step 03; do not ask a second,
content-free confirmation. Use a separate Step 02 approval only when a character
asset was generated, edited, or repaired. If the user rejects a character result,
regenerate only character assets; do not re-probe the video.

### 3. Derive chapters

Read [references/chapter-analysis.md](references/chapter-analysis.md). Transcribe
with timestamps, detect semantic turns, and present one editable manifest with
exact starts, 2–6-character labels, and a short rationale. Keep the first start
at zero and starts strictly increasing. Ask for confirmation of the timeline.

Stop for **Step 03 chapter approval**. Do not create style previews from an
unapproved timeline. If the chapter timeline changes later, invalidate Step 04
and Step 05 approvals while keeping approved source and character decisions.

### 4. Choose style and colors

Read [references/style-system.md](references/style-system.md). Show the exact four
presets on pure-white cards:

1. S1 chapter capsules;
2. S2 segmented runway;
3. S3 text progress;
4. S4 divided label band.

Beside the four presets, show one `Custom reference` card. When selected, read
[references/custom-reference-style.md](references/custom-reference-style.md),
accept one user-owned PNG, JPG, or WebP screenshot, and derive the structure
without adding a sixth workflow step. Treat the reference as a fifth selection
route, not a fifth built-in preset. Infer track geometry, chapter divisions,
label hierarchy, fill behavior, character travel plane, palette, border radius,
and shadow language; do not ask the user to choose character placement.

Preserve the uploaded reference unchanged. Create a concise style manifest with
`mode: custom-reference`, source filename, inferred pattern, placement, palette
policy, and adaptation notes. Replace source labels with the approved chapters,
adapt the result to the real video and current-task character, and show a static
reconstruction over the real video before animation. If the reference is too
ambiguous to infer one safe structure, ask only whether to preserve its colors
or apply the project palette. Do not reproduce third-party logos, watermarks,
copyrighted characters, or exact proprietary artwork.

Use the approved current-task character in all applicable thumbnails. Show the
four-swatch palette with HEX values. Let the user select one primary preset or
one custom reference route. Combine at most one secondary pattern only when
requested. Do not ask placement.

Create one representative frame over the real video and a transparent overlay
preview. Keep it clear of subtitles, faces, key UI, and demonstrations. Run the
track-fit tests and make white, black, red, blue, brand-color, and checkerboard
composites. Obtain explicit visual approval.

Stop for **Step 04 visual approval** after showing the chosen route, palette,
chapter layout, character travel plane, real-video composite, transparent
preview, and any custom-reference structure manifest. If the style, palette, or
placement changes later, invalidate only Step 05 approval.

### 5. Preview and export

Render deliverables from the approved configuration. Offer a 15-second
transparent sample crossing a chapter boundary when editor compatibility or file
size is uncertain. The sample is required before any claim of editor-import
compatibility or a sample-derived final size estimate. The user may skip the
sample only by explicitly accepting that the delivery estimate remains a planning
range and editor import remains unverified.

Before any full-duration encode, present the delivery manifest, available disk
space in the approved output folder, sample choice, and target editor. When a
sample exists, show the sample-derived final size estimate. When the sample was
skipped, show the revised planning range and label it as non-final. Ask for
**Step 05 full render authorization**. After encoding, present Alpha, codec,
duration, frame, boundary, checksum, and editor-import evidence as the final
acceptance card.

Before full encoding, confirm disk space and version outputs. After encoding:

- validate the MOV with `scripts/verify_alpha_mov.sh` and decode every frame;
- verify codec, profile, Alpha, dimensions, fps, duration, and frame count;
- inspect start/end and frames around every chapter boundary;
- create the source-video composite preview and multi-background QC;
- calculate a checksum for large deliverables;
- report whether the target editor was actually import-tested.

Do not claim 剪映/CapCut compatibility without an import test or user
confirmation.

## Five-step confirmation policy

Use up to five confirmation checkpoints, one for each risk-bearing decision:

1. material brief;
2. character identity, only when a character was generated or edited;
3. chapter timeline;
4. style, palette, placement, and static preview;
5. delivery manifest and full-render authorization.

At every checkpoint, provide one compact confirmation card with `understood`,
`evidence`, `confirm`, `next`, and `revise` fields. Ask one short question such
as “这份素材简报可以确认吗？” instead of sending a long questionnaire. Record
the answer in `decision-log.json` using the schema in
[references/confirmation-gates.md](references/confirmation-gates.md).

Never continue while a step is `awaiting_user`. Never treat silence, a file
upload, or a button click with an ambiguous label as approval. When the user has
already given an explicit future instruction such as “不要角色、S1 粉色、直接
完整版”, record it as a pre-approved decision, still show the corresponding
checkpoint summary for visibility, and avoid asking the same question again.

On revision, redo only the affected step and invalidate dependent downstream
approvals. Do not restart the whole workflow. Preserve every approved upstream
decision and the original source files.

## Design and animation

Read [references/style-system.md](references/style-system.md) when choosing the
progress-bar pattern, palette, typography, or chapter layout.

Read [references/chapter-analysis.md](references/chapter-analysis.md) when
deriving chapter timing from a video or transcript.

Read [references/character-preparation.md](references/character-preparation.md)
before editing, masking, upscaling, or generating poses from a user-uploaded
character.

Use the neutral editable starting point in
`assets/progress-bar-template.svg` when appropriate. Use
`assets/style-catalog.svg` for a character-free style-selection board. Render
text and UI shapes as vectors at final resolution. Do not upscale a
low-resolution screenshot to simulate 4K.

Keep the primary action legible:

- completed track uses the accent color;
- remaining track uses a low-contrast tint;
- current chapter is the only strongly highlighted label;
- completed and future labels remain readable but quieter;
- character position follows global time unless the user requests chapter jumps.

Derive character placement deterministically from the selected style:

- S1 chapter capsules: `on-edge`, with the feet on the upper progress line;
- S2 segmented runway: `on-edge`, with the feet on the segment baseline;
- S3 text progress: `above-track`, clear of all chapter labels;
- S4 divided label band: `inside-track`, within the active chapter segment.

Do not ask where to place the character. Change this mapping only when the user
explicitly requests an override.

When using `inside-track`, make the band tall enough for the character, reserve
a quiet zone around it, and move or abbreviate nearby text instead of letting
the character cover labels.

For a single generated walking pose, use restrained vertical bob, slight
rotation, and subtle horizontal compression to imply steps while preserving
identity. For an approved generated walk cycle, animate the real frames and
disable fake limb motion. Use the 4-frame playback order `1-2-3-4`. Default to
6 fps for a soft Q-style jog and 8 fps for a brisk walk. Use a faster cadence
only after visual approval. Preserve the user-supplied character’s colors,
proportions, markings, clothing, accessories, outline, and texture. Default to
right-facing movement; mirror only when the progress direction is reversed.

Before approving any character-led layout, run the track-fit checks in
[references/style-system.md](references/style-system.md). Align by the visible
contact foot rather than the PNG canvas edge: the foot must visibly touch the
track or band baseline without a gap, sinking, or transparent-padding offset.
Keep the fill head, character travel anchor, and contact foot on the same
progress coordinate. Reject previews where the character floats above the
track, straddles chapter labels, or visually walks on a different plane.

## Rendering and delivery rules

Read [references/export-and-qc.md](references/export-and-qc.md) before choosing
an Alpha codec or claiming delivery success.

Prefer:

```text
QuickTime MOV
Apple ProRes 4444
codec tag ap4h
yuva444p10le or decoded yuva444p12le
```

Never silently replace an Alpha MOV request with H.264, ordinary HEVC, ProRes
422, black-background video, or VP9 WebM.

Keep source media unchanged. Place intermediate files in a task-specific work
directory. Place user-facing deliverables in the approved output folder; when no
folder was specified, this is the exact directory containing the source video.
Never overwrite an existing deliverable: add a version suffix instead.

## Bundled resources

- `scripts/preflight.py`: reports local dependency, media, output-folder, and
  disk-space readiness before Step 01 approval.
- `scripts/prepare_delivery.py`: reserves a versioned delivery directory after
  Step 01 approval, without overwriting an earlier job.
- `scripts/estimate_export_size.py`: estimates 1080p, 2K, and 4K transparent
  master size ranges from the source duration and fps before Step 01 approval.
- `scripts/verify_alpha_mov.sh`: validate ProRes 4444 Alpha across every frame.
- `scripts/make_multibg_preview.sh`: composite one RGBA PNG over six backgrounds.
- `scripts/split_walk_cycle.py`: split an aligned 4-frame transparent
  sprite sheet, validate Alpha and ground-line consistency, and create an
  animated WebP preview plus manifest.
- `references/style-system.md`: patterns, palettes, typography, and layout rules.
- `references/custom-reference-style.md`: upload-to-manifest rules for adapting a
  user-owned progress-bar reference inside Step 04.
- `references/confirmation-gates.md`: five-step user confirmation cards,
  decision-log schema, dependency invalidation, and retry rules.
- `references/character-preparation.md`: faithful transparent-PNG preparation and QC.
- `references/chapter-analysis.md`: transcript-to-chapter timing rules.
- `references/export-and-qc.md`: codecs, Alpha validation, size, and editor checks.
- `assets/progress-bar-template.svg`: editable neutral vector starting point.
- `assets/style-catalog.svg`: four-style comparison board with neutral character markers.
