# F200: Shadow Box

| Field | Value |
|---|---|
| Challenge # | F200 |
| Title | Shadow Box |
| Category | Forensics |
| Difficulty (points) | 200 |
| Status | Tested |
| Delivery | Download |
| Files | [`20769767962808ed.pdf`](files/20769767962808ed.pdf) (2.37 MB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

A Decima memo, saved three times to launder what it says. Nothing is hidden as plain text. The flag is assembled from three findings, each buried in a different layer of the PDF that a later save tried to paper over.

## Skills

- PDF incremental-update forensics
- reading superseded revisions and metadata history
- recovering orphaned objects removed from the page tree
- spotting embedded JavaScript and OpenAction
- assembling a flag from separate forensic findings

## Tools that help

poppler (`pdfinfo`, `pdftotext`, `pdfimages`), Didier Stevens' `pdfid.py` and `pdf-parser.py`, a JPEG viewer or `tesseract`.

---

[Back to Forensics](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
