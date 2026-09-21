# WATCHLIST CTF

The challenge archive for WATCHLIST CTF, the capture-the-flag event run by [XposedOrNot](https://xposedornot.com) at **[ctf.xposedornot.com](https://ctf.xposedornot.com)**.

Every challenge from every edition is kept here with three things: the brief as players saw it, the files they were given, and a full solution. Replay the challenges cold, study the techniques, or see how they were built.

The theme is *Person of Interest*. Every brief is a message from THE MACHINE.

## Editions

| Edition | When | Challenges | Points | Categories | Scoreboard | Status |
|---|---|---|---|---|---|---|
| [2026](2026/) | 19 Sep 2026 03:30 UTC to 20 Sep 2026 03:30 UTC | 24 | 5560 | Forensics, Lab, OSINT, Recon, Trivia, PoI, Hidden | [CTFtime](https://ctftime.org/event/3326) | Event over. Writeups in progress. |

## How to use this repo

1. Open an edition and pick a challenge from its table.
2. Read `challenge.md`. It is the original brief and carries no spoilers.
3. Get the files from the challenge's `files/` folder. Most files sit in that folder. The three largest (F275, F300, L400) are attached to the [`2026-files` release](https://github.com/WatchlistCTF/Watchlist-CTF/releases/tag/2026-files), named after their challenge.
4. Solve it, then compare with `solution/`. Flags and walkthroughs live there.

## Repository layout

```text
.
├── README.md              this page
├── LICENSE                MIT, for code
├── LICENSE-CONTENT        CC BY 4.0, for written content
├── 2026/                  one folder per edition
│   ├── README.md          edition overview and master challenge table
│   ├── challenges.csv     master sheet (contains flags)
│   ├── forensics/         one folder per category, one subfolder per challenge
│   └── lab/  osint/  recon/  trivia/  poi/  hidden/
```

## A note

I designed, built, hosted, and ran WATCHLIST on my own: the challenges, the infrastructure, and the moderation while the event was live. I mention it only for context, not credit. It is why the rough edges are mine, and why putting the whole thing in the open here felt like the right way to close it out.

If you played, thank you. I hope something in here stays useful to you long after the scoreboard closed.

**Devanand Premkumar**, founder of XposedOrNot  
[xposedornot.com](https://xposedornot.com) · [@DevaOnBreaches](https://github.com/DevaOnBreaches)

## Links

- CTF platform: [ctf.xposedornot.com](https://ctf.xposedornot.com)
- CTFtime: [ctftime.org/event/3326](https://ctftime.org/event/3326)
- XposedOrNot: [xposedornot.com](https://xposedornot.com)

## License

Two licenses, split by what the file is:

| What | License | In short |
|---|---|---|
| Code: build scripts, generators, solvers, `challenge.yml` | [MIT](LICENSE) | Use it, change it, ship it. Keep the copyright notice. |
| Written content: briefs, walkthroughs, design notes, READMEs | [CC BY 4.0](LICENSE-CONTENT) | Reuse and adapt it, including in your own CTF or training. Credit "WATCHLIST CTF by XposedOrNot" and link back to this repo. |

Challenge files hosted outside the repo fall under the same CC BY 4.0 terms.

WATCHLIST is a fan tribute to *Person of Interest*. It is not affiliated with or endorsed by the show's creators or rights holders, and the licenses above cover only our original material, not the show's names, characters or episode titles.

## Contact

Found a broken link, a wrong checksum or a mistake in a walkthrough? [Open an issue](https://github.com/WatchlistCTF/Watchlist-CTF/issues). That is the one place we track corrections, so everyone sees the fix.
