# R150: Ghosts

| Field | Value |
|---|---|
| Challenge # | R150 |
| Title | Ghosts |
| Category | Recon |
| Difficulty (points) | 150 |
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

Northern Lights ran more relays than anyone admits, and tore most down: records pulled, links cut, names scrubbed. They forgot the one thing they never controlled. Every node that spoke securely had to ask a public authority for a certificate, and that request is witnessed forever. One relay is a ghost now. The ledger still remembers its name.

## Skills

- Certificate Transparency as a reconnaissance source
- subdomain enumeration from CT logs
- probing a set of hosts to find the one that still answers

## Tools that help

`subfinder`, `crt.sh` or the Cert Spotter API, `curl` or a browser.

---

[Back to Recon](../README.md) · [All challenges](../../README.md) · [ctf.xposedornot.com](https://ctf.xposedornot.com)
