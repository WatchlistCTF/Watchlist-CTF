#!/usr/bin/env python3
# WATCHLIST CTF - P450 "Endgame" generator. Correlates against the SHIPPED P250 DB.
import os, random, hmac, hashlib, datetime as dt, sqlite3, subprocess, zipfile, shutil
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
random.seed(450)

OUT=os.environ.get("OUT","./p450"); os.makedirs(OUT,exist_ok=True)
P250=os.environ.get("P250","./p250")
P100=os.environ.get("P100","./p100")

# ---- LOCKED (bible) ----
DEVICE_KEY=bytes.fromhex("7b1e0c9a4f2d6835a90e17c4bb52f6d38e4a1c07d9236f5b8a0e2c4471f9a6d3")
PIERCE_CARD="AR-304-77-1592"; MAYA_DESIG="558247193"; PIERCE_DESIG="304771592"
ANON="svc_export_04"; RESTRICTED="SL2-MAIN"
def sig(msg): return hmac.new(DEVICE_KEY,msg.encode(),hashlib.sha256).hexdigest()[:16]

# ---- pull Pierce's REAL badge sessions from the shipped P250 DB (co-timing target) ----
c=sqlite3.connect(f"{P250}/access_control.sqlite").cursor()
pierce_sessions=c.execute("SELECT ts,session_token FROM badge_events WHERE holder='Daniel Pierce' AND session_token IS NOT NULL ORDER BY ts").fetchall()
sl2=c.execute("SELECT ts,session_token FROM badge_events WHERE holder='Daniel Pierce' AND door='SL2-MAIN' AND direction='IN' AND date(ts)='2026-03-13'").fetchone()
c.connection.close()
SMOKING_TS, SMOKING_TOK = sl2  # 2026-03-13T19:40:33 - export co-fires here

# =========================================================================
# ARTIFACT 1: audit_export.log  (large, noisy; anon exports carry req_sig)
# =========================================================================
accounts=[f"u_{n}" for n in ("khan","reyes","shaw","ito","vance","ali","novak","berg","mehta","park","cruz","hale")]
services=["svc_report_01","svc_sync_02","svc_backup_03","svc_export_04","svc_index_05"]
actions=["QUERY","READ","LIST","AGGREGATE","VIEW","RENDER","CACHE_HIT","AUTH_OK"]
datasets=["customers","billing","telemetry","northern_lights","hr","audit","sessions","exports"]
lines=[]
def L(ts,acct,action,ds,extra=""):
    lines.append(f"{ts} lvl=INFO acct={acct} action={action} dataset={ds} rows={random.randint(1,900)}{extra}")

# ~3 weeks of dense audit noise
start=dt.datetime(2026,2,22,0,0,0)
for _ in range(140000):
    ts=(start+dt.timedelta(seconds=random.randint(0,21*24*3600))).strftime("%Y-%m-%dT%H:%M:%S")
    L(ts,random.choice(accounts+services[:3]+services[4:]),random.choice(actions),random.choice(datasets))

# the ILLICIT bulk exports by svc_export_04 - each carries req_sig=HMAC(device_key, anon||ts)
# co-timed with Pierce's badge sessions (so the correlation exists)
# exports fire only during Pierce's after-hours sessions (a focused illicit burst)
export_ts=[t for (t,_) in pierce_sessions if t[11:13] >= '18' or t[11:13] < '07']
# ensure the smoking-gun (SL2 entry) is in the set
for ts in export_ts:
    rs=sig(ANON+ts)
    lines.append(f"{ts} lvl=WARN acct={ANON} action=BULK_EXPORT dataset=northern_lights rows={random.randint(40000,90000)} dst=ext-relay req_sig={rs}")
# a few extra anon exports NOT co-timed (so it's a burst, still all under same key)
for _ in range(6):
    ts=(dt.datetime(2026,3,1)+dt.timedelta(seconds=random.randint(0,10*24*3600))).strftime("%Y-%m-%dT%H:%M:%S")
    lines.append(f"{ts} lvl=WARN acct={ANON} action=BULK_EXPORT dataset=northern_lights rows={random.randint(40000,90000)} dst=ext-relay req_sig={sig(ANON+ts)}")

random.shuffle(lines)
lines.sort(key=lambda x:x[:19])  # chronological like a real export
open(f"{OUT}/audit_export.log","w").write("\n".join(lines)+"\n")
print(f"audit_export.log: {len(lines)} lines ; anon exports: {len([1 for l in lines if ANON in l and 'BULK_EXPORT' in l])}")

