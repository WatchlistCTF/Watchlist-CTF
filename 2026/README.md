# WATCHLIST CTF: 2026 edition

Every challenge from the WATCHLIST CTF 2026, hosted by [XposedOrNot](https://xposedornot.com) at **[ctf.xposedornot.com](https://ctf.xposedornot.com)**, with its brief, its files and its solution.

The event ran for 24 hours, from 19 September 2026 03:30 UTC to 20 September 2026 03:30 UTC, and is now over. This repository is the archive: 24 challenges across 7 categories, 5560 points in total. Use it to replay the challenges, learn the techniques, or see how they were built.

The theme is *Person of Interest*. Every brief is a message from THE MACHINE, and most reference an episode.

## Event facts

| | |
|---|---|
| Start | 19 September 2026, 03:30 UTC |
| End | 20 September 2026, 03:30 UTC |
| Duration | 24 hours |
| Format | Jeopardy, online, teams of 1 to 6 |
| Platform | [ctf.xposedornot.com](https://ctf.xposedornot.com) |
| CTFtime event and scoreboard | [ctftime.org/event/3326](https://ctftime.org/event/3326) |

## How to use this repo

1. Pick a challenge from the table below and open its `challenge.md`. That is the brief exactly as players saw it, with no spoilers.
2. Get the files from the challenge's `files/` folder. Most files sit in that folder. The three largest (F275, F300, L400) are attached to the [`2026-files` release](https://github.com/WatchlistCTF/Watchlist-CTF/releases/tag/2026-files), named after their challenge.
3. Solve it. Flags look like `number{...}` unless the brief says otherwise.
4. Check yourself against `solution/`. The flag and the walkthrough live there and only there, plus `challenge.yml` and `challenges.csv`.

## Categories

| Category | Challenges | Points | What it covers |
|---|---|---|---|
| [Forensics](forensics/) | 6 | 1525 | Disk images, memory captures, documents and logs. Recover what was deleted, covered or overwritten. |
| [Lab](lab/) | 5 | 1250 | Hands-on targets: live hosts, packet captures and full disk images to walk through. |
| [OSINT](osint/) | 3 | 750 | Open-source intelligence: metadata, public records, archives and flight data. |
| [Recon](recon/) | 2 | 450 | Reconnaissance against live infrastructure: certificates, repositories and provenance trails. |
| [Trivia](trivia/) | 3 | 235 | Short warm-up and sign-off questions. |
| [PoI](poi/) | 3 | 800 | The Person of Interest story arc. Three linked challenges, one case. |
| [Hidden](hidden/) | 2 | 550 | Off-board bonus challenges. Not listed on the scoreboard, found by players who looked where they were not told to. |

## All challenges

| # | Status | Category | Title | Points | Files | Solution |
|---|---|---|---|---|---|---|
| [F100](forensics/F100-carters-note/) | Tested | Forensics | [Carter's Note](forensics/F100-carters-note/challenge.md) | 100 | [`488e9231c060b7c7.zip`](forensics/F100-carters-note/files/488e9231c060b7c7.zip) | [walkthrough](forensics/F100-carters-note/solution/README.md) |
| [F200](forensics/F200-shadow-box/) | Tested | Forensics | [Shadow Box](forensics/F200-shadow-box/challenge.md) | 200 | [`20769767962808ed.pdf`](forensics/F200-shadow-box/files/20769767962808ed.pdf) | [walkthrough](forensics/F200-shadow-box/solution/README.md) |
| [F250](forensics/F250-trap-street/) | Tested | Forensics | [Trap Street](forensics/F250-trap-street/challenge.md) | 250 | [`98e5b6c288ba3672.tar.gz`](forensics/F250-trap-street/files/98e5b6c288ba3672.tar.gz) | [walkthrough](forensics/F250-trap-street/solution/README.md) |
| [F275](forensics/F275-dead-drop/) | Tested | Forensics | [Dead Drop](forensics/F275-dead-drop/challenge.md) | 275 | [`F275-dead-drop.img`](https://github.com/WatchlistCTF/Watchlist-CTF/releases/download/2026-files/F275-dead-drop.img) | [walkthrough](forensics/F275-dead-drop/solution/README.md) |
| [F300](forensics/F300-tmpfs/) | Tested | Forensics | [Tmpfs](forensics/F300-tmpfs/challenge.md) | 300 | [`F300-tmpfs.7z`](https://github.com/WatchlistCTF/Watchlist-CTF/releases/download/2026-files/F300-tmpfs.7z) | [walkthrough](forensics/F300-tmpfs/solution/README.md) |
| [F400](forensics/F400-mirror-sites/) | Tested | Forensics | [Mirror Sites](forensics/F400-mirror-sites/challenge.md) | 400 | [`a093033e707206da.tar.gz`](forensics/F400-mirror-sites/files/a093033e707206da.tar.gz) | [walkthrough](forensics/F400-mirror-sites/solution/README.md) |
| [L100](lab/L100-reduced-footprint/) | Tested | Lab | [Reduced Footprint](lab/L100-reduced-footprint/challenge.md) | 100 | none (live target) | [walkthrough](lab/L100-reduced-footprint/solution/README.md) |
| [L200](lab/L200-signal/) | Tested | Lab | [Signal](lab/L200-signal/challenge.md) | 200 | [`5dde59ee766dcf93.pcap`](lab/L200-signal/files/5dde59ee766dcf93.pcap) | [walkthrough](lab/L200-signal/solution/README.md) |
| [L250](lab/L250-checkpoint/) | Tested | Lab | [Checkpoint](lab/L250-checkpoint/challenge.md) | 250 | [`3d44a3e47901c9c1.tar.gz`](lab/L250-checkpoint/files/3d44a3e47901c9c1.tar.gz) | [walkthrough](lab/L250-checkpoint/solution/README.md) |
| [L300](lab/L300-legion/) | Tested | Lab | [Legion](lab/L300-legion/challenge.md) | 300 | [`a342e7530aec5e66.pcap`](lab/L300-legion/files/a342e7530aec5e66.pcap) | [walkthrough](lab/L300-legion/solution/README.md) |
| [L400](lab/L400-mission-creep/) | Tested | Lab | [Mission Creep](lab/L400-mission-creep/challenge.md) | 400 | [`L400-mission-creep.7z`](https://github.com/WatchlistCTF/Watchlist-CTF/releases/download/2026-files/L400-mission-creep.7z) | [walkthrough](lab/L400-mission-creep/solution/README.md) |
| [O100](osint/O100-cadence/) | Tested | OSINT | [Cadence](osint/O100-cadence/challenge.md) | 100 | [`7ac6142bb8e8c0ea.docx`](osint/O100-cadence/files/7ac6142bb8e8c0ea.docx) | [walkthrough](osint/O100-cadence/solution/README.md) |
| [O250](osint/O250-manifest/) | Tested | OSINT | [Manifest](osint/O250-manifest/challenge.md) | 350 | [`74fbd4e07ff56e85.tar.gz`](osint/O250-manifest/files/74fbd4e07ff56e85.tar.gz) | [walkthrough](osint/O250-manifest/solution/README.md) |
| [O300](osint/O300-aletheia/) | Tested | OSINT | [Aletheia](osint/O300-aletheia/challenge.md) | 300 | none (live target) | [walkthrough](osint/O300-aletheia/solution/README.md) |
| [R150](recon/R150-ghosts/) | Tested | Recon | [Ghosts](recon/R150-ghosts/challenge.md) | 150 | none (live target) | [walkthrough](recon/R150-ghosts/solution/README.md) |
| [R300](recon/R300-razgovor/) | Tested | Recon | [Razgovor](recon/R300-razgovor/challenge.md) | 300 | none (live target) | [walkthrough](recon/R300-razgovor/solution/README.md) |
| [T10](trivia/T10-check-in/) | Tested | Trivia | [Check-In](trivia/T10-check-in/challenge.md) | 10 | none (live target) | [walkthrough](trivia/T10-check-in/solution/README.md) |
| [T100](trivia/T100-satoshi/) | Tested | Trivia | [Satoshi](trivia/T100-satoshi/challenge.md) | 100 | none (live target) | [walkthrough](trivia/T100-satoshi/solution/README.md) |
| [T125](trivia/T125-rfc-2324/) | Tested | Trivia | [RFC 2324](trivia/T125-rfc-2324/challenge.md) | 125 | none (live target) | [walkthrough](trivia/T125-rfc-2324/solution/README.md) |
| [P100](poi/P100-pilot/) | Tested | PoI | [Pilot](poi/P100-pilot/challenge.md) | 100 | [`1f97c207100afb1e.zip`](poi/P100-pilot/files/1f97c207100afb1e.zip) | [walkthrough](poi/P100-pilot/solution/README.md) |
| [P250](poi/P250-witness/) | Tested | PoI | [Witness](poi/P250-witness/challenge.md) | 250 | [`26bf84684d31d6f7.zip`](poi/P250-witness/files/26bf84684d31d6f7.zip) | [walkthrough](poi/P250-witness/solution/README.md) |
| [P450](poi/P450-endgame/) | Tested | PoI | [Endgame](poi/P450-endgame/challenge.md) | 450 | [`3b6a10347800c543.zip`](poi/P450-endgame/files/3b6a10347800c543.zip) | [walkthrough](poi/P450-endgame/solution/README.md) |
| [B200](hidden/B200-bad-code/) | Tested | Lab (hidden) | [Bad Code](hidden/B200-bad-code/challenge.md) | 200 | none (live target) | [walkthrough](hidden/B200-bad-code/solution/README.md) |
| [B350](hidden/B350-contingency/) | Tested | Forensics (hidden) | [Contingency](hidden/B350-contingency/challenge.md) | 350 | none (live target) | [walkthrough](hidden/B350-contingency/solution/README.md) |

The same table, with flags and full descriptions, is in [`challenges.csv`](challenges.csv). The number in a challenge ID is a label, not the score: O250 is worth 350 points.

## Repository layout

```text
2026/
├── README.md              this page
├── challenges.csv         master sheet (contains flags)
├── forensics/             one folder per category
│   ├── README.md          category index
│   └── F100-carters-note/ one folder per challenge
│       ├── README.md      overview and metadata
│       ├── challenge.md   the brief, spoiler-free
│       ├── challenge.yml  ctfcli spec (contains the flag)
│       ├── files/         challenge files or download reference
│       ├── solution/      flag and walkthrough
│       └── build/         generator and test scripts
├── lab/  osint/  recon/  trivia/  poi/  hidden/
```

## Live infrastructure

Some challenges ran against live hosts and services (SSH targets, a submission board, web endpoints, seeded public repos). Those may be offline now. Where a challenge needed one, its `files/` folder says what is required to stand it up again.

## Links

- All editions: [WATCHLIST CTF](../README.md)
- CTF platform: [ctf.xposedornot.com](https://ctf.xposedornot.com)
- CTFtime event and scoreboard: [ctftime.org/event/3326](https://ctftime.org/event/3326)
- XposedOrNot: [xposedornot.com](https://xposedornot.com)

