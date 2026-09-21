#!/usr/bin/env python3
# WATCHLIST CTF - L250 "Checkpoint" generator.
# Produces a SQLite WAL trio where the only RELEVANT record was inserted+deleted
# ENTIRELY within the uncheckpointed WAL tail (so it lives only in the -wal),
# plus near-miss decoys and an analyst-log lead. Packages checkpoint_evidence.tar.gz.
import sqlite3, os, base64, random, shutil, tarfile
random.seed(250)

OUT=os.environ.get("OUT","out"); os.makedirs(OUT,exist_ok=True)
WORK=os.environ.get("WORK","work"); shutil.rmtree(WORK,ignore_errors=True); os.makedirs(WORK)
DB=os.path.join(WORK,"surveillance.db")

FLAG_CONTENT="the_log_remembers_what_the_table_forgot"
b64=lambda s:base64.b64encode(s.encode()).decode()
junk=lambda n=24:base64.b64encode(os.urandom(n)).decode()   # decodes to non-text bytes

aliases=["NIGHTjar","KESTREL","MAGPIE","LINNET","SISKIN","REDPOLL","TWITE","BRAMBLING","FIRECREST",
         "WAXWING","CROSSBILL","DUNNOCK","WHIMBREL","GODWIT","TURNSTONE","SANDERLING","KNOT","RUFF"]
def rand_alias(): return random.choice(aliases)+"-"+str(random.randint(100,999))

con=sqlite3.connect(DB)
con.execute("PRAGMA page_size=4096")
con.execute("PRAGMA journal_mode=WAL")
con.execute("PRAGMA wal_autocheckpoint=0")
con.execute("""CREATE TABLE subjects(
  id INTEGER PRIMARY KEY, alias TEXT, ssn TEXT, status TEXT,
  priority TEXT, last_seen TEXT, intel TEXT)""")
con.execute("CREATE TABLE analyst_log(ts TEXT, entry TEXT)")
con.commit()

# ---- 1. checkpointed BULK: ~1700 IRRELEVANT subjects, periodic checkpoints ----
sid=1
for batch in range(40):
    rows=[]
    for _ in range(50):
        rows.append((sid, rand_alias(), f"{random.randint(100,899)}-{random.randint(10,99)}-{random.randint(1000,9999)}",
                     "IRRELEVANT", random.choice(["LOW","MEDIUM","LOW","LOW"]),
                     f"2026-0{random.randint(1,8)}-{random.randint(10,28)}", junk()))
        sid+=1
    con.executemany("INSERT INTO subjects VALUES(?,?,?,?,?,?,?)",rows)
    # delete a few decoys mid-bulk (normal churn), then checkpoint so bulk lands in main db
    if batch%3==0:
        con.execute("DELETE FROM subjects WHERE id IN (SELECT id FROM subjects ORDER BY RANDOM() LIMIT 8)")
    con.commit()
    if batch%4==0:
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
# FINAL checkpoint -> clean populated baseline
con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
con.commit()
bulk_count=con.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
relevant_in_main=con.execute("SELECT COUNT(*) FROM subjects WHERE status='RELEVANT'").fetchone()[0]
print(f"baseline: {bulk_count} subjects in main db, RELEVANT={relevant_in_main}")

# ============ UNCHECKPOINTED TAIL (no checkpoint after this point) ============
# 2. the LEAD (committed, never deleted -> visible to a read-only query)
con.execute("INSERT INTO analyst_log VALUES(?,?)",
    ("2026-09-19T03:09Z","INTAKE: node seized mid-write. WAL not flushed. Handle as evidence."))
con.execute("INSERT INTO analyst_log VALUES(?,?)",
    ("2026-09-19T03:11Z","PURGE DIRECTIVE (handler GREER): erase the asset flagged RELEVANT before seizure. "
                          "Target designation ends 0001. All others are cover."))
con.commit()

# 3. near-miss decoys + ordinary decoys, all insert+delete in the tail
target_id=999001
nearmiss=[
 (999002,"PRIMARY-2","000-00-0002","IRRELEVANT","CRITICAL","2026-09-18",junk()),   # looks urgent (CRITICAL) but IRRELEVANT
 (999003,"OVERWATCH","000-00-0009","IRRELEVANT","HIGH","2026-09-19",junk()),        # recent + HIGH, still not it
 (999004,"PRIMARY","000-00-7777","IRRELEVANT","HIGH","2026-09-19",junk()),          # same alias 'PRIMARY' but wrong ssn/status
]
ordinary=[(999010+i, rand_alias(), f"{random.randint(100,899)}-{random.randint(10,99)}-{random.randint(1000,9999)}",
           "IRRELEVANT","LOW","2026-08-15",junk()) for i in range(12)]
for r in nearmiss+ordinary:
    con.execute("INSERT INTO subjects VALUES(?,?,?,?,?,?,?)",r); con.commit()

# 4. THE TARGET: the one RELEVANT row, designation ...0001, intel decodes to English
con.execute("INSERT INTO subjects VALUES(?,?,?,?,?,?,?)",
    (target_id,"PRIMARY","000-00-0001","RELEVANT","CRITICAL","2026-09-19", b64(FLAG_CONTENT)))
con.commit()

# 5. THE PURGE: delete near-misses, ordinaries, and the target (all in the tail)
for r in nearmiss+ordinary:
    con.execute("DELETE FROM subjects WHERE id=?",(r[0],)); con.commit()
con.execute("DELETE FROM subjects WHERE id=?",(target_id,)); con.commit()   # the RELEVANT purge

# 6. snapshot the trio WHILE the connection is still open (WAL never flushed)
for ext in ["","-wal","-shm"]:
    shutil.copy(DB+ext, os.path.join(OUT,"surveillance.db"+ext))
con.close()  # close AFTER snapshot

# 7. evidence README (scaffolding)
open(os.path.join(OUT,"EVIDENCE_README.txt"),"w").write(
"""EVIDENCE INTAKE - NODE 'watchnode' - chain of custody
------------------------------------------------------
Recovered: a surveillance database, SQLite, WAL journaling mode.
You have the full trio:
  surveillance.db      - the main database (checkpointed history)
  surveillance.db-wal  - the write-ahead log (recent, UNFLUSHED transactions)
  surveillance.db-shm  - shared-memory index only. Holds NO records. Ignore for recovery.

HANDLING (read this before you touch anything):
  * Image before you analyze. Work on COPIES of all three files.
  * Do NOT open the original in a normal SQLite client / DB Browser. WAL-mode clients
    CHECKPOINT on open, which flushes and truncates the -wal - destroying any deleted
    records that were still sitting in it. That is the one mistake that loses the case.
  * Deleted rows are not gone: their pre-deletion page images may persist in the -wal
    until a checkpoint. Carving the -wal recovers them.

The node was seized mid-write; the WAL was never checkpointed. Everything the operator
did in their last moments is still in that log. Read the analyst_log for the lead.
""")

# 8. package
tar=os.path.join(OUT,"checkpoint_evidence.tar.gz")
if os.path.exists(tar): os.remove(tar)
with tarfile.open(tar,"w:gz") as t:
    for fn in ["surveillance.db","surveillance.db-wal","surveillance.db-shm","EVIDENCE_README.txt"]:
        t.add(os.path.join(OUT,fn),arcname="checkpoint_evidence/"+fn)

# sizes
for fn in ["surveillance.db","surveillance.db-wal","surveillance.db-shm"]:
    print(f"  {fn}: {os.path.getsize(os.path.join(OUT,fn))} bytes")
print("packaged:", tar, os.path.getsize(tar),"bytes")
print("FLAG: number{%s}"%FLAG_CONTENT)
