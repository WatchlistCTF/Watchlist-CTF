# F400: Mirror Sites

| Field | Value |
|---|---|
| Challenge # | F400 |
| Title | Mirror Sites |
| Category | Forensics |
| Difficulty (points) | 400 |
| Status | Tested |
| Delivery | Download |
| Files | [`a093033e707206da.tar.gz`](files/a093033e707206da.tar.gz) (23.31 MB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

A senior engineer moved a client dataset across three clouds in one night, renaming it at every hop and cleaning up behind them. No single provider saw the whole thing, the logs disagree, and they do not even share a clock. But the object carried the same fingerprint everywhere it went. Reconstruct the night and prove it was one object, one person, three clouds.

## Skills

- multi-cloud log analysis across AWS, Azure and GCP
- telling control-plane audit logs from data-plane access logs
- joining records by content hash across three formats
- timeline reconstruction across time zones
- defeating a cover-up: object versioning and soft-delete
- assembling ordered fragments

## Tools that help

Python (`json`, `csv`) and patience. No special tooling.

---

[Back to Forensics](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
