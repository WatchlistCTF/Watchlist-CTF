# O300: Aletheia

| Field | Value |
|---|---|
| Challenge # | O300 |
| Title | Aletheia |
| Category | OSINT |
| Difficulty (points) | 300 |
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

Aletheia Research published more than they meant to, then cleaned house. The site today is spotless. But the page was edited and the past was not. Find what they took down; it points to a file wrapped, and wrapped, and wrapped again, in every format they could find, including some you have to go and build yourself.

## Skills

- Wayback Machine and archive.today history recovery
- the Wayback CDX API
- identifying compression formats by magic bytes, not extension
- peeling deeply nested archives by script
- recognizing base64 and ascii85 as layers
- building obscure compressors from source

## Tools that help

the Wayback CDX API, `file` / `od`, the standard compressors, and four built from source (zpaq, lzfse, bsc, snzip).

---

[Back to OSINT](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
