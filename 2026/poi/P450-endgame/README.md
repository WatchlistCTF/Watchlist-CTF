# P450: Endgame

| Field | Value |
|---|---|
| Challenge # | P450 |
| Title | Endgame |
| Category | PoI |
| Difficulty (points) | 450 |
| Status | Tested |
| Delivery | Download |
| Files | [`3b6a10347800c543.zip`](files/3b6a10347800c543.zip) (2.06 MB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

You found her and caught the witness lying. Now finish it. The number given at the start was a lie built to bury the person it named. Put it all together, the cache she carried, the records, the fabricated proof, and tell the Machine who is about to commit a crime, and where, and when. Give it the right number.

## Skills

- synthesizing evidence across a whole arc
- HMAC correlation to tie an anonymous account to a person
- AES-GCM decryption with a derived key
- resisting the trap the evidence was built to spring

## Tools that help

Python with `hmac`, `hashlib` and the `cryptography` package; `sqlite3`; `pdftotext`.

---

[Back to PoI](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
