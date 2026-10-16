# Validation summary — JumpLab Pi 0.1.0

Date: 15 October 2026. Tested in a Linux x86-64 development environment with Python 3.12.14, FFmpeg 6.1.1, Node.js 24.19.0, Playwright 1.62.1 and headless Chromium 153.0.8010.0. **No Raspberry Pi or physical camera was attached. No real-jump criterion-validity study was performed.**

## Automated Python checks: 17/17 passed

Command: `python3 -m unittest discover -s tests -v`.

| Area | Tested behaviour | Result |
|---|---|---|
| Measurement | 0.500 s gives 0.3064578125 m; contact interval bounds | Pass |
| Event validity | Reversed/identical/adjacent contacts, out-of-range or non-integer indices | Pass |
| Timing validity | Missing, duplicate, descending, NaN and infinite times | Pass |
| Variable-rate timing | Actual adjacent intervals and gap flags, including a decoded VFR video | Pass |
| Frame correspondence | Frame count and timestamps; cached frame 45 byte-matches independent extraction of frame 45 | Pass |
| Raw H.264 | Missing PTS remains invalid; generated timestamp sidecar supplies timing; count mismatch rejected | Pass — synthetic sidecar only |
| Review | Confirmation gates, ambiguous contact rejection, correction resets review | Pass |
| Proposal preservation | Injected test proposal remains unchanged after manual corrections | Pass — detector fixture, not actual detection |
| Persistence | Same-folder reopen consistency; ZIP export/reimport retains results, selections, proposal, notes and review | Pass |
| Fallback | Unjustified fallback rejected; documented fallback preserves original missing times | Pass |
| Import failure | Broken video fails without changing prior saved trial | Pass |
| Export integrity | Original-video checksum tampering rejected; unavailable CSV values blank; formula-like text escaped | Pass |
| HTTP | Offline assets, invalid JSON handling, local host and mutation-token checks | Pass |

## Browser workflow: passed

Ran `tests/browser.cjs` against a temporary local server/data directory. The normal Playwright browser download was unavailable in this environment; a Chromium binary obtained from the npm package `@sparticuz/chromium@153.0.0` was used for development validation only. It is not bundled or required by JumpLab Pi.

- Opened the app and synthetic example; camera check selected explicit no-camera/import mode.
- Stepped 0 → 1 → 0, verified frame 1 timestamp 0.0333 s.
- Selected last contact 29 and landing 45; verified 500.0 ms and 30.6 cm.
- Verified review blocked without confirmation; then saved notes and marked Reviewed.
- Downloaded and reimported the actual trial ZIP; checked retained review and measurement.
- Made an invalid-order correction; verified Unreviewed and unavailable height, then restored the selection.
- Tested overlapping slider requests with a delayed image response; final displayed image URL and frame index matched the newest request.
- Imported a corrupt MP4; verified the existing result remained intact and an error was shown.
- Resized repeatedly across 390, 1280 and 1440 pixel widths. Viewer height remained <=350 pixels, with no horizontal document overflow. History has its own bounded scroll area. No canvas is used.
- No uncaught browser exceptions were recorded.

The first browser pass exposed stale review-error text after successful save and horizontal overflow after a failed import on a narrow screen. Both were fixed and the complete browser workflow rerun successfully. Desktop and mobile screenshots were visually inspected. See `docs/screenshots/`; the mobile screenshot intentionally shows a failed import while retaining the previous trial.

## What is still pending

| Level | Remaining work |
|---|---|
| Pi hardware compatibility | Identify Pi OS/release/architecture, camera model and installed camera stack; verify camera discovery and actual capture |
| Capture timing | Verify sidecar units and ordering for that stack, exposure timestamp meaning, timestamp gaps and clock behaviour |
| Pi resources | Measure processing duration, peak memory, thermal throttling, browser responsiveness and storage per trial on Pi 3B+ |
| Visual-label agreement | Independent annotators on representative human recordings; report disagreement in frames/ms |
| Independent measurement validity | Synchronized reference measurements with defined contact thresholds and uncertainty; assess posture assumptions |
| Automatic detector | Not implemented; requires separate development and held-out evaluation videos plus Pi benchmarks |

Software correctness, agreement with human visual labels, and independent measurement validity are distinct. Passing these software tests establishes neither human contact accuracy nor Pi performance. The sample animation is a deterministic workflow fixture, not a biomechanically validated CMJ.

## Known v0.1 limits

Single user, one active browser tab, one jump per clip, one trial open at a time; no live camera preview, USB camera adapter, automatic event detector, PDF/PNG result export or multi-user server. Camera capture requests five seconds at 640×480/30 fps; it has not been hardware-tested. JPEG previews are downscaled to at most 960 pixels wide, so fine contact inspection may require an appropriately framed source. Slow-motion/re-encoded videos require a documented timing interpretation. Existing results remain visible for rejected trials and must be filtered by state. No public deployment was performed.
