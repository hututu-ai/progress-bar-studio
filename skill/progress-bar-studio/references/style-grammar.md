# Reference-led visual grammar

For new work, the current selected catalog in assets/selected-styles.json is authoritative.
01/02/08 use full-label auto-grid geometry when needed; 07 is a plain continuous rail with numbered labels,
not hanging flags. The S7/tab descriptions below apply only to older explicit revisions.
New projects default to 4 chapters, allow 3–5, maximum 5. Keep old projects reproducible.

Use this guide when proposing a design, not as a substitute for the creator's approval. The examples are original synthetic demonstrations. Do not extract a person, avatar, logo, brand name or screenshot UI from a layout/color-only reference. A character explicitly supplied as the creator's IP, or explicitly authorized from their private IP library, follows the character workflow instead.

## Read the structure before the color

A reference can express a thin track, generous spacing, small secondary labels, low visual weight, or top-edge attachment. Identify those properties first. Changing only an accent color does not satisfy feedback about a heavy layout. The supplied reference set led to these concrete changes:

- Warm neutral tracks and understated cream, milk-tea, sage and lavender combinations.
- S3: unboxed text, a fine separator between chapters, a small active underline. No chapter-shaped background, heavy solid baseline, or automatic text-color progress line.
- S4: one thin chapter band, continuous true-time fill, fine separators. No separate active pill inside a larger card.
- S7: top-edge hanging tabs, rounded bottoms, a slightly deeper active chapter, Chinese headline with optional small English subtitle.
- Dark navy and cream is a supported alternative demonstrated by the references. Never generalize a rejection of one black line or one loud lime sample into a permanent ban on a color family.

## Built-in forms and the separate custom route

The S1–S7 names below describe native and historical implementations, not a second creator menu. New projects use only the eight public IDs in selected-styles.json; current 07 is thin-rail navigation. Historical routes remain reproducible without being offered as new choices.

A request to follow a different reference is a separate custom-design route. Do not call it S7 or use the number 7 to mean both a built-in and a custom reference. Show the current preview and obtain agreement on the selected geometry before a project sample.

## Palette and proportion

For an actual project, recommend colors that match representative video frames
unless the creator selected an explicit HEX/reference palette or approved reuse.
Read `style-system.md` for color-source priority and evidence checks. This guide
does not implement automatic extraction, and one screenshot cannot establish a
whole video's appearance. Never reuse characters from a color reference.

Offer named starting palettes only as choices: `cream-tea`, `sage`, `lavender`, `navy-cream`. Explicit palette values win over preset values. Keep surface, fill, type, and underline tokens separate. A magenta current title can sit alongside a quiet lavender underline; it does not require magenta everywhere.

At the base 1280-pixel strip, ordinary track height is 5 pixels, S4's no-character band is 44 pixels, and S3's underline is at most 48 pixels long and 2 pixels thick. Output proportions scale with canvas width, with lower readability bounds. New-project titles must remain complete and legible. Use 01/02/08 full-label multi-row layouts when needed; for a compact form propose an accurate shorter label or show an actual alternative preview. Do not accept an ellipsis or a single-character orphan as a layout fix, shrink text endlessly, or change semantic chapter boundaries to make it fit. Historical ellipsis behavior belongs only to explicit old revisions.

The four core styles retain their meaning: S1 low chapter capsules; S2 chapter-aligned runway sections; S3 text navigation; S4 duration-proportional chapter band. S7's current tab is distinguished by depth and text, not by a giant overlay panel.

## Show the real output

Preview the actual renderer's RGBA frame at a chapter boundary and mid-chapter. A comparison board may trim transparent whitespace for presentation, but must not redraw the overlay, disguise output proportions, or replace it with a different mockup. Show portrait and landscape placement at plausible video scale. A decorated web-card grid is not evidence that an overlay works on video.

For development, use a clearly labeled original geometric scene. State that it is a composite illustration, not the user's footage. For a real project, composite the approved overlay onto permitted source frames, inspect faces/subtitles/safe areas and the smallest publishing size, and ask before the next gated stage. A successful synthetic preview or passing test does not count as the creator's visual approval or an editor import test.

## Guardrails that design work must retain

Never change chapter boundaries to make a band look tidy. Preserve half-open boundary timing, actual output PTS, PNG transparency checks, planted-foot anchors, pre-resize allocation checks, no-overwrite behavior, sample/final approval boundaries, and source asset proportions. If a character needs more room than a slim style provides, report the trade-off and ask for a reviewed layout or style choice.
