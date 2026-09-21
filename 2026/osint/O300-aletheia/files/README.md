# O300 files

This challenge had no packaged download. It ran against a live static site plus the Wayback Machine.

## To stand it up again

- A GitHub Pages site (`aletheia-research.github.io`) whose current pages are clean, with an older snapshot in the Wayback Machine that still shows the removed `press.html` and disclosure PDF.
- The PDF points at `data/artifact`, the 42-layer nested file players peel.
- Build: `o300_build.py` regenerates the exact artifact stack (it needs the same toolchain as the solver, including the four source-built compressors).
- The build script will live in this challenge's `build/` folder.
