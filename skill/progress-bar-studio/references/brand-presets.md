# Reusable brand presets

A brand preset stores a creator's approved character route, exact style variant,
palette, canvas size, overlay scale, placement, and optional reference image. It
is a local, explicit asset bundle, not hidden memory. The creator chooses whether
to save it and whether to use it later.

## When to ask

After the creator has selected the character route, style route, and palette,
ask one short question about save intent:

```text
要把这套角色、样式和颜色保存成下次可复用的 ElleFlow 预设吗？
```

Ask only after the choices are visible. Never save a character, reference image,
or palette without an explicit yes. Record the preset name at this point, but
write the complete preset only after the final design confirms size, scale, and
placement. This delayed write adds no extra creator question.

If the creator chooses to save it, ask for a short preset name and whether it
should become the suggested default. A default is still a suggestion: on a later
project, show its summary and ask whether to use it before copying any assets.

## What is saved

A preset contains:

- character mode and an opt-in copy of the supplied character asset;
- S1-S4 or custom-reference style route, its exact approved variant, plus an
  opt-in copy of a reference image;
- approved palette tokens;
- approved resolution/canvas, overlay scale, and placement coordinates;
- schema version and a human-readable preset name.

It does not store source videos, transcripts, chapter lists, output folders,
editor-import claims, or any third-party logo/watermark that was removed during
reference adaptation. Chapter count is always content-adaptive and is never
copied from the previous video.

## Save and reuse

Use `scripts/preset_library.py` after explicit approval. For example:

```bash
python3 scripts/preset_library.py save \
  --name "我的 Vlog 默认风格" \
  --library-dir ~/.elleflow/presets \
  --character-mode walk-cycle \
  --character-image /path/to/avatar.png \
  --style S2 \
  --style-variant "segmented-soft-runway" \
  --palette primary=#E89AB3 \
  --palette text=#111111 \
  --resolution 2K \
  --canvas-width 2560 \
  --canvas-height 498 \
  --overlay-scale 1.0 \
  --placement top \
  --position-x 0 \
  --position-y 32 \
  --set-default \
  --json
```

The script creates a versioned, self-contained preset directory and copies only
the assets the creator explicitly approved. It never overwrites an existing
preset.

On a later project, inspect the file before offering it:

```bash
python3 scripts/preset_library.py show \
  --preset ~/.elleflow/presets/my-vlog-sop/preset.json \
  --json
```

Show the preset name, character mode, exact style variant, colors, size, scale,
and placement. The creator may use the complete bundle, adjust one part, or
decline it. A current video always gets its own chapter analysis, output folder,
collision check, and final preview. Reusing the bundle never reuses the old
chapter count.
