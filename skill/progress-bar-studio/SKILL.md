---
name: progress-bar-studio
description: "Create ElleFlow animated chapter progress bars for long or short videos, Vlogs, knowledge videos, and video series. Creators can upload a recommended 720p analysis copy to confirm chapters, choose a walking IP character or a plain bar through one clear Step 1-8 choice at a time, select a style and color, optionally save a reusable preset, and receive a high-resolution transparent ProRes 4444 MOV to align over their original video in an editor. Use for lazy, no-keyframe chapter progress-bar creation, character-led progress indicators, reusable creator SOP presets, transparent PNG/WebP frames, and ProRes 4444 MOV overlays."
metadata:
  version: "0.3.0"
  compatibility: "Requires local file access plus ffmpeg, ffprobe, and Python 3. Pillow is needed for four-frame character cycles. Transcription, image editing, and editor-import testing depend on the host."
---

# ElleFlow｜小人走路视频进度条动画

Create a chapter progress bar for any long or short video, Vlog, knowledge
video, or video series. ElleFlow uses a lightweight analysis copy to understand
content and draft chapters, then delivers a high-resolution transparent progress
bar for the creator to place over the original project in an editor. This keeps
large original videos local and avoids hand-marking timecodes or keyframes.

## First-run onboarding

On the first turn after the Skill is invoked, when the creator has not supplied
a usable source video or a concrete editing request, send a short welcome
message before explaining any workflow. Lead with what the creator can send
next. Do not surface internal terms such as Alpha, ProRes, manifests, QC, or
workbench in this message. Do not start media processing until a video is
provided.

Reply in the creator's language. For a Chinese-speaking creator, use:

```text
ElleFlow｜小人走路视频进度条动画

先选你现在的情况：

A. 我已经有一份 720p 分析版，直接上传
B. 我有剪映工程，但不知道怎样导出分析版
C. 我想先看看成品会是什么样

回复 A、B 或 C 就行。
```

When a video is supplied, acknowledge it and read
[guided-conversation.md](references/guided-conversation.md) before sending any
creator-facing reply. Follow its Step 1-8 cards exactly. Keep implementation
details out of the opening response unless the creator asks for them.

## Mandatory interaction contract

The host may render buttons, menus, or plain text, but the conversation must work
without platform-specific controls:

- show one decision per reply, headed `进度 X/8`;
- give a short title, no more than two explanatory sentences, and 2 to 5
  lettered or numbered choices;
- render the same choices as buttons when the host supports buttons; otherwise
  let the creator reply with the letter, number, or natural language;
- acknowledge the selected choice in plain language before presenting the next
  step;
- always accept `改一下` or `返回上一步` and return only to the relevant step;
- never dump later-step options, codec settings, dimensions, filesystem paths,
  or implementation vocabulary into a current decision.

The required card wording, natural-language mapping, revisions, and recovery
paths are in [guided-conversation.md](references/guided-conversation.md).

For a returning creator, inspect the default preset before asking any new
visual questions. If it exists, make the first Step 1 decision a one-question
offer to reuse the complete approved bundle: character, animation mode, exact
style variant, palette, size, scale, and placement. Reuse never carries forward
the old video's chapters, timing, source, output folder, or render approval.

## Creator-first order

Follow this order. Do not move output folder, resolution, or file-size questions
into the first creative conversation.

1. **Read video**: accept or help the creator export a 720p analysis copy. When
   a valid default preset exists, first ask whether to reuse its complete visual
   bundle. Then probe it internally, derive an editable chapter draft, and show
   the chapter-confirmation card.
2. **Confirm chapters**: let the creator accept, edit, or reanalyse the draft
   before any visual choice.
3. **Choose character**: offer walking character, light-motion character, plain
   progress bar, or an approved preset through one choice card.
4. **Choose style**: show S1-S4 visually where possible, plus one custom-
   reference route.
5. **Choose color**: let the creator choose video-derived color, palette image,
   named color, or an ElleFlow recommendation.
6. **Save preset**: offer an optional preset name after character, style, and
   color are approved; write it only after the final design confirms size,
   scale, and placement.
7. **Choose transparent export**: confirm the original timeline still matches
   the analysis copy, then ask for resolution and output folder in separate
   choice cards. Detect the source orientation internally; do not make the
   creator calculate a canvas ratio.
8. **Review and export**: show the combined design, make a 15-second transparent
   sample after approval, then export the final MOV only after the sample passes.

Treat each decision as one short, focused question. Do not ask the creator to
choose frame count or character placement: the selected style determines both.
Do not start a costly render while a decision is awaiting approval.

## Lightweight analysis copy and chapter confirmation

The uploaded video is an analysis copy, not the final publishing asset. Recommend
`720p` because it keeps uploads manageable while retaining enough detail for
most Vlogs, talking-head clips, knowledge videos, and series content. `480p` is
a fallback for very long videos or slow networks, not the default recommendation.

Before upload, tell the creator:

```text
建议从剪映导出 720p 轻量分析版。它只用于理解内容和做章节，不会替代你的高清原片。
请在剪辑内容定稿后导出，并保持和原工程相同的时长、画面比例和播放速度；之后把高清透明进度条从视频开头对齐拖回原工程即可。
```

