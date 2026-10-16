# Interface screenshots

Captured from the running application in a headless desktop Chromium browser using the bundled synthetic example. These are software UI checks, not Pi or human-jump measurements.

- `01-empty-workspace.png`: initial import-ready workspace.
- `02-reviewed-demo-desktop.png`: selected contact frames, 500 ms estimate and Reviewed state.
- `03-mobile-layout.png`: narrow layout after a deliberately failed import, showing that the earlier trial and result remain available.
- `04-timing-diagnostics.png`: expanded timing provenance and review information.

Start the actual local interface with `python3 -m jumplab.server`, then open `http://127.0.0.1:8765` on the same computer. Screenshots are static; the application is interactive.
