# Custom reference style

Use this route only during the style decision. It extends style choice without adding a separate creator decision or replacing the four built-in presets.

## Accepted input

Accept one user-owned PNG, JPG, or WebP image that clearly shows a progress bar.
Keep the file unchanged. Reject unreadable thumbnails and ask for a clearer
frame only when the track, labels, or chapter state cannot be distinguished.

## Reconstruction workflow

1. Separate content from style. Ignore example chapter names and identify the
   track, fill, segments or nodes, label system, character or icon anchor,
   typography weight, palette, outline, radius, and shadow.
2. Classify the nearest motion grammar: continuous travel, chapter jumps,
   milestone stops, inside-band travel, or text-only state change.
3. Infer the visible foot or icon baseline and choose placement from the
   reference. Do not ask the user where the character should sit.
4. Replace source labels with the approved presentation chapters. Re-space the
   design for the current content-adaptive count; shorten labels or merge
   subordinate nodes before shrinking text.
5. Apply the current-task character only when enabled. Remove or replace any
   character, logo, portrait, watermark, or brand mark contained in the source.
6. Rebuild lines, pills, labels, dividers, and fills as vectors at final size.
   Never upscale the screenshot and call it a 4K overlay.
7. Show one transparent reconstruction over the analysis video, then make the
   creator check its safe placement in the original high-resolution editing project before full export.
   Run the same track-fit, collision, contrast, and multi-background checks used
   by the presets, then obtain visual approval.

## Style manifest

Record at least:

```json
{
  "mode": "custom-reference",
  "referenceFile": "favorite-progress-bar.png",
  "pattern": "segmented-runway",
  "placement": "on-edge",
  "motion": "continuous-travel",
  "palettePolicy": "adapted-from-reference",
  "replacedElements": ["example labels", "source mascot"],
  "notes": "Rebuilt as vectors and fitted to approved chapters"
}
```

Use `palettePolicy: project-palette` when the user wants their chosen colors.
If no preference is stated, extract the reference palette, show the derived four
swatches, and keep every value editable.

## Boundaries

- Recreate structure and visual grammar, not exact protected artwork.
- Never preserve third-party characters, faces, logos, or watermarks.
- Never claim the uploaded screenshot itself is transparent or production-ready.
- Never add a separate custom-style decision. Custom output uses the combined design preview and the sample/full-export authorization from the creator-first confirmation policy.
