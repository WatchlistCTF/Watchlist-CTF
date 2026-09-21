#!/usr/bin/env python3
# ============================================================================
#  WATCHLIST CTF - L250 "Checkpoint" - SOLVER / ANSWER KEY
#
#  Carves the WAL at the FORMAT level (own parser - proves the challenge is
#  solvable without any specific tool), applies the analyst-log lead + triage,
#  decodes, and asserts every anti-shortcut property. Exit 0 = solves + safe.
#
#  Usage:
#    tar xzf ../files/3d44a3e47901c9c1.tar.gz
#    python3 solve_l250.py checkpoint_evidence
#
#  Needs only the Python 3 standard library. No network access.
#  It copies the three files to a temporary folder first and never opens the
#  originals, because opening this database the normal way destroys the
#  evidence (see the walkthrough).
# ============================================================================
import os, sys, base64, struct, sqlite3, shutil, tempfile, re

DIR = sys.argv[1] if len(sys.argv)>1 else "checkpoint_evidence"
P=lambda f:os.path.join(DIR,f)
ok=[];fail=[]
def check(n,c,d=""):
    (ok if c else fail).append(n); print(f"  [{'✓' if c else '✗'}] {n}"+(f"  : {d}" if d else ""))

print("="*68); print("L250 CHECKPOINT - SOLVER / ANSWER KEY"); print("="*68)

# ---------------------------------------------------------------- STEP 0: discipline
print("\nSTEP 0 - image before analysis (work on a copy; never checkpoint the original)")
tmp=tempfile.mkdtemp()
for ext in ["","-wal","-shm"]:
    shutil.copy(P("surveillance.db"+ext), os.path.join(tmp,"surveillance.db"+ext))
check("copied the full trio read-only to a scratch dir", os.path.exists(os.path.join(tmp,"surveillance.db-wal")))

# ---------------------------------------------------------------- STEP 1: main db is clean
print("\nSTEP 1 - the main db alone is sanitized (ignore-the-WAL shortcut fails)")
c=sqlite3.connect(os.path.join(tmp,"surveillance.db")).cursor()
n=c.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
rel=c.execute("SELECT COUNT(*) FROM subjects WHERE status='RELEVANT'").fetchone()[0]
check("main db is populated but has ZERO relevant rows", n>1000 and rel==0, f"{n} subjects, {rel} RELEVANT")

# ---------------------------------------------------------------- STEP 2: read the lead
print("\nSTEP 2 - read the analyst_log lead (committed; visible read-only)")
lead=" ".join(e for (t,e) in c.execute("SELECT ts,entry FROM analyst_log").fetchall())
m=re.search(r"ends? (\d{4})", lead)
lead_suffix=m.group(1) if m else None
check("lead names the target by a matchable property (designation ends NNNN)", lead_suffix=="0001", f"...{lead_suffix}")
check("lead warns others are cover (triage is required)", "cover" in lead.lower())

# ---------------------------------------------------------------- STEP 3: FORMAT-LEVEL WAL carve
print("\nSTEP 3 - carve the -wal at the format level (tool-independent parser)")
def carve_wal(dbpath, walpath):
    """Minimal SQLite WAL frame carver: pull leaf-table cells from every frame page.
       Returns list of recovered rows as tuples of column values."""
    db=open(dbpath,"rb").read(); page_size=struct.unpack(">H",db[16:18])[0] or 4096
    if page_size==1: page_size=65536
    w=open(walpath,"rb").read()
    if w[:4] not in (b"\x37\x7f\x06\x82", b"\x37\x7f\x06\x83"): return []
    # WAL header 32 bytes; each frame = 24-byte header + page_size bytes
    rows=[]; off=32; framesz=24+page_size
    while off+framesz<=len(w):
        page=w[off+24:off+24+page_size]; off+=framesz
        if not page: continue
        ptype=page[0]
        if ptype!=0x0D: continue          # 0x0D = leaf table b-tree
        ncell=struct.unpack(">H",page[3:5])[0]
        cellptrs=[struct.unpack(">H",page[8+2*i:10+2*i])[0] for i in range(ncell)]
        for cp in cellptrs:
            if cp<=0 or cp>=page_size: continue
            try:
                p=cp
                plen,p=read_varint(page,p)      # payload length
                rowid,p=read_varint(page,p)      # rowid
                rec=parse_record(page[p:p+plen])
                if rec: rows.append(rec)
            except Exception: continue
    return rows

def read_varint(buf,p):
    val=0
    for i in range(9):
        b=buf[p]; p+=1
        if i==8: val=(val<<8)|b; break
        val=(val<<7)|(b&0x7f)
        if not (b&0x80): break
    return val,p

