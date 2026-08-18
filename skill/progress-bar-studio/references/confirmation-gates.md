# Creator-first confirmation gates

Use this reference for an ElleFlow project. The creator first confirms what the
lightweight analysis video says, then decides character, style, color, and
transparent-export settings. A 15-second transparent sample must be reviewed
before the full export.

## Confirmation card

At each risk-bearing decision, send one compact card:

```text
Decision: what is being chosen now
Understood: what ElleFlow heard
Evidence: chapter draft, selected asset, swatches, preview, or sample
Confirm: the one choice that needs approval
Next: exactly what will happen after approval
Revise: what can change without restarting the project
Question: one short question
```

Never use silence, a file upload, or an ambiguous button click as approval.

## Decision order

### 1. Analysis video and chapter confirmation

Treat the uploaded video as a lightweight analysis copy, not the final publishing
asset. Recommend a 720p export from the creator's editing project. It should
preserve the original timeline's duration, aspect ratio, order, and playback
speed. Explain that 480p is a fallback for very long videos or slow networks.

Derive an editable chapter draft from the actual content. Show chapter names,
timestamps, and short transition reasons. Ask the creator to confirm or revise
this draft before asking about characters, style, color, output, or resolution.

Only if the source cannot be transcribed should ElleFlow explain that limitation
and ask for a timestamped chapter list. If slides, code, tables, or other small
on-screen text cannot be read from the analysis copy, request a clear still or
the relevant chapter names. Do not require the high-resolution original by
default and never divide a video into equal lengths.

### 2. Character route

Ask whether the creator wants no character, a single light-motion character, or
a four-frame walk cycle. For a character route, request an IP image, turn it
into the approved walking asset, then show the source and result with edge,
baseline, and loop evidence. For no character, record the choice and continue
without a content-free confirmation.

### 3. Style and color route

Show S1-S4 and one `Custom reference` route. A custom route requires a
creator-owned reference image and must remove third-party logos, watermarks, and
characters. Then ask for a color, HEX, palette image, video still, or permission
to propose a palette from the selected reference. Show editable main, surface,
accent, and text swatches with HEX values.

### 4. Optional reusable preset

After character, style, and color are approved, ask whether to save that
combination as a named local preset. Saving is opt-in. A saved default is only a
future suggestion: show it and ask before reuse.

### 5. Transparent-overlay export

Ask for the output folder and 1080p/2K/4K resolution. Explain that ElleFlow
will deliver a high-resolution transparent MOV, which the creator places over
the original high-resolution editing project from timecode `00:00`.

Before export, ask the creator to confirm that the analysis copy and original
project have the same duration, aspect ratio, clip order, and playback speed.
Use the actual output folder to show available disk space and planning size
ranges. Once approved, reserve a versioned delivery directory. Do not silently
select 4K or overwrite an existing project.

### 6. 15-second sample review

Render a 15-second transparent MOV sample crossing a chapter boundary. Show:

- `sample_progress_bar.mov` for transparency, timing, and chapter-transition inspection;
- actual sample size and Alpha result;
- target-editor import status when tested.

Ask whether this sample is approved for the final transparent export. A creator
may explicitly skip it only after accepting that the file-size estimate remains
a planning range and editor import is unverified.

### 7. Final delivery

Only after sample approval may `progress_bar.mov` be rendered. Do not offer a
finished composited MP4: re-encoding the full original video adds upload time,
positioning ambiguity, and another edit round. The creator keeps the original
high-resolution project and aligns the transparent master from its start.

After full export, show codec/profile, Alpha scan, dimensions, fps, duration,
chapter-boundary check, checksum, and actual editor-import status. A long
`preview.mp4` is not a default final file.

## Decision log

Create `decision-log.json` in the task work directory. Record every decision:

```json
{
  "schemaVersion": 4,
  "decisions": [
    {
      "order": 1,
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
| analysis video or chapters | none unless unchanged | every later decision |
| character | analysis video and chapters | style preview, sample, final delivery |
| style or color | analysis video, chapters, character | preset choice, sample, final delivery |
| preset | current project choices | only future reuse behavior |
| output folder or resolution | creative choices | size check, sample, final delivery |
| sample rejection | every approved creative and export choice | sample and final delivery only |

Repair the smallest failing artifact, rerun its evidence, and return to the same
decision. Do not restart the whole project because one preview, sample, or encode
failed.
