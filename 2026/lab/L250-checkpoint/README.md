# L250: Checkpoint

| Field | Value |
|---|---|
| Challenge # | L250 |
| Title | Checkpoint |
| Category | Lab |
| Difficulty (points) | 250 |
| Status | Tested |
| Delivery | Download |
| Files | [`3d44a3e47901c9c1.tar.gz`](files/3d44a3e47901c9c1.tar.gz) (100.64 kB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

A surveillance database seized before it finished writing. An operator ran a purge on a written order; the deletion was committed but the log never caught up. The table says the record is gone. The write-ahead log disagrees. Handle it wrong and you finish the purge for them.

## Skills

- SQLite WAL-mode forensics
- imaging and working on copies to preserve evidence
- carving deleted rows from a write-ahead log
- using a lead to separate the real record from decoys
- base64 decoding

## Tools that help

the `sqlite3` library for reading (never opening the original), `strings` or a WAL frame parser, `base64`.

---

[Back to Lab](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
