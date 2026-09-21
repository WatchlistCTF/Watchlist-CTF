# L250: Checkpoint (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{the_log_remembers_what_the_table_forgot}
```

## In short

A record was deleted from a SQLite database, but the database was seized before it tidied up its write-ahead log (the WAL file). The deleted record is still sitting in that log. The catch: opening the database the normal way makes SQLite merge the log and destroys the evidence.

## Walkthrough

1. Unpack the archive. You get `surveillance.db`, `surveillance.db-wal`, `surveillance.db-shm` and `EVIDENCE_README.txt`.
2. Read the readme first. It warns you not to open the database in a normal SQLite client, because doing so checkpoints the WAL and finishes the purge.
3. Work on copies, and look at the main database without triggering a checkpoint (open it read-only or immutable, or just read copies). All 1,888 subjects are marked IRRELEVANT.
4. Read the `analyst_log` table. It records the purge order, dated 2026-09-19 and given by handler Greer: erase the asset flagged RELEVANT before seizure. The target's designation ends in `0001`, and all the others are cover.
5. Do not query for it. Read the WAL file directly. Running `strings` over `surveillance.db-wal` and looking for "RELEVANT" while excluding "IRRELEVANT" is enough.
6. One record turns up, repeated several times because the log keeps a copy of the page for each write: `PRIMARY`, `000-00-0001`, `RELEVANT`, `CRITICAL`, `2026-09-19`, followed by a base64 string in the intel field. The purge order itself also shows up in the search.
7. Base64-decode that field. It gives `the_log_remembers_what_the_table_forgot`. Wrap it in `number{}`.

## Watch out for

- The trap is real, and we tested it. One ordinary open and close of `surveillance.db` deleted the WAL file outright. After that the record was gone from the log and was not in the main database either. Keep an untouched copy of the archive.
- In the `strings` output the fields run together with no separators, and one stray character is stuck to the end of the base64 text. If your decode complains about invalid input, drop the last character.
- The `.db-shm` file is only an index. You can ignore it.
- No special tool is needed. `strings` on the WAL is the simplest route.

## Solver

[`solve_l250.py`](solve_l250.py) reads the WAL with its own small parser, so it depends on no forensic tool. It applies the lead from the analyst log, decodes the intel field and runs 12 checks.

- Unpack the challenge file from [`../files/`](../files/) first, then pass the `checkpoint_evidence/` folder to the script.
- It needs only the Python 3 standard library. No network access or live server is needed.
- It works on a temporary copy and never opens your originals.
- It knows no answers in advance. It reads the `0001` lead from the analyst log, and the flag text comes out of the decoded field.
