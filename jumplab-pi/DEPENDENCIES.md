# Dependencies and versions

| Component | Requirement / tested environment |
|---|---|
| Application | JumpLab Pi 0.1.0; schema 1 |
| Runtime Python | Standard library only; intended Python >=3.9; tested 3.12.14 |
| Video tools | `ffmpeg` and `ffprobe` on PATH; tested FFmpeg 6.1.1-3ubuntu5 |
| Browser | Modern browser with ES2021 support; tested headless Chromium 153.0.8010.0; bundled HTML/CSS/JS, no CDN |
| Camera (optional) | `rpicam-vid` or `libcamera-vid`, CSI camera; actual Pi/OS/camera compatibility pending |
| Sample regeneration only | Pillow and FFmpeg with libx264; sample already bundled |
| Browser testing only | Tested Node.js 24.19.0 / Playwright 1.62.1; not installed or used by the application |

No pip installation is needed to launch the app or run its Python tests. No machine-learning runtime is required. FFmpeg's installed build and external camera tools retain their own licences; these binaries are not redistributed in the project ZIP.

Optional developer setup:

```bash
npm install --no-save playwright
npx playwright install chromium
python3 -m jumplab.server --data /tmp/jumplab-test-data
# In another terminal, in this project directory:
node tests/browser.cjs
```

The browser test creates synthetic trials and screenshots. Run it against a disposable data directory on a machine without a CSI camera; its no-camera assertion intentionally expects import mode. `JUMPLAB_URL` can change the local test URL.
