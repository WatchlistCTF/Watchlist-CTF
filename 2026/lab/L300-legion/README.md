# L300: Legion

| Field | Value |
|---|---|
| Challenge # | L300 |
| Title | Legion |
| Category | Lab |
| Difficulty (points) | 300 |
| Status | Tested |
| Delivery | Download |
| Files | [`a342e7530aec5e66.pcap`](files/a342e7530aec5e66.pcap) (2.85 MB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

One capture, a hundred small machines checking in to a single hub, buried in the noise of a thousand that do not matter. Alone each is nothing; together they are a net. Pull them apart, name all hundred, and the number is yours. You will not do this by hand.

## Skills

- large pcap triage: finding a high fan-in destination
- separating periodic beacons from irregular noise by timing
- measuring timing regularity (coefficient of variation)
- XOR decoding a payload
- scripting a bulk submission against a live board

## Tools that help

`scapy` or `tshark` with Python, `numpy` for the timing math, an HTTP client and `nc`.

---

[Back to Lab](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
