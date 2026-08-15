# Character preparation

Convert every user-uploaded static character into an approved same-IP walking
pose and transparent PNG before designing or animating the progress bar. The
user should not need to redraw the pose or remove the background manually.

## Preserve the source

- Keep the original uploaded file unchanged.
- Work on a versioned copy.
- Preserve the character's identity, colors, proportions, outline, texture,
  clothing, accessories, and distinctive markings.
- Treat the uploaded image as the identity anchor. Pose and expression may
  change only as needed to create a clean walking or running action.

## Create the walking pose

When the source is static and the selected progress style uses a moving
character, automatically create a walking or light-running version before
background extraction.

- Default to a full-body, three-quarter side view facing right.
- Use a readable locomotion silhouette: one leg forward, one leg back, opposing
  arm swing, and hair, ears, clothing, or tail following the motion.
- Preserve head shape, facial markings, palette, accessories, outline
  thickness, texture, and overall proportions.
- Change a closed-eye, yawning, sitting, or front-facing source into a clear,
  awake, friendly walking expression without redesigning the IP.
- Use the smallest reliable deliverable first: one approved hero walking pose
  plus a restrained bob animation.
- Offer a real walk cycle after the hero pose is approved. When the user
  explicitly requests frame-by-frame walking, go directly to a cycle and
  default to four frames.
- Generate against a flat chroma-key color that is absent from the character,
  then build and verify the Alpha channel separately.
- Show the source and generated pose side by side. If any identity anchor
  drifts, reject the result and retry with targeted constraints.

## Choose the extraction method

Inspect the actual image before choosing a method.

- For a uniform exterior background, prefer a connected-background mask or a
  carefully reviewed segmentation mask.
- Never use a global white colorkey when the character contains white areas.
- For a complex photographic background, use image editing with the uploaded
  image as the reference. Limit the instruction to background removal and edge
  repair.
- If an image edit changes the character, discard it and use a mask-based method.
- If the model returns an opaque image, create the Alpha channel separately.

## Create the canonical PNG

- Export RGBA PNG as `character-walk-transparent.png`.
- Keep the full character, including hair, ears, tail, hands, feet, shadows that
  belong to the artwork, and small accessories.
- Add 8–12% transparent padding around the visible bounds.
- Preserve native resolution. Offer upscaling when the character is too small
  for the requested output, and require approval if upscaling changes linework.
- Keep semi-transparent antialiased edges. Avoid hard jagged cutouts.

## Verify transparency

Do not infer transparency from the filename or file extension.

- Confirm that the PNG contains an Alpha channel and transparent corner pixels.
- Inspect for white or dark halos, missing interior details, transparent holes,
  clipped extremities, colored spill, and opaque background remnants.
- Composite the PNG over white, black, red, blue, brand-color, and checkerboard
  backgrounds using `scripts/make_multibg_preview.sh`.
- Show the transparent PNG and multi-background QC image to the user.
- Obtain approval before using the character in style previews or animation.

## Generated walk-cycle variants

Prefer one horizontal sprite-sheet generation over separate independent image
generations. A single sheet gives the image model one shared canvas and reduces
identity drift. Generate on a flat chroma-key background absent from the
character, remove it from the whole sheet, and then split equal-width cells.

### Four-frame full cycle

Use by default for frame-by-frame walking:

1. left contact;
2. left passing with a subtle body rise;
3. right contact;
4. right passing with a subtle body rise.

Play as `1-2-3-4`. Default to 6 fps for a soft Q-style jog and 8 fps for a
brisk walk. Use a faster cadence only after the loop reads naturally at the
smallest delivery size.

### Frame consistency requirements

- Keep the same canvas size, character scale, ground line, facing direction,
  palette, expression family, outline thickness, lighting, and texture.
- Keep the head and torso nearly fixed in scale; change only limbs, tail, hair,
  clothing follow-through, and a restrained vertical body shift.
- Preserve transparent padding around every frame. Do not auto-trim frames
  independently because that causes visible jitter.
- Reject a sheet if any frame loses markings, accessories, fingers, feet, ears,
  tail details, or clothing elements.
- Reject any frame that turns toward the camera, reverses direction, changes
  proportions, or redraws the IP.
- Show the source, all frames, an animated loop, and multi-background QC before
  progress-bar layout.

### Track-contact preparation

- Record the Alpha-visible bottom and the forward contact-foot anchor for every
  frame; do not use the padded PNG rectangle as the ground reference.
- Keep visible-bottom spread within 0.5% of frame height or 2 pixels, whichever
  is larger. Shift complete frames on a shared canvas when correction is
  needed; never crop or scale frames independently.
- Create a shared-crop layout derivative when large transparent padding makes
  accurate track placement difficult. Preserve the canonical padded frames.
- Verify frames twice: first alone on checkerboard, then with the contact foot
  placed on the actual progress line used by the selected style.
- Reject a cycle when a contact frame has no planted foot, a passing frame looks
  like another long lunge, or the feet appear to skate above the track.

Export:

- `character-walk-frame-01.png` through `character-walk-frame-04.png`;
- `character-walk-spritesheet.png`;
- `character-walk-preview.webp`;
- `character-walk-cycle.json` with frame order, fps, canvas size, and warnings.
