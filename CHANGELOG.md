# Changelog

## 0.2.5 - 2026-08-18

### Changed

- Reworked the creator experience into an enforced Step 1-8 conversation: one question, one decision, and 2 to 5 A/B/C choices per reply.
- Made the first-run message a three-way starting choice for creators who already have an analysis video, need a 720p export hint, or want to preview the output first.
- Separated the one creator-facing final file from internal project records, and delayed final delivery-folder reservation until the 15-second sample is approved.
- Added explicit choice acknowledgement, plain-language state recap, `改一下`, and `返回上一步` behavior so a revision never restarts the project.

### Added

- Added `guided-conversation.md`, with required Chinese creator-facing cards, button/text fallback, natural-language mapping, and error-recovery paths.

## 0.2.4 - 2026-08-18

### Changed

- Made a `720p` lightweight analysis copy the recommended upload path; `480p` is now a fallback for very long videos or slow networks.
- Separated analysis from publishing: the upload is used for content understanding and chapter timing, while the original high-resolution project stays in the creator's editor.
- Made high-resolution transparent `progress_bar.mov` the only standard final delivery.
- Removed direct full-video compositing, composited MP4 samples, and delivery-mode choices to avoid re-upload cost, placement ambiguity, and unnecessary re-encoding.

### Added

- Added alignment rules requiring the analysis copy and original project to keep the same duration, aspect ratio, clip order, and playback speed.
- Added a clear-screen or chapter-name fallback when 720p cannot expose small text, slides, code, or tables.

## 0.2.3 - 2026-08-18

### Changed

- Made chapter confirmation the first creator decision after a video is dropped in.
- Removed the user-facing emphasis on source audio; only explain transcription limits when they actually block chapter analysis.
- Replaced the default long preview deliverable with two 15-second review samples: a transparent overlay and a composited video preview.

### Added

- Added delivery-mode choice: transparent overlay, final composited MP4, or both.

## 0.2.2 - 2026-08-18

### Changed

- Reordered the creator experience to video, character, style, color, optional reusable preset, delivery settings, combined preview, 15-second sample, then full export.
- Moved output folder, resolution, and size planning until after visual decisions are complete.
- Made the combined chapter-character-style preview the final creative checkpoint before animation.

### Added

- Added opt-in local brand presets for approved character assets, style routes, and color palettes.

## 0.2.1 - 2026-08-18

### Changed

- Renamed the user-facing product to `ElleFlow｜小人走路视频进度条动画`.
- Kept the Skill ID `progress-bar-studio` unchanged so existing installation paths and calls remain compatible.

## 0.2.0 - 2026-08-18

### Changed

- Added a first-run welcome message that tells new users what they can send next.
- Made output folder and export resolution explicit Step 01 decisions.
- Defaults approved deliverables to the source-video folder without overwriting existing files.
- Added 1080p, 2K (2560px wide), and 4K planning estimates before rendering.
- Clarified that a skipped sample cannot produce a final size estimate or an editor-compatibility claim.
- Skips a separate character checkpoint when the user has already chosen no character.

### Fixed

- Default prompt now enters the material brief before chapter analysis.
- File-size estimates now inspect the actual delivery folder.
- The walk-cycle splitter is executable and uses the documented foot-baseline tolerance.

### Added

- `estimate_export_size.py` for text and JSON size planning.
- `preflight.py` for machine-readable environment and delivery-folder checks.
