# T125: RFC 2324

| Field | Value |
|---|---|
| Challenge # | T125 |
| Title | RFC 2324 |
| Category | Trivia |
| Difficulty (points) | 125 |
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

An old, particular device on the network that makes coffee. It will not answer a browser and it will not answer the wrong request. It follows a standard written long ago, more carefully than the people who wrote it intended. Ask it properly and it pours; ask it wrong and it reminds you what it is.

## Skills

- reading an RFC and speaking its protocol
- HTTP methods, headers and bodies beyond a browser's defaults
- RFC 2324 (HTCPCP), the 418 status

## Tools that help

`curl` (to set a custom method, header and body).

---

[Back to Trivia](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
