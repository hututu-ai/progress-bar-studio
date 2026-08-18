# Export and QC

## Transparent master

Use ProRes 4444 MOV when the creator needs a robust Alpha overlay:

```bash
ffmpeg -i <rgba-source> \
  -c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le \
  -an <output.mov>
```

Decoded FFmpeg metadata may report `yuva444p12le`; this is acceptable when the
codec profile is ProRes 4444 and Alpha verification passes.

Do not use H.264, ordinary HEVC, ProRes 422, or a filled background when Alpha is
required. HEVC with Alpha needs a proven native Apple encoder and decoder.
Documented SDK support alone is insufficient.

## Analysis copy and alignment

The uploaded source may be a 720p analysis copy. It is used to understand
content, prepare chapter timings, and produce a visual preview; it is not the
final publishing asset. The final `progress_bar.mov` must use the creator's
selected 1080p, 2K, or 4K canvas and be designed for the original project's
aspect ratio.

Before rendering, confirm that the original project and analysis copy have the
same duration, aspect ratio, clip order, and playback speed. The creator will
place the transparent master at the start of the original timeline. If the
original is later trimmed, reordered, or sped up, require a newly exported
analysis copy before delivery.

## Size planning

After the creator has chosen an output folder and output resolution, run
`scripts/estimate_export_size.py <analysis-video> --output-dir <output-folder>`
and show a planning range for all three confirmed output-resolution options:

- 1080p: 1920 pixels wide;
- 2K: 2560 pixels wide;
- 4K: 3840 pixels wide.

The planning range must use the real analysis-copy duration and fps. It is
deliberately a range because the final strip height and animation complexity are
not known until the visual design is approved. Do not present a generic
file-size claim as an exact estimate.

After the creator approves the 15-second transparent sample, calculate the
full-render estimate:

```text
estimated full size =
sample bytes x full duration / sample duration
```

The sample is required before claiming editor compatibility or a sample-derived
final size estimate. When the creator explicitly skips it, keep the planning
range as an estimate, mark editor import as unverified, and do not call the
number final. Before full-export authorization, show the estimate alongside
available disk space in the approved output folder. Keep room for the output,
temporary files, and validation reads.

## Required checks

1. Probe codec, profile, tag, pixel format, dimensions, fps, duration, and frame
   count.
2. Decode the entire file.
3. Confirm every frame contains transparent pixels and fully opaque pixels.
4. Inspect start, end, motion, and every chapter transition.
5. Composite an encoded frame over white, black, red, blue, brand color, and
   checkerboard.
6. Create a 15-second transparent sample that crosses a chapter boundary.
7. Calculate SHA-256 for large final files.

Use `scripts/verify_alpha_mov.sh` for the full Alpha scan.

## Editor handoff

- Import the 15-second transparent sample into the actual editor before full render.
- Place it on an overlay track at the start of the original high-resolution timeline.
- Confirm that duration, chapter changes, subtitles, and character placement align.
- A black preview in a generic player does not prove Alpha failure.
- Do not claim practical compatibility until the editor import succeeds or the
  creator confirms it.
- For a 3840-wide strip in a 480-wide project, 12.5% scale restores the design
  size when the editor does not auto-fit.

## Delivery report

Report:

- master path and file size;
- codec/profile/tag;
- dimensions, fps, duration, and frame count;
- Alpha scan result;
- chapter-transition result;
- QC paths;
- whether the target editor was actually tested.
