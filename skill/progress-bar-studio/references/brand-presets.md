# Reusable brand presets

A brand preset stores a creator's approved character route, style route, palette,
and optional reference image. It is a local, explicit asset bundle, not hidden
memory. The creator chooses whether to save it and whether to use it later.

## When to ask

After the creator has selected the character route, style route, and palette,
ask one short question:

```text
要把这套角色、样式和颜色保存成下次可复用的 ElleFlow 预设吗？
```

Ask only after the choices are visible. Never save a character, reference image,
or palette without an explicit yes.

If the creator chooses to save it, ask for a short preset name and whether it
should become the suggested default. A default is still a suggestion: on a later
project, show its summary and ask whether to use it before copying any assets.

## What is saved

A preset contains:

- character mode and an opt-in copy of the supplied character asset;
- S1-S4 or custom-reference style route, plus an opt-in copy of a reference image;
- approved palette tokens;
- schema version and a human-readable preset name.

It does not store source videos, transcripts, chapter lists, output folders,
editor-import claims, or any third-party logo/watermark that was removed during
reference adaptation.

## Save and reuse

Use `scripts/preset_library.py` after explicit approval. For example:

```bash
python3 scripts/preset_library.py save \
  --name "我的 Vlog 默认风格" \
  --library-dir ~/.elleflow/presets \
  --character-mode walk-cycle \
  --character-image /path/to/avatar.png \
  --style S2 \
  --palette primary=#E89AB3 \
  --palette text=#111111 \
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

Show the preset name, character mode, style route, and colors. The creator may
use it unchanged, adjust any part for the current video, or decline it. A
current video always gets its own chapter analysis, output folder, resolution,
and final preview.