# =========================================================================
# ARTIFACT 2: pierce_plan.enc  (AES-256-GCM; key derived from arc artifacts)
# =========================================================================
exhibit_sha=hashlib.sha256(open(f"{P250}/exhibit_A.jpg","rb").read()).hexdigest()
key=hashlib.sha256((MAYA_DESIG+RESTRICTED+exhibit_sha).encode()).digest()
plan=(f"""OPERATION NOTE - PRIVATE. DO NOT RETAIN.
Target: M. Cole (analyst). She has the export records. She has gone to the hotline.
When:  Friday 2026-03-20, 21:00.  Where: Sub-Level 2 Restricted ({RESTRICTED}).
She thinks the 21:00 meeting is about her complaint. It is not.
After this the Northern Lights arrangement continues. No more loose ends.
- D.P.  [designation on file: {PIERCE_DESIG}]
""").encode()
nonce=hashlib.sha256(b"pierce_plan_nonce_v1").digest()[:12]  # deterministic for reproducibility
ct=AESGCM(key).encrypt(nonce,plan,None)
open(f"{OUT}/pierce_plan.enc","wb").write(nonce+ct)   # ship nonce||ciphertext
print(f"pierce_plan.enc: {len(nonce+ct)} bytes (AES-256-GCM)")

# =========================================================================
# ARTIFACT 3: evidence_cache/  (re-context + the key_hint that makes it discoverable)
# =========================================================================
ec=f"{OUT}/evidence_cache"; os.makedirs(ec,exist_ok=True)
open(f"{ec}/README.txt","w").write(
f"""EVIDENCE CACHE - compiled by M. Cole (the material P100 mislabeled "target research").

Read these together with the badge database and the audit log.

WHAT I FOUND
- Someone using the service account '{ANON}' has been bulk-exporting the
  Northern Lights subject dataset to an external relay. Those export lines in
  the audit log each carry a request signature (req_sig=...).
- That signature is not random. The building's access system signs every one
  of a person's badge events with the SAME per-device key (the session_token
  column). The export signatures were produced with that same key.
- So: whoever holds that device key made both the badge events AND the exports.

HOW TO PROVE WHO
- Each token is:  HMAC_SHA256( device_key , IDENTIFIER || timestamp )[:16 hex]
      badge event : IDENTIFIER = the cardholder's card_id
      export line : IDENTIFIER = the account name ('{ANON}')
- One export fires at the EXACT timestamp of a restricted-level badge entry.
  Recompute both HMACs with the key below; if both match the values on record,
  the exporter shares the badge-holder's device key. Find whose card_id that is.
- The card_id encodes their 9-digit designation (AR-XXX-XX-XXXX).

RECOVERED DEVICE KEY (hex) - I lifted it from the access controller:
  {DEVICE_KEY.hex()}

worked check (the smoking gun):
  timestamp        = {SMOKING_TS}
  badge card_id    = {PIERCE_CARD}
  export account   = {ANON}
  -> HMAC(key, card_id||ts)[:16] should equal that badge row's session_token
  -> HMAC(key, '{ANON}'||ts)[:16] should equal that export line's req_sig
  if both hold, the exporter IS the badge holder.

Then decrypt his plan (pierce_plan.enc):
  key = SHA256( <Maya's designation from P100> || "{RESTRICTED}" || sha256(exhibit_A.jpg) )
  format = nonce(12 bytes) || AES-256-GCM ciphertext
""")
# a couple of clearly-fictional re-context notes
open(f"{ec}/note_meeting.txt","w").write(
"Photo log (my notes): the man in the CCTV stills meeting the outside buyer is D. Pierce,\nnot me. I was the one photographing HIM. The 'stalking' was me gathering proof.\n")
print("evidence_cache/ written (README carries the discoverable key_hint)")

# =========================================================================
# RE-SHIP P100 pdf + P250 db (self-contained dossier)
# =========================================================================
shutil.copy(f"{P100}/cole_notes.pdf",f"{OUT}/cole_notes.pdf")
shutil.copy(f"{P250}/access_control.sqlite",f"{OUT}/access_control.sqlite")
shutil.copy(f"{P250}/exhibit_A.jpg",f"{OUT}/exhibit_A.jpg")

# =========================================================================
# PACKAGE
# =========================================================================
zp=f"{OUT}/endgame_dossier.zip"
if os.path.exists(zp): os.remove(zp)
with zipfile.ZipFile(zp,"w",zipfile.ZIP_DEFLATED) as z:
    for a in ["audit_export.log","pierce_plan.enc","cole_notes.pdf","access_control.sqlite","exhibit_A.jpg"]:
        z.write(f"{OUT}/{a}",a)
    for root,_,files in os.walk(ec):
        for fn in files: z.write(os.path.join(root,fn),os.path.relpath(os.path.join(root,fn),OUT))
print("endgame_dossier.zip packaged")
print("FLAG: number{%s}  | TRAP (fails): number{%s}"%(PIERCE_DESIG,MAYA_DESIG))
