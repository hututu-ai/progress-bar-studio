# Changelog

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
