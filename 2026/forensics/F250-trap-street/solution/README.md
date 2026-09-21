# F250: Trap Street (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{shaw_followed_the_breadcrumbs}
```

## In short

The download is a real honeypot's logs: more than two months of mostly bot traffic. One session belongs to a human who knew what they wanted. Find that session, follow the file they downloaded, and the file itself tells you where to go for the flag.

## Walkthrough

1. Unpack the archive. You get a `README.txt` that repeats the brief, `logs/` (62 daily Cowrie JSON logs, about 234,000 lines), `tty/` (310 session recordings) and `downloads/` (17 files that sessions pulled down, each named by its SHA-256 hash).
2. Do not read the logs by hand. Load the JSON and group the typed commands by session id. There are over 22,000 sessions.
3. Filter for behaviour that bots do not show:
   - commands that mention `decima`, `personnel` or `transit` (a bot does not care about those words),
   - a `history -c` before leaving (bots never clean up after themselves),
   - gaps of a few seconds between commands (a person thinking, not a script).
4. Only one session matches all of that: `68688776fe89`. The visitor logs in, runs a few quick checks (`whoami`, `id`, `uname -a`, `ls /root`), downloads one file with `wget`, clears the history and leaves in about a minute.
5. Read the `wget` line. It gives the full address of the canary file, `decima_q4_personnel.xlsx`, including a long random token in the path that you could not have guessed.
6. Get the spreadsheet from that address. It is also one of the 17 files in `downloads/`, where 16 are small Excel files that look alike. The one Shaw took is the largest of them, and downloading from her address settles which. It looks like an ordinary personnel list.
7. Look for what is hidden. Cells A30 to A33 hold text in white on a white background, and A35 joins them with a formula. Select all and change the font colour to black, or unzip the xlsx and read `xl/worksheets/sheet1.xml`.
8. The joined pieces form a check-in address on the `transit` host, ending in `/checkin?id=NLA-2026-04`.
9. Request that address. The reply is JSON saying the canary was acknowledged, and it carries the flag.

## Watch out for

- The flag is not in the logs. Searching them for `number{` finds nothing, so the triage is unavoidable.
- The check-in endpoint only answers to the right id. A wrong id returns no flag.
- Crypto miners and botnet installers also use `wget`. What sets Shaw apart is what she went looking for and that she cleaned up.

## Solver

[`solve_f250.py`](solve_f250.py) runs the same four acts and checks each one.

- Unpack the challenge file from [`../files/`](../files/) first, then pass the `trap_street/` folder to the script.
- It needs only Python 3. With `openpyxl` installed it also rebuilds the hidden address from the spreadsheet cells. Without it, it reads the pieces from the sheet's XML.
- Acts 1 and 2 work offline. Acts 3 and 4 talk to the live worker on the `transit` host. If that worker is ever taken down, those acts fail and the script says so. It never prints a flag it did not receive.
- Writing your own script for the last step? Send a browser-style User-Agent. The host sits behind Cloudflare, which rejects Python's default one with error 1010.
