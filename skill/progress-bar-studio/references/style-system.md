# Progress-bar style system

## Current creator catalog (0.7.4)

Read `assets/selected-styles.json` through `style_router.py catalog --creator-facing`.
It is the only maintained mapping for public IDs, names, visual revisions and progress modes.
Show all eight together: 01 章节胶囊, 02 分段跑道, 07 细轨章节导航, 08 双层胶囊,
10 贯穿章节带, 11 短横线分段, 13 箭头阶梯, 15 点阵进度.
Create new configs with `style_router.py new-config`; do not set one revision for all styles.
New projects default to four chapters, allow three to five, maximum five. Historical projects keep their old counts.
01/02/08 have automatic full-label multi-row layouts with a height fixed before rendering.
Do not shrink or ellipsize a title into one character. Other compact forms may reject long titles;
offer an accurate shorter label or one of these named multi-row alternatives, never obsolete internal IDs.

The following S keys document historical/native renderer forms, not the current public numbering.
S7 with `editorial-20261030` is the current plain thin-rail navigation; hanging tabs below refer only to old revisions.

## Four classic styles, three optional styles, and a separate custom route

### S1 Chapter capsules

Show a content-adaptive number of rounded chapter pills below or inside a track.
Highlight only the current chapter and move the uploaded character along the track. Best for semantic
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

### Optional S5 Current-chapter card

Show the current chapter number and title in a compact card, with a thin total-
progress line. Character placement is a separate horizontal lane above the card.

### Optional S6 Corner ring

Show total progress in a small ring and the current title beside it. An enabled
character follows a separate horizontal lane above the card; it never orbits the ring.

### Optional S7 Top hanging tabs

Attach tabs to the top edge, with rounded lower corners and a slightly deeper
current tab. Optional secondary labels may sit below the headline. An enabled
character uses a lower horizontal lane clear of every tab.

These S keys describe the classic renderer only. The current creator catalog keeps
eight original IDs: 01, 02, 07, 08, 10, 11, 13, 15. Use style_router.py
catalog --creator-facing and assets/style-catalog-selected.png. Show the eight together,
optionally marking one or two recommendations. Retired routes remain for old files only.
`Custom reference` is a separate unnumbered route
for a creator-owned screenshot. It is
never S5, S7 or S8. Read [custom-reference-style.md](custom-reference-style.md)
when selected. Do not collapse all forms into one capsule design.

Use `assets/style-catalog-selected.png` or render a fresh comparison with the approved
palette. The PNG contains actual renderer output with transparent whitespace
trimmed only for presentation. The old SVG is a historical schematic, not the
new renderer's appearance. Read [style-grammar.md](style-grammar.md); cream-tea,
sage, lavender and navy-cream are editable options, not an inferred brand choice.
A chosen structure still needs project-specific palette and placement approval.

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

Show selected swatches and HEX values with the combined dynamic draft. If only
one main color is supplied, derive a proposed complete palette and test contrast
at the smallest display size. A marked unapproved animation is allowed for that
single review; do not insert a separate color-confirmation gate or export final
before the actual combined decision.

## Video-matched palette proposal

The ordinary recommendation is a palette that belongs with the current video,
not a fixed milk-tea, pink or lime scheme. Apply the creator's current explicit
HEX palette or explicitly selected color-reference image first. Explicit reuse
of an approved palette is also a chosen source; do not override it automatically.
A screenshot supplied only for geometry does not silently replace an already
chosen palette. If two explicit sources conflict, ask which colors to use.

When proposing from video, inspect representative frames from the beginning,
major content sections and ending, including brighter/darker scenes and frames
with titles/subtitles. Look for recurring background, graphic, title and subtitle
colors and the overall temperature/saturation. Do not sample primarily skin,
one transient object, a logo, compression noise or a single unrepresentative
frame. A screenshot alone is a reference for that image, not evidence of the
whole video's palette. If the host cannot inspect the video, say so and request
representative stills or the creator's color choice; do not pretend extraction
ran. No automatic extraction script is provided in this package.

Propose a small editable palette, mapping the headline swatches to all renderer
tokens. Make the active state legible and keep text, surface and progress colors
independent. Check contrast and composite the actual overlay over representative
real-video frames at the intended display scale, including light and dark
scenes, subtitles, faces and UI. Adjust only the affected tokens if the design
blends in or competes with content; obtain color and combined-preview approval.

