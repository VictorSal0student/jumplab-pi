# JumpLab Pi 0.1.0

A local, offline, single-user CMJ video measurement application for Victor Salvat and Baptiste's **Measurement and Analysis Chain for Biofeedback** project (Pr. Gilles Despaux, M2 DigiMove-IDIL).

**Working scope:** import or record one jump, inspect indexed decoded images, select contact frames, calculate flight time and estimated centre-of-mass rise, review, save, reopen and export. Automatic detection is deliberately unavailable. All processing and storage run on the computer serving the app; the intended computer is a Raspberry Pi 3B+.

## Install on Raspberry Pi

Target: Raspberry Pi OS with a desktop browser and Python 3.9 or newer. This release has been software-tested on Linux x86-64; actual Pi/camera compatibility and performance remain to be validated. No Python runtime packages, Node.js, model downloads or API keys are required.

1. Extract this ZIP to a writable folder, such as `~/jumplab-pi`.
2. Install system dependencies once (internet or an offline package source is needed for installation):

   ```bash
   sudo apt update
   sudo apt install python3 ffmpeg
   ```

3. In a terminal, launch from the extracted project directory:

   ```bash
   cd ~/jumplab-pi
   python3 -m jumplab.server
   ```

4. On the **same Pi**, open `http://127.0.0.1:8765` in Chromium or another current browser. Keep the terminal open. Press Ctrl+C to stop the server.

Once installed, the app works without internet. Interface assets and the synthetic sample are bundled. The server binds only to loopback; this is not a public deployment or a phone-accessible network service.

Optional data directory and port:

```bash
python3 -m jumplab.server --data ~/JumpLabPi-data --port 8765
```

The default data directory is `~/JumpLabPi-data`. Back it up separately from the source folder. Restart the server and use **Open** in session history to reopen a saved trial.

## First successful trial (no camera needed)

1. Click **Open synthetic demo**. The video and UI explicitly identify it as synthetic.
2. Go to frame **29**, then click **Set last ground contact**. Inspect frame 30 to confirm flight.
3. Go to frame **45**, then click **Set first landing contact**. Inspect frame 44 to confirm flight.
4. Expected estimate: **500.0 ms**, **30.6 cm**; frame-bound flight interval approximately **466.7–533.3 ms**. These are generated software-test values, not a human measurement or accuracy validation.
5. Check the two review confirmations after inspection, then **Mark reviewed**.
6. **Export trial ZIP** saves the original video, JSON and frame timestamps. **Export CSV** saves session results. Reimport the trial ZIP to verify portability.

For a real video, enter a participant code and session, then **Import video / trial ZIP**. Use one short jump clip: 3–1800 decoded frames, upload at most 256 MiB. On Pi 3B+, start with 640×480 and a 3–5 second clip. Processing is asynchronous; wait for completion. Failed imports leave the previous trial intact.

## Camera mode

**Check camera** uses `rpicam-vid` or, on older systems, `libcamera-vid`. If neither a supported adapter nor CSI camera is detected, import mode remains fully usable. USB/V4L2 cameras and legacy `raspivid` are not supported in v0.1.

On Raspberry Pi OS releases using rpicam, camera applications may need installation with `sudo apt install rpicam-apps`; package availability depends on the OS. Check `rpicam-vid --list-cameras` (or `libcamera-vid --list-cameras`) before recording. Do not change OS camera configuration blindly: first identify your camera model, OS release and camera stack.

**Record 5 seconds** requests 640×480 H.264 at 30 fps and a `--save-pts` timestamp sidecar. An operator should trigger capture with the participant already in view. There is no live preview or audible countdown; inspect a short test capture to position the camera. Requested fps is metadata, not the measurement clock. Sidecar counts must match the decoded frame count. Exposure timing and frame correspondence still require hardware verification.

## Measurement and review

- **Takeoff selection:** last image with any foot-ground contact before flight; its following frame must show both feet airborne.
- **Landing selection:** first image with any foot-ground contact after flight; its preceding frame must be airborne.
- Physical event times are bracketed by these adjacent timestamps. The estimate uses interval midpoints, not exact contact times.
- Height is `9.80665 × flight_time_seconds² / 8`: estimated takeoff-to-apex centre-of-mass rise, assuming equal COM height at takeoff and landing. No force, power or injury-risk estimate is produced.
- Source presentation timestamps are used, including variable-rate intervals, only after image-count/sequence correspondence checks. They are not automatically proof of a calibrated camera clock.
- Invalid/missing timestamps block results. A documented constant-rate fallback must be explicitly applied; it assumes no dropped frames. Slow-motion export timestamps may represent playback rather than real capture time. Inspect provenance before review.
- **Unreviewed**, **Reviewed** and **Rejected** are explicit states. Changing selections or timing invalidates review. Ambiguous contacts cannot be marked Reviewed. Unavailable results are blank/“Unavailable”, never a numerical zero.
- Rejected trials keep their computed values for audit; use the state column to exclude them from analyses. “Reviewed” means visual/timing checks were acknowledged, not independent validation.

See [annotation protocol](docs/PROTOCOL.md), [measurement method](docs/MEASUREMENT.md), [trial format](docs/FORMAT.md), [validation](docs/VALIDATION.md), [reference inspection](docs/REFERENCE_REVIEW.md) and [dependencies](DEPENDENCIES.md).

## Project layout

| File | Responsibility |
|---|---|
| `jumplab/capture.py` | Isolated optional CSI camera adapter |
| `jumplab/video.py` | FFprobe timing and sequential FFmpeg image extraction |
| `jumplab/measurement.py` | Timing checks, contact intervals, flight time and height |
| `jumplab/detection.py` | Explicit unavailable proposal object; extension point |
| `jumplab/storage.py` | JSON persistence, ZIP round trip, CSV, audit |
| `jumplab/server.py` | Local HTTP endpoints and background jobs |
| `jumplab/static/` | Bundled HTML/CSS/JavaScript interface |
| `tests/` | Python tests and optional browser workflow checks |
| `samples/` | Labelled synthetic video |

## Tests and troubleshooting

```bash
python3 -m unittest discover -s tests -v
```

For optional development browser tests, start the server with a disposable data directory, install Playwright in your development environment and run `node tests/browser.cjs`. These tools are not required on the Pi. See DEPENDENCIES.md for the tested version.

If FFmpeg is missing, run `ffmpeg -version` and `ffprobe -version`, install the package and retry. If processing times out, use a shorter/lower-resolution clip. If a codec is unsupported, use a compatible source; preserve and document any conversion because re-encoding can change timing. Invalid order or incomplete contacts leaves results unavailable. If timing is unreliable and no defensible fallback exists, reject the trial.

Storage grows with decoded JPEG previews and original recordings. Monitor free SD-card space. Export trial ZIPs for transfer; while the app is stopped, back up or remove complete trial folders to reclaim space. No deletion button, automatic backup, PDF report, live tracking or automatic detector is included in this first version.
