# Current-source and authorization rule

A readable finished video supplied for this project is its timing source; do not
require a second confirmation about an analysis copy that does not exist. When
an independent analysis copy is used, verify timeline equivalence and ask only
if uncertain or later edits are reported. Preserve explicit current-project
choices, delegation, sample waiver and final authorization. The checks below
apply to missing evidence, not permission already granted.

# Export and QC

## Video fit check

Run this check for every current video, including quick reuse. The expected outcome
is a coordinated, readable overlay that follows the actual content and timing;
matching does not require copying every color from a frame.

1. **Content and timing.** Bind chapter evidence to this finished video's sourceId,
   duration and fps. Recheck each new-task boundary and title. Re-edits invalidate
   old timing even when the framework and IP stay the same. The character and fill
   share the chosen progress mapping; do not mix time-linear and chapter-weighted
   positions. Use actual encoded frame times and the documented one-frame rounding
   rule, never extend the strip with a repeated tail.
2. **Visual direction.** Inspect representative beginning, middle and ending
   frames, plus significant light/dark or layout changes. Use recurring background,
   title and subtitle colors and visual weight to propose a coordinated palette
   and structure. Current explicit colors/styles and authorized brand reuse retain
   priority. Lime is a catalog example. Do not infer a palette from the person's
   skin or one incidental object, or claim automatic extraction that never ran.
3. **Geometry in the actual video.** Determine displayed orientation/aspect ratio
   from decoded frames, not the filename. Choose a lane clear of subtitles, faces,
   titles and essential demonstrations. Fit strip width/height, font hierarchy and
   IP size at the actual publishing scale; a 2160px master width does not specify
   how large it should appear in a portrait frame. Record intended displayed width,
   placement and scale (displayed strip width / encoded strip width). Agent measures
   these; the user is not asked to enter coordinates. Keep the full overlay and
   character within bounds, without a single-character orphan or hidden chapter.
4. **Actual-frame proof.** Overlay the same routed renderer's output on the current
   source frame at the intended placement and scale. Include a representative
   bright/dark view where present and chapter-boundary before/after checks. Before
   final handoff use frames decoded from the actual MOV to detect crop, timing or
   font differences. Inspect at the smallest publishing size, not only the master.

Keep sourceId, sampled times, actual preview paths, intended placement/scale and
any unresolved collision/contrast issue in the private project decision record.
Review these together with the dynamic draft; do not ask for separate approvals
for each frame. Source pixels remain unchanged and the delivered master remains
an independent transparent MOV; do not encode a full composite without a request.

An opaque review GIF or short MP4 can accompany the transparent master where a
host cannot preview ProRes. Label it as a review copy. Alpha scans, six-background
boards, a synthetic blank video, or timestamped transcript alone cannot establish
visual fit with a real video. If actual frames are inaccessible, keep that check
unverified, preserve completed analysis and ask only for the missing representative
frames or viewing access.

Quick reuse retains approved IP and the requested style/brand settings; it does
not transfer previous timing or a previous video's visual-fit verdict. If a new
frame reveals a collision or unreadable contrast, propose only the affected local
adjustment and show it in the same draft. Do not regenerate the IP or silently
replace an explicitly chosen style/color to satisfy the fit check.

## Rendering boundary

For S1–S7 use `scripts/render_progress.py` with an explicit approved render
config; read [rendering.md](rendering.md). It renders actual RGBA frames and
streams ProRes 4444 MOV, but does not analyze the source video, infer a portrait
layout, generate character assets or accept brand-preset JSON directly. Custom
references outside its supported forms require a host-built implementation.
The FFmpeg command below is an alternative for an existing RGBA source; it does
not create chapter visuals from `chapters.json`.

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
selected strip-width quality preset and be laid out for the original project's
aspect ratio. The strip is not a full-frame video canvas.

When an independent analysis copy is used and matching is uncertain, confirm that it and the original project have the same duration, aspect ratio, clip order and playback speed. When the uploaded finished video itself defines timing, skip that redundant confirmation. The creator will
place the transparent master at the start of the original timeline. If the
original is later trimmed, reordered, or sped up, require a newly exported
analysis copy before delivery.

## Size planning

After the creator has chosen dimensions, estimate the EXACT current routed config:
`python scripts/estimate_export_size.py <current-video> --config <current-routed.json> --output-dir <approved-folder> --json`.
This uses the derived multi-row height, exact width, and target fps. A conflicting
`--width` or `--strip-height` fails rather than silently changing the estimate.
For a pending draft, add `--draft` to this command. The estimate includes the
actual DRAFT label band. It leaves the configuration and approval state unchanged;
never relabel pending assets as approved to estimate them. After design approval,
estimate the approved final config again without `--draft`, since its band is gone.
Without a config, `--width <exact-pixels>` estimates only that selected width.
Without either option, the comparison presets are:

- 1080p: 1920 pixels wide;
- 2K in this project: 2160 pixels wide;
- 4K: 3840 pixels wide.

An explicitly requested 2560px project remains 2560; do not relabel or resize it.
These are strip-width presets for both portrait
and landscape videos. They are not full-frame 1920×1080 / 1080×1920 dimensions,
and the estimator does not auto-rotate them. Probe source orientation separately,
design readable labels and safe placement for the original aspect ratio, and
record the actual strip size and editor scale. A full-canvas overlay would need
a separately constructed render and size calculation; do not claim the bundled
estimator provides it.

The planning range uses the real video's duration and the selected render fps.
It is an uncalibrated heuristic, not a guaranteed upper bound: actual graphical
ProRes exports can exceed it substantially. Do not promise a file-size ceiling
or use that range as sufficient evidence that disk space is safe for a long export.

Once an actual transparent short draft/sample exists (at most 15 seconds, or the
whole shorter clip), use its measured bytes and encoded duration to calibrate the
full-render estimate. Measurement itself grants no design or export approval:

```text
estimated full size =
sample bytes x full duration / sample duration
```

Use identical codec, dimensions and fps for the extrapolation. A marked draft
includes extra pixels; its rate is only an approximate guide for an unmarked final.
Editor compatibility still requires an actual editor import; bytes alone do not
establish it. When the creator explicitly skips the sample, keep the planning
range as an estimate, mark editor import as unverified, and do not call the
number final. Log the explicit waiver and final-export permission, reserve with
`prepare_delivery.py --sample-waived`, and do not save a verified preset. Never
substitute `--sample-approved` for a skipped sample. Before full-export authorization, show the estimate alongside
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
6. Normally create and approve a sample of at most 15 seconds (the whole shorter
   clip), crossing a chapter boundary where one exists. For a single chapter,
   check start/end and motion. Record any explicit creator-requested waiver separately.
7. Calculate SHA-256 for large final files.

Use `scripts/verify_alpha_portable.py` for the full Alpha scan (the .sh wrapper remains compatible).
For six-background review use `python scripts/make_multibg_preview.py <RGBA.png> <new-review.png> <brand-HEX>`;
it works without Bash and refuses overwrites. Review interior opacity separately: decoded Alpha can
pass while a white body is accidentally translucent. Keep identity, gait and editor-import verdicts separate.

## Editor handoff

- On the normal sample path, import the transparent sample into the actual
  editor before full render when that editor is available; otherwise report
  editor import as unverified and let the creator test it.
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
