# Preserved gallery geometry

This directory preserves the installed September 2026 gallery's drawing code.
No gallery images, example avatar, private state, user profile or character
asset is included. The repository's MIT license applies to this project code.

Source fingerprints before adaptation:

- render_overlay.py: `63972a89ab50029b1e6e998b82885f952073d7229aa6bb0c7d0a1d912be0bac1`
- reference_presets.py: `1028e50f1312ce94926e7cff9925968afd19e70bbe4cba9c718618c30d3ae9f5`

`reference_presets.py` is unchanged. In `render_overlay.py`, the project-validator
import and old CLI were removed and the reference-presets import made relative.
The drawing class is unchanged. The old CLI forced its final encoded frame to
the timeline endpoint; exports now use the candidate encoder's actual frame
presentation times, approval checks and atomic no-overwrite behavior instead.

Use `style_router.py`, never an ambiguous S number across both engines. Its
adapter validates inputs before calling this geometry and requires an explicit
palette. Capturing an old effective default during an explicitly sourced import
does not make that palette a default for future videos.
