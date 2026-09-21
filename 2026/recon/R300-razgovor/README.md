# R300: Razgovor

| Field | Value |
|---|---|
| Challenge # | R300 |
| Title | Razgovor |
| Category | Recon |
| Difficulty (points) | 300 |
| Status | Tested |
| Delivery | Live / no download |
| Files | none (live target) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

A tool leaked out of Decima, made 'clean' in a hurry, and left public as if nothing happened. Whoever scrubbed it was careless: every artifact remembers where it came from and points, quietly, at the next one. Start with what they published and follow what it is still saying.

## Skills

- reading git history for scrubbed secrets
- following a chain of artifacts across services
- recovering data from image EXIF and embedded thumbnails
- recovering routes from a JavaScript source map or an exposed .git

## Tools that help

`git` (log, reflog), `gitleaks`, `exiftool`, a browser's dev tools.

---

[Back to Recon](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
