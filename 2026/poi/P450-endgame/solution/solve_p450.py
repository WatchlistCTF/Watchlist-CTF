#!/usr/bin/env python3
# WATCHLIST CTF P450 "Endgame" reference solver / answer key.
#
# Usage:  unzip ../files/3b6a10347800c543.zip -d dossier
#         python3 solve_p450.py dossier
# Needs:  the cryptography package, and pdftotext (poppler) on PATH.
#         No network access.
import os, sys, re, sqlite3, hmac, hashlib, subprocess
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
DIR = sys.argv[1] if len(sys.argv)>1 else "."
P=lambda f:os.path.join(DIR,f)
FLAG_DESIG="304771592"; TRAP="558247193"; ANON="svc_export_04"; RESTRICTED="SL2-MAIN"
ok=[];fail=[]
def check(n,c,d=""):
    (ok if c else fail).append(n); print(f"  [{'✓' if c else '✗'}] {n}"+(f"  : {d}" if d else ""))
print("="*68); print("P450 ENDGAME - SOLVER / ANSWER KEY"); print("="*68)
print("\nSTEP 1 - isolate the illicit exports in the audit log")
log=open(P("audit_export.log")).read().splitlines()
exports=[l for l in log if f"acct={ANON}" in l and "BULK_EXPORT" in l]
check("audit log is tool-scale (>100k lines)", len(log)>100000, f"{len(log)} lines")
check(f"isolated {ANON} bulk-export lines with req_sig", len(exports)>0 and all("req_sig=" in e for e in exports), f"{len(exports)} exports")
print("\nSTEP 2 - recover the device key (from evidence_cache/README)")
readme=open(P("evidence_cache/README.txt")).read()
m=re.search(r"RECOVERED DEVICE KEY \(hex\).*?\n\s*([0-9a-f]{64})",readme,re.S)
device_key=bytes.fromhex(m.group(1))
check("device_key recovered from README key_hint", len(device_key)==32, m.group(1)[:16]+"…")
sig=lambda msg: hmac.new(device_key,msg.encode(),hashlib.sha256).hexdigest()[:16]
print("\nSTEP 3 - hash-correlate exports to badge sessions (prove exporter = Pierce)")
c=sqlite3.connect(P("access_control.sqlite")).cursor()
matched_card=None; smoking=None
for e in exports:
    ts=e[:19]; mrs=re.search(r"req_sig=([0-9a-f]{16})",e)
    if not mrs: continue
    if sig(ANON+ts)!=mrs.group(1): continue
    row=c.execute("SELECT card_id,session_token FROM badge_events WHERE ts=? AND session_token IS NOT NULL",(ts,)).fetchone()
    if row and sig(row[0]+ts)==row[1]:
        matched_card=row[0]; smoking=ts; break
check("found co-timed export+badge both signed by same device_key", matched_card is not None, f"card={matched_card} @ {smoking}")
desig=(matched_card or "").replace("AR-","").replace("-","")
check("matched card_id encodes Pierce's designation", desig==FLAG_DESIG, f"{matched_card} -> {desig}")
print("\nSTEP 4 - decrypt the plan (key derived from P100 + P250 artifacts)")
exhibit_sha=hashlib.sha256(open(P("exhibit_A.jpg"),"rb").read()).hexdigest()
maya=subprocess.run(["pdftotext",P("cole_notes.pdf"),"-"],capture_output=True,text=True).stdout
maya_desig=re.search(r"(\d{9})",maya).group(1)
key=hashlib.sha256((maya_desig+RESTRICTED+exhibit_sha).encode()).digest()
blob=open(P("pierce_plan.enc"),"rb").read(); nonce,ct=blob[:12],blob[12:]
try: pt=AESGCM(key).decrypt(nonce,ct,None).decode(); dec_ok=True
except Exception: pt=""; dec_ok=False
check("plan decrypts with SHA256(maya||door||exhibit_sha)", dec_ok)
check("decrypted plan confirms imminent crime (03-20 21:00 SL2)", "2026-03-20" in pt and RESTRICTED in pt)
check("decrypted plan corroborates Pierce's designation", FLAG_DESIG in pt)
print("\nANTI-SHORTCUT - flag is EARNED, not lying in plaintext")
leak=[]
for f in ["audit_export.log","evidence_cache/README.txt","evidence_cache/note_meeting.txt"]:
    if FLAG_DESIG in open(P(f),errors="ignore").read(): leak.append(f)
if FLAG_DESIG in maya: leak.append("cole_notes.pdf")
check("Pierce's designation in NO shipped plaintext (only via correlation/decrypt)", not leak, f"leaks: {leak or 'none'}")
check("trap present (Maya's designation is the wrong answer)", TRAP in maya)
print("\n"+"="*68)
print(f"FLAG = number{{{FLAG_DESIG}}}   (Pierce, the true perpetrator)")
print(f"TRAP = number{{{TRAP}}} fails (Maya - the un-flipped read)")
print("="*68)
print(f"\n{len(ok)} checks passed, {len(fail)} failed")
sys.exit(1 if fail else 0)
