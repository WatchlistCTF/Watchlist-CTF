# L250 build

`generate_l250.py` builds the SQLite evidence trio: a `subjects` table of 1,888 decoys, an `analyst_log` with the purge order, and a deleted RELEVANT record left recoverable in the write-ahead log (`.db-wal`). Output goes to `out/` by default (`OUT=` / `WORK=` override).

The shipped download is `checkpoint_evidence.tar.gz`, already in this challenge's `files/`.
