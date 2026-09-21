# P250: Witness

| Field | Value |
|---|---|
| Challenge # | P250 |
| Title | Witness |
| Category | PoI |
| Difficulty (points) | 250 |
| Status | Tested |
| Delivery | Download |
| Files | [`26bf84684d31d6f7.zip`](files/26bf84684d31d6f7.zip) (687.49 kB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

A manager comes forward: calm, specific, certain that she stalked and threatened him and invented her evidence. He gave exact times. The Machine does not deal in stories, it deals in records, and records do not care what anyone is certain of. Check the times. Find where the story and the clock disagree.

## Skills

- multi-source timeline reconstruction
- querying a large badge database with SQL
- reading mbox headers to place someone
- EXIF metadata to date a fabricated exhibit

## Tools that help

the `sqlite3` client, a mail reader or `grep` over the mbox, `exiftool`.

---

[Back to PoI](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
