# T100: Satoshi

| Field | Value |
|---|---|
| Challenge # | T100 |
| Title | Satoshi |
| Category | Trivia |
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

On the day the Machine was first tested, another system was being born. On 3 January 2009 its anonymous creator embedded a newspaper headline in his first transmission, a comment on the institutions that had failed. Find the sentence, hash it, and give the Machine the first sixteen hex characters.

## Skills

- recognizing the Bitcoin genesis block from a description
- finding the exact embedded coinbase text
- SHA-256 hashing with byte-exact input

## Tools that help

any SHA-256 tool (`sha256sum`), and a primary source for the exact sentence.

---

[Back to Trivia](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
