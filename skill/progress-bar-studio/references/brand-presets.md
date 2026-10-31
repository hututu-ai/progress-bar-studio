# Reusable brand presets

Compatibility reference for older schema-4 presets. New opt-in saves should use
[visual-profiles.md](visual-profiles.md) to retain the complete executable visual contract for all eight routes.
The limitations and manual adapter below concern the older format; do not silently rewrite existing files.

A brand preset stores a creator's sample-approved character route, exact style
variant, palette, overlay scale, placement, and optional reference image. For a
walking role it includes the complete four-frame transparent walk-cycle bundle;
for a static role it includes one transparent pose. It is a local, explicit asset
bundle, not hidden memory. The creator chooses whether to save it and whether to
use it later.

## When to ask

After the creator has selected the character route, style route, and palette,
ask one short question about save intent:

```text
要把这套角色、样式和颜色保存成下次可复用的 ElleFlow 预设吗？
```

Ask only after the choices are visible. Never save a character, reference image,
or palette without an explicit yes. Record the preset name at this point, but
write the complete preset only after the actual sample (at most 15 seconds; shorter clips use the whole clip) passes and the creator
authorizes the final master. This delayed write adds no extra creator question.

If the creator chooses to save it, ask for a short preset name and whether it
should become the suggested default. A default is still a suggestion: on a later
project, show its summary and ask whether to use it before copying any assets.

## What is saved

A preset contains:

- character mode and either an opt-in copy of one approved static PNG or the
  four transparent frames, sprite sheet, preview, manifest, frame order, and
  fps of an approved walk cycle;
- S1–S7 or custom-reference style route, its exact approved variant, plus an
  opt-in copy of a reference image;
- approved palette tokens;
- approved overlay scale and placement inside the independent transparent strip;
- schema version, human-readable name, explicit sample/final-export approval
  records, and SHA-256 checksums for the configuration and required assets.

It does not store source videos, transcripts, chapter lists, output folders,
editor-import claims, or any third-party logo/watermark that was removed during
reference adaptation. Chapter count is always content-adaptive and is never
copied from the previous video.

## Save and reuse

Use `scripts/preset_library.py` after opt-in saving, sample approval, and
final-export authorization. The two approval flags are assertions of the actual
recorded creator decisions, not a way to obtain or bypass approval. A sample
waiver cannot create a verified preset. For example:

```bash
python3 scripts/preset_library.py save \
  --name "我的 Vlog 默认风格" \
  --library-dir ~/.elleflow/presets \
  --character-mode walk-cycle \
  --character-cycle-dir /path/to/approved-walk-cycle \
  --style S2 \
  --style-variant "runway" \
  --palette surface=#FFFDFD \
  --palette active=#E89AB3 \
  --palette inactive=#FBE9EE \
  --palette text=#4D3A40 \
  --palette active-text=#382B24 \
  --palette outline=#DAD0C5 \
  --palette shadow=#493D2E08 \
  --overlay-scale 1.0 \
  --placement top \
  --position-x 0 \
  --position-y 32 \
  --sample-approved \
  --final-export-approved \
  --set-default \
  --json
```

A verified preset must include the exact `--style-variant`, at least one
approved `--palette` token, positive `--overlay-scale`, `--placement`, and finite
`--position-x` / `--position-y`. Fill these from the approved render design;
this does not add new questions for the creator. Incomplete configurations must
not qualify for complete reuse.

The script creates a named, self-contained schema-4 preset directory. It refuses
an existing name rather than auto-versioning or overwriting it. A `walk-cycle`
save decodes all four distinct transparent PNGs, the matching sprite sheet, and
the four-frame WebP preview. Frame sizes, preview content/order and frame duration, positive fps, and
manifest references must agree. Only those six images and the manifest are
copied; unrelated files in the source directory are not included. Relative paths
must remain inside the bundle and may not traverse symlinks. Static poses must
also be real transparent PNGs. These checks do not replace visual identity,
edge, baseline, or motion review.

On a later project, inspect the file before offering it:

```bash
python3 scripts/preset_library.py show \
  --preset ~/.elleflow/presets/my-vlog-sop/preset.json \
  --require-verified \
  --json
```

`show` rechecks approval records, required assets, decoded transparency, and
checksums. Only `status: verified` with `reuseEligible: true` qualifies for the
verified quick-reuse card. The default pointer alone is insufficient; inspect
the actual `preset.json` it names. Without `--require-verified`, invalid or older
presets remain inspectable and return `inspectionIssues`; with it, they exit 2.
Schemas 1–3 are always `unverified`, even if old JSON contains a verified label.
Do not silently reuse them. Offer to review their known choices, regenerate or
repair missing assets, then obtain a new sample approval and save under a new
name. Do not overwrite or silently migrate the old file.

Checksums detect missing/changed files and configuration; they are not a
cryptographic signature or proof of human approval. They do not establish target
editor compatibility. The host must keep the actual decision log separately.

Show the preset name, character mode, exact style variant, colors, scale, and
placement. The creator may use the complete bundle, adjust one part, or decline
it. A current video always gets its own chapter analysis, output resolution,
output folder, collision check, and final preview. Reusing the bundle never
reuses the old chapter count.

## Renderer compatibility is a separate check

Schema 4 stores the fields above; it is not a `render_progress.py` config and
cannot recreate every renderer setting automatically. See
[rendering.md](rendering.md#brand-preset--render-config-explicit-manual-adapter)
for the manual mapping, especially palette tokens/alpha, style variants, font,
character height/contact anchors, cycle cadence, and editor placement.

The 0.5 candidate accepts S1–S7 plus `custom`, and both six- and eight-digit HEX
palette values. The schema remains 4; 0.4 readers do not support the added routes
or alpha-valued palette entries. Saving checks storage integrity, not geometry,
contrast or editor compatibility. Validate the resulting renderer config too.

Complete quick reuse requires recovering all relevant visual settings from the
approved design and matching the built-in variant. If required settings are not
stored or cannot be represented, resolve only those fields with a new preview.
Never treat `reuseEligible` alone as an automatic-import or identical-output
promise. Preserve the approved render config with project evidence; schema 4
does not embed it in the reusable asset bundle.
