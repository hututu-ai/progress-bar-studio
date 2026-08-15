---
name: progress-bar-studio
description: "Create custom animated chapter progress bars through a five-step workflow: upload media, optionally generate a same-IP single walking pose or 4-frame walk cycle, derive semantic chapters, choose one of four presets or upload a favorite progress-bar reference for a custom style, edit colors, then preview and export transparent assets. Use for video chapter analysis, reference-led progress-bar reconstruction, character-led progress indicators, transparent PNG/WebP frames, sprite sheets, static style previews, and 4K ProRes 4444 MOV overlays for 剪映/CapCut, Premiere, Final Cut, or similar editors."
---

# Progress Bar Studio

Create a reusable animated chapter progress bar that matches the source video,
keeps the user in control through one explicit confirmation at every step, and
exports a genuinely transparent editing asset.

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

## Inputs and defaults

Collect or infer only what is needed:

- source video, or exact duration when no video is available;
- optional chapter labels/timestamps; otherwise derive them from speech;
- character choice: uploaded character or no character;
- when a character is used, animation choice: single-pose light motion or one
  fixed 4-frame cycle;
- one of four preset styles or one uploaded progress-bar reference for a custom
  style, plus an editable palette, HEX value, or palette image;
- target editor, canvas orientation, frame rate, resolution, and output folder.

Do not ask the user to choose frame count or character placement. The only
animation choices are `single` and `four-frame`; the selected style determines
placement. Ask only for genuinely missing choices and infer technical defaults.

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

Default delivery when unspecified:

- a 3840-pixel-wide transparent strip with layout-derived height;
- source frame rate, otherwise 30 fps, and exact source duration;
- ProRes 4444 MOV master with no audio;
- lightweight MP4 composite preview with source audio;
- transparent character PNG or four PNG frames, sprite sheet, animated WebP,
  and cycle manifest when a character is used;
- chapter-transition and multi-background QC images.

Interpret “4K progress bar” as a 3840-pixel-wide strip unless the user requests
a full 3840×2160 or vertical 2160×3840 canvas. Explain that the strip avoids
encoding unused transparent pixels.

## Canonical five-step workflow

### 1. Upload material

Preserve source files unchanged and probe the video with
`scripts/probe_video.sh`. Record dimensions, fps, duration, frame count, audio,
file size, and available disk space. Accept an optional original IP image and
optional palette/reference image in the same step.

Present one material brief containing the exact files, duration, dimensions,
fps, audio, character choice, intended editor, output size, and output folder.
Stop for **Step 01 material approval** before transcription, image generation,
or rendering. Label every inferred technical default as inferred.

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

If no character is used, still show a short no-character summary and obtain
**Step 02 character-mode approval** before deriving chapters. If the user rejects
the character result, regenerate only the character assets; do not re-probe the
video.

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
size is uncertain. The user may explicitly skip the sample and authorize the
full render after approving the static design; record that choice instead of
forcing another gate.

Before any full-duration encode, present the delivery manifest, estimated size,
available disk space, sample choice, and target editor. Ask for **Step 05 full
render authorization**. After encoding, present Alpha, codec, duration, frame,
boundary, checksum, and editor-import evidence as the final acceptance card.

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

Use exactly five confirmation checkpoints, one for each canonical step:

1. material brief;
2. character mode and identity;
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
directory and user-facing deliverables in the task output directory.

## Bundled resources

- `scripts/probe_video.sh`: probe video and available disk space.
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
