# Measurement model and timing uncertainty

For zero-based decoded frame timestamps `t[i]`, let `a` be the last ground-contact frame before flight, and `b` the first landing-contact frame. Require `0 <= a`, `a + 1 < b`, and `b < frame_count`. At least one airborne frame must be visible between contacts.

| Quantity | Definition |
|---|---|
| Takeoff interval | `[t[a], t[a+1]]` |
| Landing interval | `[t[b-1], t[b]]` |
| Takeoff estimate | `(t[a] + t[a+1]) / 2` |
| Landing estimate | `(t[b-1] + t[b]) / 2` |
| Flight estimate T | Landing estimate minus takeoff estimate |
| Flight bounds | `[max(0, t[b-1] - t[a+1]), t[b] - t[a]]` |
| Estimated COM rise | `g × T² / 8`, with `g = 9.80665 m/s²` |
| Height bounds | Apply the same formula to each flight bound |

These bounds are conditional on correct visual labels and trustworthy timestamps. They are not statistical confidence intervals and omit exposure duration, rolling shutter, clock calibration, motion blur, occlusion, codec artifacts and posture differences. Midpoints are a declared estimator; they do not establish sub-frame accuracy. At constant frame period Δ, the flight midpoint has a frame-bound half-width of Δ, not Δ/2, because both transitions contribute.

At 30 fps, a 500 ms midpoint flight estimate has frame-bound limits about 466.7–533.3 ms, corresponding to approximately 26.7–34.9 cm. The midpoint height is 30.6 cm. A squat landing changes COM height and can bias this formula even with perfect contact timing. The result is not total jump displacement from standing, and no force or power is inferred.

## Clock and image correspondence

FFprobe reads frame `pts_time` in decoded display order. FFmpeg sequentially emits JPEGs numbered from zero, with `-vsync 0` to avoid intentional frame duplication/drop. A `showinfo` filter observes the same output sequence. Counts and indices must match, and available PTS are cross-checked. The viewer loads the indexed JPEG before switching image, index and timestamp together; annotation never uses HTML video seeking.

Imported source timestamps are retained verbatim as numeric seconds in `source_timestamps_s`; valid working times are normalized to the first timestamp. Stream timebase, nominal/average fps and FFmpeg version are retained. Nominal fps does not drive calculations. Variable-rate data use actual adjacent PTS intervals.

The camera adapter reads `--save-pts` values in milliseconds and converts to seconds. The encoded order/frame-count correspondence is assumed by this adapter and must be verified on the actual camera stack. Camera sidecar timing overrides raw H.264's missing/synthetic container times. Source sidecar and capture log are retained.

Every timestamp must be finite, and all intervals strictly positive. Missing, duplicate or descending timestamps invalidate timing. Gap indices identify intervals greater than `max(1.8 × median interval, 50 ms)`. Interval variation greater than `max(0.1 ms, 2% of median interval)` is flagged as variable rate. These are screening rules, not calibrated hardware fault thresholds. A long gap can hide contact and invalidate the labels even when ordering remains valid; inspect and reject when necessary.

## Explicit fallback

The user must enter an assumed constant rate (1–240 fps) and a justification of at least 12 characters. The active times become `i/fps`; original times remain preserved. This assumes a constant capture rate without dropped frames and cannot repair VFR, establish real-time semantics of slow motion, or recover an unrecorded event. Fallback status is flagged and review reset. There is no silent use of average fps.

An explicit fallback can replace even valid container timing if external evidence shows it represents a different clock; document that evidence carefully. To undo a fallback in v0.1, reimport the original video as a new trial and reannotate. Earlier fallback changes remain in the audit trail.
