# L200: Signal

| Field | Value |
|---|---|
| Challenge # | L200 |
| Title | Signal |
| Category | Lab |
| Difficulty (points) | 200 |
| Status | Tested |
| Delivery | Download |
| Files | [`5dde59ee766dcf93.pcap`](files/5dde59ee766dcf93.pcap) (1.64 MB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

A full day of DNS from inside Aletheia, captured. Folded into ten hours of ordinary lookups, an implant called out and something answered. Read the traffic, rebuild what it was told, and ask the same question it did.

## Skills

- DNS traffic analysis in a large capture
- carving chunked, sequenced data out of TXT records
- reassembling and reading an exfiltrated script without running it
- recovering a key sent one character per subdomain label
- querying a C2 endpoint and decoding its reply

## Tools that help

Wireshark or `tshark`, `base64`, `curl`.

---

[Back to Lab](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
