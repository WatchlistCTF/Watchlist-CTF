# O100: Cadence

| Field | Value |
|---|---|
| Challenge # | O100 |
| Title | Cadence |
| Category | OSINT |
| Difficulty (points) | 100 |
| Status | Tested |
| Delivery | Download |
| Files | [`7ac6142bb8e8c0ea.docx`](files/7ac6142bb8e8c0ea.docx) (37.31 kB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

A Decima compliance memo, signed by the right person in the right tone, saying nothing. The name on it did not write it. Read what the software recorded while someone typed, the author, the machine, the hour, and the line they deleted before release.

## Skills

- OOXML (.docx) internals: it is a zip of XML
- reading document metadata: creator, last-saved-by, template path
- recognizing a service account and a byline as decoys
- recovering deleted text from tracked changes

## Tools that help

`exiftool`, `unzip`, and any text viewer for `word/document.xml`.

---

[Back to OSINT](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