Preserve source files unchanged. Run
`scripts/preflight.py --source-video <analysis-video> --json` after receiving
the video; an unselected output folder is a warning at this point, not a blocker.
Probe dimensions, fps, duration, audio, and file size internally. Read
[chapter-analysis.md](references/chapter-analysis.md), make an editable chapter
draft with real semantic turns, show it to the creator, and ask whether the
chapter names and boundaries are correct. Never divide a video into equal
durations.

Detect semantic nodes first, then choose visible presentation chapters. For
videos up to 3 minutes, normally use 3–5 chapters; use 6–7 only when the content
has that many strong, distinct turns and the final labels remain readable.
Longer videos may use more according to content density. Never reuse a saved
preset's previous chapter count.

Only when the source truly cannot be transcribed should you explain the
limitation and request a timestamped chapter list. If the content depends on
small on-screen text, slides, code, or tables that the analysis copy cannot
reliably show, ask for a clear still or the relevant chapter names. Do not ask
all creators for a high-resolution source by default.

Do not ask about characters, style, colors, output folder, or resolution until
the creator has confirmed or revised the chapter draft.

## Character decision

Offer exactly these paths:

- `none`: a clean progress bar with no character;
- `single-pose`: one explicitly approved character PNG with light motion;
- `walk-cycle`: an explicitly approved four-frame walking character.

If the creator selects `none`, record the choice and continue directly to style.
Do not show a content-free character approval card.

Treat `none` as a render invariant. Do not load or pass any character asset into
style cards, the combined preview, sample, transparent master, or delivery
package. Before delivery, inspect at least one preview frame and one decoded
master frame to confirm that no added character pixels remain.

For a character path, read
[character-preparation.md](references/character-preparation.md). Preserve the
uploaded character's identity, colors, proportions, markings, clothing,
accessories, outline, and texture. Use image editing with the uploaded source as
the identity reference. Reject any result that redesigns the IP.

For a four-frame cycle, create one aligned sprite sheet, prepare real RGBA PNGs,
and split it with `scripts/split_walk_cycle.py`. Show the source, output, loop,
foot baseline, and multi-background edge check. Obtain explicit approval before
using that character in a combined preview.

Never silently reuse a character from another project. A saved preset is the
only reuse route, and its complete contents must be shown and approved for the
current video.

## Style and color decision

Read [style-system.md](references/style-system.md). Show these four built-in
routes on a simple comparison board:

1. S1 chapter capsules;
2. S2 segmented runway;
3. S3 text progress;
4. S4 divided label band.

Also show `Custom reference` as a separate route. When selected, read
[custom-reference-style.md](references/custom-reference-style.md), accept one
creator-owned PNG, JPG, or WebP reference, and extract its layout logic. Do not
reproduce third-party logos, watermarks, copyrighted characters, or exact
proprietary artwork.

Character placement is determined by the chosen route:

- S1: on the upper progress-line edge;
- S2: on the segment baseline;
- S3: above the track, clear of labels;
- S4: inside the active band.

Do not ask the creator to decide placement unless she explicitly requests an
override.

## Color decision

Ask for one of these inputs:

- a HEX value or a named color;
- a palette image or brand card;
- a still from the creator's video;
- permission to propose a palette from the chosen custom reference.

Extract or derive a small editable palette containing main, light surface, deep
accent, and text colors. Show the swatches with HEX values before approval. Do
not silently default every project to pink, and do not copy a third party's logo
or proprietary color treatment as if it belongs to the creator.

## Reusable ElleFlow presets

After the character, exact style variant, palette, size, scale, and placement
are approved, ask:

```text
要把这套角色、样式和颜色保存成下次可复用的 ElleFlow 预设吗？
```

On an explicit yes, ask for a preset name and whether it should be the suggested
default. Use `scripts/preset_library.py` to save a self-contained local preset
with copies of only the approved character and reference assets plus the exact
visual configuration. It never overwrites an existing preset.

On a later project, inspect a supplied or discovered default preset before the
new video's chapter card. Show its character mode, exact style variant, palette,
size, scale, and placement, then ask whether to reuse the complete bundle. The
creator can reuse it, revise one field, or decline it. Complete reuse pre-approves
the saved visual decisions after file and real-video collision checks, so do not
ask the same character, style, color, size, or placement questions again. A
preset never carries forward source videos, chapters or chapter count, output
folders, file-size claims, or editor-import claims.

## Transparent-overlay delivery decision

Only after creative choices are approved, ask for the output resolution and
output folder in separate choice cards. Detect the analysis video's orientation
and canvas ratio internally; do not ask a novice to calculate or type it. The default and only standard final delivery is a transparent
progress-bar MOV that the creator places over the original high-resolution video
in an editor. Do not offer to re-encode the creator's full video or claim to
deliver a finished composited MP4.

Confirm that the creator will use the same final timeline as the analysis copy:

