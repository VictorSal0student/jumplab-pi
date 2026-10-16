# Trial and export format — schema 1

Each saved trial has a random 32-character hexadecimal ID and a directory under the configured data root. One trial is open in the workspace; the history lists all saved trials in that data directory.

| File | Content |
|---|---|
| `trial.json` | Authoritative metadata, times, selections, derived results and audit |
| `original.<extension>` | Byte-for-byte original input video |
| `frames/000000.jpg`, etc. | Decoded display-order previews, zero-based; downscaled to at most 960 pixels wide |
| `capture.pts` | Camera timestamps when captured with the CSI adapter |
| `capture.log` | Camera tool output when available |

JSON saves use a temporary file followed by an atomic replacement. Original video SHA-256 is recorded. JPEGs are display caches; they are not replacement source media. Export/back up only after processing completes. Run one server instance and use one active browser tab per data directory; multi-user/concurrent-writer operation is outside v0.1.

## JSON fields

| Field | Meaning |
|---|---|
| `schema_version`, `software_version` | Storage schema integer and app version |
| `id`, `created_at`, `updated_at` | Trial identity and UTC ISO timestamps |
| `participant`, `session`, `notes`, `demo` | User metadata; synthetic origin boolean |
| `original_file`, `original_name`, `original_sha256` | Stored basename, input name, content checksum |
| `camera` | Import adapter or camera command/settings/log provenance; hardware validation status |
| `video.frame_count` | Number of decoded display frames |
| `video.timestamps_s` | Active measurement times, normalized when valid or explicitly replaced by fallback |
| `video.source_timestamps_s` | Original frame times, including null when missing; never changed by manual fallback |
| `video.time_origin_s` | Original normalization offset, null when unavailable |
| `video.provenance` | Source timing method; always interpret together with `timing_fallback` |
| `video.stream`, `video.format` | FFprobe timebase, frame-rate metadata, codec/dimensions and format metadata |
| `video.quality` | Timing validity, flags, gap indices and interval summaries |
| `video.processing_seconds`, `video.ffmpeg_version` | Actual processing duration and decoder version |
| `automatic_proposals` | Original detector output, independent of manual selections; unavailable in v0.1 |
| `selections.takeoff`, `selections.landing` | Zero-based integer contact frame indices, or null |
| `status` | `Unreviewed`, `Reviewed`, or `Rejected` |
| `review` | Contact confirmation, timing acknowledgement and contact ambiguity booleans |
| `results` | Flight time/height, interval estimates, bounds and estimator, or null |
| `quality_flags` | Timing, synthetic, tracking and review warnings; may include calculation failure text |
| `settings` | Gravity, annotation convention, estimator and detector configuration |
| `timing_fallback` | Assumed fps, user reason, time of application and assumption; null by default |
| `audit` | Prior/new selections and review states, timestamps and fallback details per edit |
| `imported_from_id` | Present when restored from an exported trial ZIP |

All times are seconds unless the field explicitly says otherwise. Height is metres in JSON/CSV and centimetres in the UI. JSON uses null for unavailable values; NaN/Infinity are not written. Gap index `i` means the interval between frames `i` and `i+1`.

The audit is an edit trail, not a cryptographically signed record or a complete revision history of every note/metadata field. Automatic proposals cannot be replaced through the normal edit API.

## Portable ZIP

Contains `trial.json`, original video, `frames.csv`, `README.txt`, and camera sidecars when present. It omits regenerable JPEG previews. Reimport verifies the original checksum, re-decodes frames, checks frame count and imported PTS, recalculates results, restores selections/proposals/notes/review and assigns a **new** ID. The source ID is recorded in `imported_from_id`; original exported JSON retains its original creation date. The restored trial's creation date is the reimport date.

`frames.csv` columns:

```text
frame_index,measurement_timestamp_s,source_timestamp_s
```

The first column indexes the exact decoded display sequence. Blank timestamp cells mean unavailable. The ZIP is portable application data, not a trained detector or an accuracy certificate.

## Session CSV

```text
trial_id,participant,session,created_at,state,synthetic_demo,flight_time_s,height_m,notes
```

Missing numerical values are blank. Filter `state` and `synthetic_demo` before analysis: rejected/unreviewed/demo rows remain exported. Text beginning with a spreadsheet formula prefix is escaped with an apostrophe. Full timing uncertainty and quality metadata are in each trial ZIP's JSON.
