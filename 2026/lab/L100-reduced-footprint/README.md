# L100: Reduced Footprint

| Field | Value |
|---|---|
| Challenge # | L100 |
| Title | Reduced Footprint |
| Category | Lab |
| Difficulty (points) | 100 |
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

A node its owners called decommissioned, reachable over a read-only SSH seat. Something on it still wakes on a schedule. Three things look like they belong and two of them do; the third keeps the intruder resident. Find it, and the key is inside.

## Skills

- reading Linux persistence: cron, profile scripts, systemd services and timers
- telling a real service from a planted one
- following a service's ExecStart to its payload
- spotting hidden dot-directories
- base64 decoding

## Tools that help

an SSH client, and ordinary shell commands (`ls -a`, `cat`, `systemctl`, `base64`).

---

[Back to Lab](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
