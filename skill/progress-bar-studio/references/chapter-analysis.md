# Chapter analysis

## Derive chapters from a source video

1. Probe exact duration and fps.
2. Transcribe speech with timestamps.
3. Mark all semantic nodes without aiming for a predetermined count: hook,
   definition, demonstration, comparison, example, recommendation, recap, and
   call to action.
4. Convert semantic nodes into visible presentation chapters. Merge supporting
   examples, substeps, repeated claims, and intervals shorter than about 8
   seconds into their parent chapter unless a rapid format is intentional.
5. Choose the visible count from content density and final-size readability:
   - for videos up to 180 seconds, normally present 3–5 chapters;
   - 6–7 chapters are allowed when every transition is semantically strong and
     every label remains readable;
   - for longer videos, add chapters only when distinct content sections require
     them. Seven may still be sufficient; there is no duration-derived target or
     fixed upper count.
6. Name chapters with 2–6 Chinese characters or 1–3 short English words.
7. Align chapter changes to the first frame of the new spoken idea.
8. Show the proposed timeline before designing.

Do not divide the video into equal durations when speech provides meaningful
boundaries.

Keep raw `semanticNodes` and visible `chapters` conceptually separate. Never
force three chapters because a reused S1 preset once showed three capsules, and
never expose seven capsules merely because transcription produced seven raw
markers. A preset reuses visual grammar, not the previous video's chapter count.

## Timing manifest

Keep one explicit manifest:

```json
{
  "duration": 120.8,
  "fps": 30,
  "chapters": [
    {"start": 0.0, "label": "开场"},
    {"start": 13.0, "label": "信息雷达"},
    {"start": 40.0, "label": "日报周报"}
  ]
}
```

Validate:

- first chapter starts at zero;
- starts are strictly increasing;
- last start is before duration;
- frame count equals rounded duration × fps as required by the source;
- labels fit at the smallest display size.

## Transition QC

For every boundary, inspect one frame immediately before and one immediately
after it. Confirm:

- only the expected chapter changes highlight;
- the character and completed track remain continuous;
- no one-frame flash, missing label, or stale state appears.
