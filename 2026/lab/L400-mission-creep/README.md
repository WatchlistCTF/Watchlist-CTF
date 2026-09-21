# L400: Mission Creep

| Field | Value |
|---|---|
| Challenge # | L400 |
| Title | Mission Creep |
| Category | Lab |
| Difficulty (points) | 400 |
| Status | Tested |
| Delivery | Download |
| Files | [`L400-mission-creep.7z`](https://github.com/WatchlistCTF/Watchlist-CTF/releases/download/2026-files/L400-mission-creep.7z) (1.07 GB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

A compromised relay, taken offline, its disk imaged. One unlocked door became a habit, a key, then the whole house. Walk it forward: where they got in, how they stayed, how they became root, and what they carried out. The last of those is the flag.

## Skills

- disk-image mounting and super-timeline building
- tracing an intrusion stage by stage
- finding a webshell in web logs
- spotting a malicious systemd timer among legitimate ones
- detecting a trojaned system binary against package records
- reading a cover-up: wiped logs as evidence
- recovering data from a core dump

## Tools that help

`guestmount` or loopback with LVM, The Sleuth Kit (`fls`, `mactime`), `dpkg --verify` or `debsums`, `strings`, `gdb`.

---

[Back to Lab](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
