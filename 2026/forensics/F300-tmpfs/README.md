# F300: Tmpfs

| Field | Value |
|---|---|
| Challenge # | F300 |
| Title | Tmpfs |
| Category | Forensics |
| Difficulty (points) | 300 |
| Status | Tested |
| Delivery | Download |
| Files | [`F300-tmpfs.7z`](https://github.com/WatchlistCTF/Watchlist-CTF/releases/download/2026-files/F300-tmpfs.7z) (407.02 MB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

A safehouse memory capture, taken while the operative was still at the keyboard. He erased his encrypted vault from disk, but the process holding it was alive and the pages were still in RAM. His key was split across two places. Recover both halves, carve the vault out of memory, and decrypt it.

## Skills

- Linux memory forensics with Volatility 3
- process triage: the work versus operating-system noise
- reading a process's environment and command line
- recovering a deleted-but-open file from process memory
- recovering shell history from RAM
- AES-128-CBC decryption

## Tools that help

Volatility 3 with the supplied symbol table, `openssl`, `python`. `7z` and `xz` to unpack.

---

[Back to Forensics](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
