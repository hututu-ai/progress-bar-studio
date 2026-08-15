# Progress-bar style system

## Four preset styles and one custom route

### S1 Chapter capsules

Show 4–7 rounded chapter pills below or inside a track. Highlight only the current
chapter and move the uploaded character along the track. Best for semantic
navigation and friendly personal-brand videos. Fixed character placement:
`on-edge`, with the feet on the upper progress line.

### S2 Segmented runway

Use separated dashes or blocks and move the uploaded character from segment to
segment. Best for retro, pixel, skeleton, mechanical, or playful character styles.
Fixed character placement: `on-edge`, with the feet on the segment baseline.

### S3 Text progress

Show chapter names in one line separated by dividers. Recolor completed,
current, and future states; the uploaded character may sit above the current
label. Best when vertical space is limited. Fixed character placement:
`above-track`, clear of every label.

### S4 Divided label band

Use one full-width soft band divided by vertical separators. Put chapter labels
inside the band and position the uploaded character, avatar, car, or icon inside
the active segment. Reserve a quiet area so it does not cover the label. Best
when the chapter names must stay readable at small size. Fixed character
placement: `inside-track`, within the active chapter segment.

The previous thin step line, framed loading bar, milestone nodes, partitioned
bracket track, dual-layer chapter track, and text-embedded progress bar are not
part of the default catalog. Always show these four styles when the user asks
to compare presets. Also show one separate `Custom reference` route that accepts
a user-owned progress-bar screenshot. Do not relabel it S5 or treat it as a
fifth preset. Read [custom-reference-style.md](custom-reference-style.md) when it
is selected.
Do not collapse them into one capsule design. Combine at most two patterns after
the user selects them.

For the default four-style comparison board, use pure-white cards (`#FFFFFF`)
for S1–S4 and the lime/black/white product palette as an editable example.
Highlight only the selected card with a light accent surface. The accent palette
shown in the board is a demonstration and must remain editable.

## Custom color system

Do not hard-code pink as the final palette. Accept any of:

- exact HEX values;
- an uploaded color-card image;
- a screenshot or visual reference;
- one main color from which a tint family can be proposed.

Map every design to these editable tokens:

- `surface`: the card, band, or pill background;
- `active`: completed track and current highlight;
- `inactive`: future track and inactive labels;
- `text`: normal chapter text;
- `active-text`: text on the active fill;
- `outline`: optional borders and dividers;
- `shadow`: optional shadow or glow.

Show the selected swatches and HEX values at the static-preview gate. If only
one main color is supplied, derive lighter and darker variants, then wait for
approval before rendering animation. Check text contrast at the smallest target
display size.

## Character modes

The user defines the character for each project. Support four modes:

1. full-body follower or walk-cycle sprite;
2. portrait/avatar sticker at the active edge;
3. object or vehicle icon such as a car, rocket, or mascot;
4. no character.

Placement is part of each style and is not a separate user question. Use:

- S1: `on-edge`;
- S2: `on-edge`;
- S3: `above-track`;
- S4: `inside-track`.

Only expose placement as an override when the user explicitly requests one.
For S4, keep the character at
roughly 70–90% of the usable band height and reserve a quiet zone around it.
Never let it cover chapter labels.

Never reuse or package a character from another task. Preserve the uploaded
asset’s identity, colors, proportions, and facing direction. Use a neutral
character silhouette in generic catalogs.

## Layout

- Keep the overlay away from existing subtitles, faces, and core demonstrations.
- Use a strip height of roughly 20–28% of its width at design scale only when
  chapter pills are present; use less for a line-only design.
- Keep 2–4% horizontal safe margins.
- Place the character according to the fixed S1–S4 mapping. Keep ears, hair,
  tail, and limbs inside the encoded
  canvas.
- Use 4–7 chapters. Shorten labels before shrinking text.
- Test the smallest final display size, not only the 4K master.

## Track-fit calibration

Treat character-to-track contact as a required layout test, not a decorative
adjustment.

1. Define the style baseline `groundY`: the upper line for S1, the segment
   baseline for S2, the invisible walking plane above labels for S3, and the
   internal band baseline for S4.
2. Read the Alpha-visible contact foot from each PNG frame. Do not align using
   the padded image box. Place the visible planted foot at `groundY` with no
   perceptible gap; allow at most 1 design pixel of tolerance.
3. Bind the horizontal contact-foot anchor to the progress coordinate:
   `x = trackStart + progress * (trackEnd - trackStart)`. End the completed fill
   at the same `x`; do not position the fill and character with unrelated
   percentages.
4. Keep the track visually behind or immediately beneath the planted foot. Do
   not let it cut through the torso, tail, or face.
5. Reserve a character-width quiet zone around the moving anchor. Move,
   abbreviate, or temporarily fade nearby labels instead of covering them.
6. Render contact, passing, and chapter-boundary frames over the real video at
   both master size and smallest display size. Reject floating, sinking,
   moonwalking, label collisions, and canvas-edge clipping.

For preview motion, keep horizontal travel continuous and play the real four
frames independently in `1-2-3-4` order. Choose the slowest cadence that still
reads as walking; 6 fps is appropriate for a soft Q-style jog, while 8 fps is a
friendlier brisk walk. Do not add CSS rotation or fake limb deformation to an
approved real cycle. For long videos where continuous travel would make the
feet visibly skate, walk between chapter anchors during short transition bursts
and idle at the active chapter instead of looping rapidly in place.

## Hierarchy

1. Current chapter or moving uploaded character.
2. Completed track.
3. Chapter labels.
4. Remaining track and surface decoration.

Avoid a second high-saturation element that competes with the current chapter.

## Optional palette presets

### Cream pink

- canvas/background: `#FBEAF0`
- surface: `#FFFDFD`
- inactive pill: `#FBE9EE`
- remaining track: `#F7DDE5`
- active/completed: `#E89AB3`
- text: `#4D3A40`
- deep accent: `#C9698B`
- active text: `#FFFDFC`

### Paper red

- canvas: `#EEE9E3`
- surface: `#F8F4EF`
- remaining: `#FFFFFF`
- active/completed: `#C95345`
- text: `#4A3D38`

### Dark neon

- canvas: transparent or `#101012`
- surface: `#1A1A1F`
- remaining: `#303038`
- active: `#F2AFC8`
- secondary accent: `#9FE4E5`
- text: `#F9F6FA`

### Fresh loading

- canvas: `#FCE8B9`
- surface: `#FFFDFC`
- remaining: `#FFFFFF`
- active: `#B9D59C`
- outline: `#F08EAB`
- text: `#77966D`

These presets are starting points only. Adapt colors to the video before using
a preset. Match hue temperature,
saturation, surface radius, typography, and shadow language across the entire
video.

## Typography

- Prefer one rounded sans-serif family for labels.
- Use medium or semibold weight.
- Use dark warm gray instead of pure black in soft palettes.
- Use white text only when the active fill has sufficient contrast.
- Avoid rough handwritten type beside clean UI cards unless the whole design
  intentionally uses a hand-made visual language.

## Reference-image policy

Use reference images for pattern, spacing, motion, and palette direction. Do not
copy third-party copyrighted characters, logos, or exact artwork. Use only the
character uploaded for the current task. Do not reuse a character from another
task or package it inside the Skill.
