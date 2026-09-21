# F275: Dead Drop

| Field | Value |
|---|---|
| Challenge # | F275 |
| Title | Dead Drop |
| Category | Forensics |
| Difficulty (points) | 275 |
| Status | Tested |
| Delivery | Download |
| Files | [`F275-dead-drop.img`](https://github.com/WatchlistCTF/Watchlist-CTF/releases/download/2026-files/F275-dead-drop.img) (67.11 MB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

A wiped USB left behind in a cleared safehouse. It looks empty on the surface; it is not. Windows shortcuts on it remember the machine, the user and its network card, and a second partition hides the case number. The flag is a hash of what the drive gives up.

## Skills

- partition-table analysis
- Windows LNK (shortcut) forensics, including the tracker block and MAC address
- detecting timestamp stomping
- carving a file by signature from unallocated space
- finding and mounting a hidden partition
- deriving a keyed hash from recovered values

## Tools that help

`mmls` (Sleuth Kit), a loopback mount, LnkParse3, `foremost` or a signature scan, `7z`, `sha256sum`.

---

[Back to Forensics](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
