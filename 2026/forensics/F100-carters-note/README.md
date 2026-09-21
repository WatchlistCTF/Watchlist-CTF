# F100: Carter's Note

| Field | Value |
|---|---|
| Challenge # | F100 |
| Title | Carter's Note |
| Category | Forensics |
| Difficulty (points) | 100 |
| Status | Tested |
| Delivery | Download |
| Files | [`488e9231c060b7c7.zip`](files/488e9231c060b7c7.zip) (25.98 MB) |

## What is in this folder

| Path | Purpose |
|---|---|
| [`challenge.md`](challenge.md) | The brief exactly as players saw it on the board. Spoiler-free. |
| [`challenge.yml`](challenge.yml) | The same challenge in ctfcli format, ready to load into CTFd. Contains the flag. |
| [`files/`](files/) | Challenge files handed to players, or the download reference for large ones. |
| [`solution/`](solution/) | Flag and full walkthrough. Spoilers. |
| [`build/`](build/) | Scripts that generate and test the challenge. |

## Summary

A dead detective's USB drive, imaged. Joss Carter deleted five files before she was killed: three are cover, two hold the work. Recover them all, read past the decoys, and reassemble a number she split on purpose. This is the gateway challenge, and its real lesson is that "recovered" is not the same as "relevant".

## Skills

- FAT32 filesystem layout
- recovering deleted files from unallocated space
- triage: telling operational files from decoys
- base64 decoding
- reassembling a secret split across two files

## Tools that help

The Sleuth Kit (`fls`, `icat`), a loopback mount, `base64`, any hex viewer. Autopsy covers the same ground on Windows or macOS.

---

[Back to Forensics](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