The cream-tea, sage, lavender and navy-cream files are optional starting points
for explicit selection or labeled synthetic demos. Never apply one to every
project. A selected soft-pink reference, for example, may suggest a white
surface, dusty-rose active fill, pale-pink inactive fill and warm dark text, but
these still need project contrast/composite checks. Reference characters are
not palette assets and are never copied automatically.

## Character modes

New user-facing choices are no IP or four-frame walking IP. The following modes describe
legacy asset/placement compatibility, not extra new-user menus:

1. full-body follower or walk-cycle sprite;
2. portrait/avatar sticker at the active edge;
3. object or vehicle icon such as a car, rocket, or mascot;
4. no character.

Placement is part of each style and is not a separate user question. Use:

- S1: `on-edge`;
- S2: `on-edge`;
- S3: `above-track`;
- S4: `inside-track`;
- S5/S6: a horizontal lane above the card;
- S7: a lower horizontal lane clear of the tabs.

Only expose placement as an override when the user explicitly requests one.
For S4, keep the character at
roughly 70–90% of the usable band height and reserve a quiet zone around it.
Never let it cover chapter labels.

Use only a character supplied for this task or actually authorized for reuse
from the current user's private library. Do not silently borrow unrelated
characters or package private IP in the public Skill. Preserve identity, colors,
proportions and facing direction. Use a neutral silhouette in generic catalogs.

## Layout

- Keep the overlay away from existing subtitles, faces, and core demonstrations.
- Use a strip height of roughly 20–28% of its width at design scale only when
  chapter pills are present; use less for a line-only design.
- Keep 2–4% horizontal safe margins.
- Place the character according to the S1–S7 mapping above. Keep ears, hair,
  tail, and limbs inside the encoded
  canvas.
- For new projects use 3–5 visible chapters, default 4 and maximum 5. Group subordinate
  examples and steps into their parent tasks; do not split by equal duration. Old projects remain reproducible.
- Test the smallest final display size, not only the 4K master.

## Track-fit calibration

Treat character-to-track contact as a required layout test, not a decorative
adjustment.

1. Define the style baseline `groundY`: the upper line for S1, the segment
   baseline for S2, the invisible walking plane above labels for S3, and the
   internal band baseline for S4. S5/S6 use the lane above the card; S7 uses the
   clear lower lane.
2. Read the Alpha-visible contact foot from each PNG frame. Do not align using
   the padded image box. Place the visible planted foot at `groundY` with no
   perceptible gap; allow at most 1 design pixel of tolerance.
3. Bind the horizontal walking anchor to the progress coordinate:
   `x = trackStart + progress * (trackEnd - trackStart)`. End the completed fill
   at the same `x`; do not position the fill and character with unrelated
   percentages. With bodyPivotX this is the stable body reference, while each
   frame's visible foot supplies Y; natural alternating foot X need not equal
   the fill endpoint. Without bodyPivotX retain the old explicit foot X. Do not
   silently mix these anchors or modify an approved old project's geometry.
4. Keep the track visually behind or immediately beneath the planted foot. Do
   not let it cut through the torso, tail, or face.
5. Keep a clear character lane that does not cover chapter labels. If the
   selected geometry collides, adjust the proposed layout or offer an actual
   alternative preview; do not silently fade, truncate or remove chapter names.
6. Render contact, passing, and chapter-boundary frames over the real video at
   both master size and smallest display size. Reject floating, sinking,
   moonwalking, label collisions, and canvas-edge clipping.

For preview motion, keep horizontal travel continuous and play the real four
frames independently in `1-2-3-4` order. Choose the slowest cadence that still
reads as walking; 6 fps is appropriate for a soft Q-style jog, while 8 fps is a
friendlier brisk walk. Do not add CSS rotation or fake limb deformation to an
approved real cycle. For long videos where continuous travel would make the
feet visibly skate, walk between chapter anchors during short transition bursts
and idle at the active chapter instead of looping rapidly in place. The bundled
renderer only plays the approved cycle continuously at a fixed cadence; it does
not implement chapter-burst motion or physical foot-locking. If that motion is
required, a separately implemented and reviewed extension is needed. Do not
claim the built-in renderer already provides it.

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
character uploaded for the current task or explicitly authorized saved IP from
the user's private library. Do not borrow unrelated characters or package IP
inside the public Skill. Authorized reuse does not inherit an old video's timing.