```text
这条高清透明进度条会按当前视频的时长和章节时间点制作。
请确认：你的高清原工程与上传的分析版时长、画面比例和播放速度一致；后续只需从视频开头把进度条对齐拖进去。
```

If no folder is specified, propose the analysis-video folder as an inferred
default. If no resolution is specified, show all three options and recommend
one; never silently default to 4K.

The following pixel widths are technical planning values for the transparent
strip, not extra choices the creator must understand. Detect source orientation
internally and include it in the export plan:

- 1080p: 1920-pixel-wide transparent strip;
- 2K: 2560-pixel-wide transparent strip;
- 4K: 3840-pixel-wide transparent strip.

Run:

```text
scripts/preflight.py --source-video <analysis-video> --output-dir <output-folder> --json
scripts/estimate_export_size.py <analysis-video> --output-dir <output-folder>
```

Only after the Step 8 sample approval, reserve the final delivery directory:

```text
scripts/prepare_delivery.py --source-video <analysis-video> --output-dir <output-folder> --character-mode <approved-mode> --sample-approved --json
```

Before that, keep samples in the task's temporary work area so a rejected or
abandoned design does not leave an empty delivery folder.

## Combined preview

Create a representative frame over the real analysis video and a transparent
overlay preview. Show them together with:

- the editable chapter list and exact timestamps;
- the approved character or explicit no-character choice;
- the style route, color swatches, and any custom-reference adaptation notes;
- subtitle, face, UI, and chapter-label collision checks;
- white, black, red, blue, brand-color, and checkerboard composites.

Read [style-system.md](references/style-system.md) for track-fit rules. Align a
character's visible contact foot with the progress coordinate; reject previews
where it floats, sinks, or blocks chapter labels. Do not animate the full video
until the creator approves this combined preview.

## 15-second sample and final delivery

Read [export-and-qc.md](references/export-and-qc.md). Render a 15-second
transparent sample using the approved settings and crossing a chapter boundary.
Show its actual size, Alpha result, and target-editor import status when tested.

Only after the creator approves the sample may the final transparent master be
rendered as `progress_bar.mov`. Do not include a full-length `preview.mp4` as a
default deliverable. If the sample is skipped by explicit creator choice, show
only a planning size range, label editor import as unverified, and do not call
the estimate final.

For the final transparent master, prefer QuickTime MOV, Apple ProRes 4444,
`ap4h`, and `yuva444p10le` or decoded `yuva444p12le`. Never silently replace an
Alpha MOV request with H.264, ordinary HEVC, ProRes 422, or a filled-background
video.

After encoding:

- validate the MOV with `scripts/verify_alpha_mov.sh` and decode every frame;
- verify codec, profile, Alpha, dimensions, fps, duration, and frame count;
- inspect start, end, motion, and every chapter boundary;
- create multi-background QC;
- calculate a checksum for large deliverables;
- state whether the target editor was actually import-tested.

## Confirmation and revision policy

Use a compact confirmation card for each risk-bearing choice. Include
`understood`, `evidence`, `confirm`, `next`, and `revise`, then ask one short
question. Record explicit choices in `decision-log.json`.

Keep approved upstream choices when a creator changes one thing. A complete
Step 1 preset-reuse answer may mark the corresponding later decisions approved
with `approvalSource: step1-reuse-preset`; do not turn them into repeated user
stops.

| Changed choice | Keep | Revisit |
| --- | --- | --- |
| analysis video or chapter list | none unless unchanged | every later decision |
| character | analysis video and chapter draft | style preview, sample, full export |
| style or color | analysis video, chapter draft, character | combined preview, sample, full export |
| preset | current project choices | only future reuse behavior |
| output folder or resolution | creative choices | size check, sample, full export |

Repair the smallest failing artifact and return to the relevant decision. Never
restart the whole project because one preview or encode failed.

## Bundled resources

- `scripts/preflight.py`: dependency, analysis-video, output-folder, and disk-space checks.
- `scripts/estimate_export_size.py`: 1080p, 2K, and 4K transparent-export planning ranges.
- `scripts/prepare_delivery.py`: reserves a versioned final-delivery directory after sample approval.
- `scripts/preset_library.py`: explicit save and inspection of creator presets.
- `scripts/verify_alpha_mov.sh`: ProRes 4444 Alpha validation across every frame.
- `scripts/make_multibg_preview.sh`: RGBA compositing over six backgrounds.
- `scripts/split_walk_cycle.py`: four-frame splitting, baseline validation, and WebP preview.
- `references/chapter-analysis.md`: content-to-chapter timing rules.
- `references/character-preparation.md`: faithful character preparation and QC.
- `references/style-system.md`: style, palette, placement, and track-fit rules.
- `references/custom-reference-style.md`: custom-reference adaptation rules.
- `references/guided-conversation.md`: required Step 1-8 creator cards, choices, revisions, and recovery paths.
- `references/brand-presets.md`: save and reuse rules for creator presets.
- `references/export-and-qc.md`: codecs, sample rules, Alpha, and editor checks.
- `assets/progress-bar-template.svg`: editable neutral vector starting point.
- `assets/style-catalog.svg`: four-style comparison board.
