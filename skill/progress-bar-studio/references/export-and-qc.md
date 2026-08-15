# Export and QC

## Transparent master

Use ProRes 4444 MOV when the editor needs a robust Alpha overlay:

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

## Size planning

Encode the approved 15-second sample with final settings, then estimate:

```text
estimated full size =
sample bytes × full duration / sample duration
```

Check free disk space before full encoding. Keep room for the output, temporary
files, and validation reads.

## Required checks

1. Probe codec, profile, tag, pixel format, dimensions, fps, duration, and frame
   count.
2. Decode the entire file.
3. Confirm every frame contains transparent pixels and fully opaque pixels.
4. Inspect start, end, motion, and every chapter transition.
5. Composite an encoded frame over white, black, red, blue, brand color, and
   checkerboard.
6. Create a lightweight MP4 preview over the source video.
7. Calculate SHA-256 for large final files.

Use `scripts/verify_alpha_mov.sh` for the full Alpha scan.

## 剪映/CapCut handoff

- Import the 15-second sample into the actual editor before full render.
- Place it on an overlay track and view it over real footage.
- A black preview in a generic player does not prove Alpha failure.
- Do not claim practical compatibility until the editor import succeeds or the
  user confirms it.
- For a 3840-wide strip in a 480-wide project, 12.5% scale restores the design
  size when the editor does not auto-fit.

## Delivery report

Report:

- master path and file size;
- codec/profile/tag;
- dimensions, fps, duration, and frame count;
- Alpha scan result;
- chapter-transition result;
- preview and QC paths;
- whether the target editor was actually tested.