def parse_record(rec):
    try:
        p=0; hdrlen,p=read_varint(rec,p); hdr_end=hdrlen; serials=[]
        while p<hdr_end:
            s,p=read_varint(rec,p); serials.append(s)
        vals=[]; body=p
        for s in serials:
            if s==0: vals.append(None)
            elif s==1: vals.append(int.from_bytes(rec[body:body+1],"big",signed=True)); body+=1
            elif s==2: vals.append(int.from_bytes(rec[body:body+2],"big",signed=True)); body+=2
            elif s==3: vals.append(int.from_bytes(rec[body:body+3],"big",signed=True)); body+=3
            elif s==4: vals.append(int.from_bytes(rec[body:body+4],"big",signed=True)); body+=4
            elif s==5: vals.append(int.from_bytes(rec[body:body+6],"big",signed=True)); body+=6
            elif s==6: vals.append(int.from_bytes(rec[body:body+8],"big",signed=True)); body+=8
            elif s==8: vals.append(0)
            elif s==9: vals.append(1)
            elif s>=13 and s%2==1:
                ln=(s-13)//2; vals.append(rec[body:body+ln].decode("utf-8","replace")); body+=ln
            elif s>=12 and s%2==0:
                ln=(s-12)//2; vals.append(rec[body:body+ln]); body+=ln
            else: vals.append(None)
        return vals
    except Exception: return None

carved=carve_wal(os.path.join(tmp,"surveillance.db"), os.path.join(tmp,"surveillance.db-wal"))
# recovered subject rows look like [alias, ssn, status, priority, last_seen, intel] (id is rowid)
subj=[r for r in carved if len(r)>=7 and isinstance(r[3],str) and r[3] in ("RELEVANT","IRRELEVANT")]
# de-duplicate carved rows (same row appears in multiple frame page images)
seen=set(); uniq=[]
for r in subj:
    k=(r[1],r[2],r[3])
    if k not in seen:
        seen.add(k); uniq.append(r)
subj=uniq
# the carve recovers the DELETED tail rows (near-misses + target) plus bulk copies;
# the deleted target is the RELEVANT one that is ABSENT from the live main db.
check("format-level carver recovered subject rows from the WAL", len(subj)>=5, f"{len(subj)} unique rows carved")
relevant=[r for r in subj if r[3]=="RELEVANT"]
check("recovered the deleted RELEVANT row from the WAL", len(relevant)>=1, f"{len(relevant)} RELEVANT")

# ---------------------------------------------------------------- STEP 4: triage w/ the lead
print("\nSTEP 4 - triage against the lead (near-misses present; WHERE alone insufficient)")
# near-miss check: are there IRRELEVANT rows that look important (CRITICAL/HIGH)?
nearmiss=[r for r in subj if r[3]=="IRRELEVANT" and r[4] in ("CRITICAL","HIGH")]
check("near-miss decoys exist (a bare status filter isn't enough)", len(nearmiss)>=2, f"{len(nearmiss)} near-misses")
# apply lead: ssn ends 0001 AND status RELEVANT
target=[r for r in subj if r[3]=="RELEVANT" and str(r[2]).replace('-','').endswith("0001")]
check("lead+status pinpoints exactly one target", len(target)==1, f"{len(target)} match")

# ---------------------------------------------------------------- STEP 5: decode + self-check
print("\nSTEP 5 - decode the target's intel (self-check: target=English, decoys=junk)")
tgt=target[0]; intel=tgt[6]
def is_text(b64s):
    try: d=base64.b64decode(b64s); d.decode("ascii"); return all(32<=x<127 or x in (9,10) for x in d)
    except Exception: return False
check("target intel decodes to readable English", is_text(intel), base64.b64decode(intel).decode("ascii","replace"))
# confirm a near-miss decodes to junk
if nearmiss: check("a near-miss intel decodes to non-text junk (confirming signal)", not is_text(nearmiss[0][6]))
flag="number{"+base64.b64decode(intel).decode()+"}"

# ---------------------------------------------------------------- ANTI-SHORTCUT
print("\nANTI-SHORTCUT - the wrapped flag is nowhere in the bytes")
walbytes=open(P("surveillance.db-wal"),"rb").read()
check("'number{' absent from WAL bytes", b"number{" not in walbytes)
check("decoded phrase absent from WAL bytes (only base64 stored)", b"the_log_remembers" not in walbytes)

print("\n"+"="*68); print(f"FLAG = {flag}"); print("="*68)
print(f"\n{len(ok)} checks passed, {len(fail)} failed")
sys.exit(1 if fail else 0)
