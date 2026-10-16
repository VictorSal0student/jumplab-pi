# Athlete Lens reference inspection

Reviewed the supplied `athlete-lens-main.zip` source snapshot, not an assumed current GitHub branch.

- Repository: https://github.com/JoseGarciaMayen/athlete-lens
- Revision recorded by the ZIP archive comment: `2a85fc192487e9c1b9fb8d39af77252f87c5e231`.
- Relevant files: `backend/core/vertical/extractor.py`, its adjacent README, `backend/pyproject.toml`, `backend/tests/README.md`, and root `LICENSE`.
- Repository licence: MIT, copyright (c) 2026 Jose Garcia Mayen. A copy is included as `licenses/athlete-lens-MIT.txt` for the reference record. **No Athlete Lens source code, model weights or frontend assets are incorporated into JumpLab Pi.**

## Rechecked findings

1. The vertical module uses Ultralytics YOLO ankle coordinates (keypoints 15 and 16), averaged for the first detected person. Missing detections after the first frame repeat the previous value; missing initial detection fails.
2. Event detection uses the first 15 frames' median, a threshold 30% of the ankle excursion above baseline, and two sustained frames. The supplied README explicitly states calibration on one 60 fps CMJ video. The code hardcodes `0.3`, despite documentation describing it as configurable.
3. The README acknowledges that ankle movement and foot-ground contact differ. Its claim that threshold calibration should fix that bias is not independent validation. Its claim of approximately 2–5 ms error after interpolation is also unsupported by the supplied evaluation materials; JumpLab Pi does not repeat that accuracy claim.
4. Timing is read from OpenCV `CAP_PROP_POS_MSEC` before each read, then threshold crossings are interpolated. A gap validator is present. This does not prove correspondence to physical contact or calibrated capture timing.
5. Personal integration videos are explicitly excluded from the repository. No real-video accuracy test could be reproduced from this snapshot.
6. The backend declares Python >=3.11 and dependencies including FastAPI, OpenCV, Ultralytics and SQLAlchemy. The repository MIT licence does not substitute for checking all transitive packages and pretrained-weight licences if those are ever adopted.

## JumpLab Pi decision

Use an independently implemented manual method with decoded-frame indexing, retained timestamps, explicit contact intervals and conditional bounds. Do not require YOLO, MediaPipe, Torch or external weights. Automatic proposals remain unavailable because no labelled representative recordings or Pi benchmark establish a defensible lightweight detector here. A future foot-region detector would require controlled recording conditions, missing-data reporting, retained proposals and separate tuning/evaluation datasets.

## Camera adapter reference

Official documentation consulted for the optional camera command and timestamp sidecar:
https://www.raspberrypi.com/documentation/computers/camera_software.html

The documentation describes `rpicam-vid` and `--save-pts`, whose sidecar can be used when packaging H.264 into a timed container. Command support depends on the hardware/software stack; this reference does not constitute a successful Pi 3B+ capture test.
