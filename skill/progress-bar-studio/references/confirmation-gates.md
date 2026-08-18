# Creator-first confirmation gates

Use this reference with [guided-conversation.md](guided-conversation.md). The
conversation guide controls the creator-facing Step 1-8 cards; this file controls
what must be confirmed, recorded, and regenerated behind those cards.

## Interaction enforcement

Every creator-facing reply must contain exactly one current decision. Use the
matching card from `guided-conversation.md`, headed `进度 X/8`, with 2 to 5
choices. A host may render buttons, but a letter, number, or unambiguous natural-
language answer must work everywhere.

After each choice, repeat the selected value in plain language and then show the
next step. `改一下` and `返回上一步` must return to the smallest relevant
decision. Never treat silence, an upload, or an ambiguous click as approval.

## Required decisions

| Step | Approval needed | Evidence shown before approval | On revision |
| --- | --- | --- | --- |
| 1. Chapters | chapter names and timestamps | semantic chapter draft and transition reasons | rerun only chapter analysis |
| 2. Character | walking, static, plain, or preset route | source/result, edge, baseline, and loop evidence where relevant | rebuild character and later visual work |
| 3. Style | S1-S4 or custom-reference route | visual comparison or adapted reference preview | rebuild later visual work |
| 4. Color | approved palette | no more than four named swatches | rebuild later visual work |
| 5. Preset | save or do not save | exact character, style, and palette summary | affects only future reuse |
| 6. Export | resolution and destination | original-timeline alignment confirmation, estimated size, available space | rerun only export planning |
| 7. Design | complete visual design | real-video still with chapters, role, style, and colors | return to the changed creative step |
| 8. Sample | final export permission | 15-second transparent sample across a chapter boundary | rerun sample and final export only |

## Step-specific rules

### 1. Analysis video and chapters

Treat the uploaded video as a lightweight analysis copy, not the final publishing
asset. Recommend a 720p export from the creator's editing project. It must
preserve the original timeline's duration, aspect ratio, order, and playback
speed. Explain that 480p is a fallback for very long videos or slow networks.

Do not ask about character, style, color, presets, output, or resolution until
the chapter draft is explicitly confirmed. If transcription fails, ask for a
timestamped chapter list. If small on-screen text is unreadable, offer a clear
still, a chapter name supplied by the creator, or proceeding with the current
draft. Never require a high-resolution original by default and never divide a
video into equal lengths.

### 2. Character

The creator chooses `walk-cycle`, `single-pose`, `none`, or an approved preset.
For a character route, preserve identity and show the prepared asset before
continuing. For `none`, record the choice and proceed directly to style.

### 3. Style and color

Show built-in styles visually whenever possible. A custom route requires a
creator-owned reference image and must remove third-party logos, watermarks, and
characters. The palette must remain editable and never silently copy a third
party's treatment as the creator's brand.

### 4. Optional preset

Saving is opt-in. Store only the approved character asset, style route, optional
reference image, and palette. Never store source videos, chapter data, output
folders, or editor-import claims. A future default is a suggestion, never a
silent reuse action.

### 5. Transparent-overlay export

The only standard final delivery is a transparent progress-bar MOV over the
creator's original high-resolution timeline. Do not offer a full composited MP4.
Before rendering, the creator must confirm that the original project and analysis
copy keep the same duration, aspect ratio, clip order, and playback speed.

Then collect resolution and output destination one at a time. Show the planning
range and free space after both values are known. Reserve a versioned final-
delivery directory only after the Step 8 sample is approved; store rejected or
abandoned samples in the task's temporary work area. Do not silently select 4K
or overwrite an existing project.

### 6. Design and sample

The design card must show the selected chapters, role, style, palette, and
resolution in plain language. Only a Step 7 approval can start the 15-second
sample. The sample must cross a real chapter boundary and demonstrate transparency,
character motion where applicable, and likely subtitle/face collisions.

Only a Step 8 approval may start `progress_bar.mov`. If the creator explicitly
skips sample review, mark editor import as unverified and retain only a planning
size range.

## Decision log

Create `decision-log.json` in the task work directory. Record every decision:

```json
{
  "schemaVersion": 5,
  "decisions": [
    {
      "step": 1,
      "name": "chapter-confirmation",
      "status": "awaiting_user",
      "inputs": [],
      "evidence": [],
      "summary": "",
      "userDecision": "",
      "approvedAt": null,
      "nextAction": ""
    }
  ]
}
```

Allowed statuses are `pending`, `working`, `awaiting_user`, `approved`,
`revise`, and `complete`. Do not mark a decision approved without an explicit
creator response. Mark the project complete only after final QC evidence is
delivered.

## Revision rules

| Changed choice | Keep | Revisit |
| --- | --- | --- |
| analysis video or chapters | none unless unchanged | every later step |
| character | analysis video and chapters | style through sample |
| style or color | analysis video, chapters, character | preset, design, sample |
| preset | current project choices | only future reuse behavior |
| output folder or resolution | creative choices | export plan, design, sample |
| sample rejection | every approved upstream choice | sample and final delivery only |

Repair the smallest failing artifact, rerun its evidence, and return to the same
step. Do not restart the whole project because one preview, sample, or encode
failed.
