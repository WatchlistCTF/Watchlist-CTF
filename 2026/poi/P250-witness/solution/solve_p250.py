#!/usr/bin/env python3
# ============================================================================
#  WATCHLIST CTF - P250 "Witness" - SOLVER / ANSWER KEY
#
#  Walks the intended DFIR solve path against the shipped case file and asserts
#  each stage. Doubles as the answer key and a playtest harness.
#
#  Usage:   unzip ../files/26bf84684d31d6f7.zip -d casefile
#           python3 solve_p250.py casefile
#  Needs:   exiftool on PATH (for STEP 4); the rest is standard library.
#
#  Exit 0 = challenge solves end-to-end and all anti-shortcut properties hold.
# ============================================================================
import sqlite3, mailbox, subprocess, sys, os, re

DIR = sys.argv[1] if len(sys.argv) > 1 else "."
FLAG = "number{AR-ETH-884213}"
NIGHT = "2026-03-13"

P = lambda f: os.path.join(DIR, f)
ok=[]; fail=[]
def check(name, cond, detail=""):
    (ok if cond else fail).append(name)
    print(f"  [{'✓' if cond else '✗'}] {name}" + (f"  : {detail}" if detail else ""))

print("="*68)
print("P250 WITNESS - SOLVER / ANSWER KEY")
print("="*68)

# ---------------------------------------------------------------- STEP 1
print("\nSTEP 1 - the witness statement (the trap: it accuses Maya)")
stmt = open(P("pierce_statement.txt")).read()
claim = ("21:00" in stmt and "21:15" in stmt)
check("Pierce makes a falsifiable 21:00 / 21:15 claim", claim)
print("      claim: Maya 'outside the facility' ~21:00; 'threat' 21:15 (Exhibit A)")

# ---------------------------------------------------------------- STEP 2
print("\nSTEP 2 - QUERY the access-control DB (not read it)")
con = sqlite3.connect(P("access_control.sqlite")); c = con.cursor()
total = c.execute("SELECT COUNT(*) FROM badge_events").fetchone()[0]
check("DB volume is tool-scale (>20k events, not pasteable)", total > 20000, f"{total} events")

maya = c.execute(
    "SELECT ts,door,direction FROM badge_events WHERE holder='Maya Cole' "
    "AND date(ts)=? ORDER BY ts", (NIGHT,)).fetchall()
last = maya[-1]
maya_gone = (last[2] == "OUT" and last[0].endswith("18:30:02")
             and not any(r[0] > last[0] for r in maya))
check("Maya badged OUT 18:30 with NO later event -> 21:00 claim impossible",
      maya_gone, f"last = {last}")

pierce_restricted = c.execute(
    "SELECT ts FROM badge_events WHERE holder='Daniel Pierce' AND door='SL2-MAIN' "
    "AND direction='IN' AND date(ts)=? ORDER BY ts", (NIGHT,)).fetchone()
check("Pierce entered RESTRICTED SL2-MAIN on the night (P450 seed)",
      pierce_restricted is not None, f"@ {pierce_restricted[0] if pierce_restricted else '-'}")

late = c.execute("SELECT COUNT(DISTINCT holder) FROM badge_events WHERE time(ts)>='20:00'").fetchone()[0]
check("Decoy noise present (many late workers -> Maya-absent isn't obvious)", late > 20, f"{late} distinct late people")

# cross-act: Pierce rows carry HMAC session_token; nobody else does (P450 correlation)
tok_holders = [r[0] for r in c.execute(
    "SELECT DISTINCT holder FROM badge_events WHERE session_token IS NOT NULL").fetchall()]
check("Only Pierce's rows carry session_token (feeds P450 hash-correlation)",
      tok_holders == ["Daniel Pierce"], f"holders w/ tokens: {tok_holders}")
con.close()

# ---------------------------------------------------------------- STEP 3
print("\nSTEP 3 - recover the case number from the mbox (structured field, not prose)")
mb = mailbox.mbox(P("maya_mail.mbox"))
header_val = None; body_leak = 0
for m in mb:
    if m.get("X-Case-Ref"): header_val = m.get("X-Case-Ref")
    if "884213" in (m.get_payload() or ""): body_leak += 1
case_ref = (header_val or "").strip()
recovered_flag = f"number{{{case_ref}}}" if case_ref else None
check("case reference found in X-Case-Ref header", case_ref == "AR-ETH-884213", f"X-Case-Ref: {header_val}")
check("recovered flag matches the expected value", recovered_flag == FLAG, recovered_flag)
check("case number does NOT leak into any readable message body (anti-skim)", body_leak == 0,
      f"{body_leak} body occurrences")

# ---------------------------------------------------------------- STEP 4
print("\nSTEP 4 - corroborate: the 'proof' exhibit was fabricated")
def exif(tag, f):
    r = subprocess.run(["exiftool","-s3","-"+tag, P(f)], capture_output=True, text=True)
    return r.stdout.strip()
sw = exif("Software","exhibit_A.jpg"); cd = exif("CreateDate","exhibit_A.jpg")
check("exhibit_A.jpg edited in an image editor (Software tag)", "Photoshop" in sw or "GIMP" in sw, sw)
check("exhibit created 03-14, AFTER the 03-13 report -> doctored",
      cd.startswith("2026:03:14"), cd)

# ---------------------------------------------------------------- RESULT
print("\n" + "="*68)
print(f"FLAG = {FLAG}")
print("Reading: Pierce's testimony is impossible; Maya was filing case 884213")
print("against him. The witness lied; the accused is the whistleblower.")
print("="*68)
print(f"\n{len(ok)} checks passed, {len(fail)} failed")
if fail:
    print("FAILED:", ", ".join(fail)); sys.exit(1)
print("✓ P250 solves end-to-end and all anti-shortcut properties hold.")
