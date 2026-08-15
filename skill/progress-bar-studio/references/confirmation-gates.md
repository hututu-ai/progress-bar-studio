# Five-step confirmation gates

Use this reference before running a Progress Bar Studio project. The purpose is
to keep the workflow collaborative without restarting approved work or asking
the user unnecessary questions.

## Contents

1. Confirmation card
2. Five checkpoint definitions
3. Decision log
4. Dependency and retry rules
5. Communication rules

## Confirmation card

At the end of every step, send one compact card with these fields:

```text
Step: 01 / Material brief
Understood: what Codex believes the user wants
Evidence: files, probe results, preview, or QC created in this step
Confirm: the one decision the user must approve
Next: the exact work that starts after approval
Revise: what can be changed without restarting upstream work
Question: one short confirmation question
```

Keep the question singular. Place additional editable details in the card, not
as several separate questions. If one missing choice would materially change
the result, ask it before producing the card.

## Five checkpoint definitions

### Step 01 - Material brief

Show the exact source filenames and preserved originals; video duration,
dimensions, fps, audio, and file size; optional character, palette, and style
reference; target editor, orientation, output width, fps, output folder, and
inferred defaults.

Confirm the source and delivery brief. Do not start transcription, image
generation, or media rendering before this approval.

### Step 02 - Character mode and identity

For `no-character`, show the recorded choice and confirm that all styles will be
character-free.

For `single` or `four-frame`, show the original and generated assets side by
side; identity anchors; Alpha, multi-background, edge, foot-baseline, and loop
evidence; chosen animation mode and playback order.

Confirm character mode and identity fidelity. On rejection, regenerate or
repair only character assets.

### Step 03 - Chapter timeline

Show transcript-derived chapter starts and 2-6-character labels, one short
semantic reason for each transition, strict time ordering and the zero start,
plus any uncertainty or merged short sections.

Confirm the editable timeline. Do not render style previews before this
approval.

### Step 04 - Style and visual fit

Show the chosen S1-S4 preset or custom-reference structure manifest, editable
palette and contrast, deterministic character placement and foot-to-track
alignment, static transparent preview, real-video composite, collision check,
and multi-background QC. For custom references, list removed third-party
elements.

Confirm style, palette, placement, and static composition. Do not animate the
full video before this approval.

### Step 05 - Delivery and render authorization

Before rendering, show exact output files, dimensions, fps, duration, codec,
estimated size, available disk space, output version, target editor, and whether
a 15-second sample is needed or explicitly skipped.

Confirm full-duration render authorization. After rendering, show final
acceptance evidence: decoded Alpha, codec/profile, duration/frame count, chapter
boundaries, checksum, preview, and actual editor import status.

## Decision log

Create `decision-log.json` in the task work directory. Keep one entry per step:

```json
{
  "schemaVersion": 1,
  "steps": [
    {
      "step": 1,
      "name": "material-brief",
      "status": "awaiting_user",
      "inputs": [],
      "outputs": [],
      "summary": "",
      "userDecision": "",
      "approvedAt": null,
      "nextAction": ""
    }
  ]
}
```

Allowed statuses are `pending`, `working`, `awaiting_user`, `approved`,
`revise`, and `complete`. Do not mark a step `approved` without an explicit user
decision. Mark Step 05 `complete` only after final QC evidence is delivered.

## Dependency and retry rules

| Revised decision | Keep approved | Invalidate |
| --- | --- | --- |
| Step 01 source video or output spec | none unless unchanged | Steps 02-05 as affected |
| Step 02 character mode or identity | Step 01 | Steps 04-05; keep Step 03 when video content is unchanged |
| Step 03 chapters or timestamps | Steps 01-02 | Steps 04-05 |
| Step 04 style, palette, or placement | Steps 01-03 | Step 05 |
| Step 05 output path or codec only | Steps 01-04 | Step 05 render authorization |

If a failure is technical rather than a user decision, repair the smallest
failing artifact, rerun its QC, and return to the same checkpoint. Never restart
the whole workflow merely because one preview or encode failed.

## Communication rules

- Lead with the current result and the one decision required.
- Keep progress updates separate from approval questions.
- Explain inferred defaults and uncertainty; do not present them as user choices.
- Record explicit pre-approvals and do not ask the same question twice.
- Do not run a costly or long operation while `awaiting_user`.
- If the user revises an approved choice, state which downstream approvals were
  invalidated before continuing.
- At handoff, report the verified layer: configuration, preview, rendered file,
  Alpha QC, and editor import are separate claims.
