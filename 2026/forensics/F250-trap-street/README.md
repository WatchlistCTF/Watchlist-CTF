# F250: Trap Street

| Field | Value |
|---|---|
| Challenge # | F250 |
| Title | Trap Street |
| Category | Forensics |
| Difficulty (points) | 250 |
| Status | Tested |
| Delivery | Download |
| Files | [`98e5b6c288ba3672.tar.gz`](files/98e5b6c288ba3672.tar.gz) (7.38 MB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

Seventy days of honeypot logs, almost all of it automated noise. One human visitor knew exactly what they wanted. Find their session by how it behaves, recover the canary file they took, and follow what the file hides to the endpoint that gives them away.

## Skills

- large-scale log triage by script, not by eye
- behavioural fingerprinting: human tradecraft versus bot noise
- recovering a downloaded artifact from capture data
- finding content hidden by formatting inside a spreadsheet
- following a recovered callback to a live endpoint

## Tools that help

`jq` or Python for the JSON logs, a spreadsheet app or `unzip` for the xlsx, `curl`.

---

[Back to Forensics](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
