# O250: Manifest

| Field | Value |
|---|---|
| Challenge # | O250 |
| Title | Manifest |
| Category | OSINT |
| Difficulty (points) | 350 |
| Status | Tested |
| Delivery | Download |
| Files | [`74fbd4e07ff56e85.tar.gz`](files/74fbd4e07ff56e85.tar.gz) (409.80 kB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

A week of a metro's aircraft position broadcasts. Most is couriers and charters flying the same boring triangles. Twice, on two days, an aircraft went somewhere it did not file and then went in circles. Two tails, one story: they were watching the same ground, and that ground is on no list.

## Skills

- parsing large ADS-B position data by scripting
- detecting circular orbits from noisy points
- telling surveillance from a holding pattern by altitude profile
- cross-day, cross-aircraft correlation
- orbit-centroid geometry
- decoding data hidden in squawk codes and callsigns
- keying a coordinate into a grid registry

## Tools that help

Python (`json`, `csv`, `math`, `statistics`). No special tooling.

---

[Back to OSINT](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
