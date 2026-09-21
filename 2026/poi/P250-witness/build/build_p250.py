#!/usr/bin/env python3
# WATCHLIST CTF - P250 "Witness" generator. All facts from poi-arc-case-bible.md.
import sqlite3, os, random, hmac, hashlib, datetime as dt, mailbox, email.utils, subprocess
random.seed(313)

OUT=os.environ.get("OUT","./p250"); os.makedirs(OUT,exist_ok=True)

# ---- LOCKED constants (bible) ----
DEVICE_KEY=bytes.fromhex("7b1e0c9a4f2d6835a90e17c4bb52f6d38e4a1c07d9236f5b8a0e2c4471f9a6d3")
MAYA_CARD="AR-558-24-7193"; PIERCE_CARD="AR-304-77-1592"
CASE="884213"; RESTRICTED="SL2-MAIN"
NIGHT=dt.date(2026,3,13)
def tok(card, ts_iso): return hmac.new(DEVICE_KEY,(card+ts_iso).encode(),hashlib.sha256).hexdigest()[:16]

# ---- roster ----
first=["Maya","Daniel","Aisha","Tom","Priya","Ken","Lena","Omar","Sara","Nils","Ivy","Raj","Cara","Paul","Nadia","Sam","Ella","Yusuf","Bea","Leo","Mira","Dev","Ana","Ravi","Tess","Jon","Kim","Ada","Ben","Zoe"]
last=["Cole","Pierce","Khan","Reyes","Shaw","Ito","Vance","Ali","Novak","Berg","Frost","Mehta","Diaz","Lund","Park","Bauer","Ross","Cruz","Hale","Wong"]
holders=[("Maya Cole",MAYA_CARD),("Daniel Pierce",PIERCE_CARD)]
used={"Maya Cole","Daniel Pierce"}
cid=1000
while len(holders)<64:
    n=f"{random.choice(first)} {random.choice(last)}"
    if n in used: continue
    used.add(n); cid+=1; holders.append((n,f"AR-{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}"))
name2card=dict(holders)

doors=[("LOBBY-N","Lobby North","public"),("LOBBY-S","Lobby South","public"),
       ("L1-OFFICE","Level 1 Office","general"),("L2-OFFICE","Level 2 Office","general"),
       ("L3-LAB","Level 3 Lab","general"),("CAFE","Cafeteria","public"),
       ("SERVER-A","Server Room A","restricted"),(RESTRICTED,"Sub-Level 2 Restricted","restricted")]

dbp=f"{OUT}/access_control.sqlite"
if os.path.exists(dbp): os.remove(dbp)
con=sqlite3.connect(dbp); c=con.cursor()
c.execute("CREATE TABLE cardholders(card_id TEXT PRIMARY KEY, holder TEXT, dept TEXT)")
c.execute("CREATE TABLE doors(door TEXT PRIMARY KEY, name TEXT, zone TEXT)")
c.execute("""CREATE TABLE badge_events(id INTEGER PRIMARY KEY, card_id TEXT, holder TEXT,
             door TEXT, direction TEXT, ts TEXT, session_token TEXT)""")
depts=["Analytics","Engineering","Ops","Admin","Security","Research"]
for n,card in holders: c.execute("INSERT INTO cardholders VALUES(?,?,?)",(card,n,random.choice(depts)))
for d,nm,z in doors: c.execute("INSERT INTO doors VALUES(?,?,?)",(d,nm,z))

rows=[]
def ev(card,holder,door,direction,when):
    ts=when.strftime("%Y-%m-%dT%H:%M:%S")
    st=tok(card,ts) if card==PIERCE_CARD else None   # ONLY Pierce carries session_token (P450 correlation)
    rows.append((card,holder,door,direction,ts,st))

# 3 weeks of realistic churn (weekdays busy, some late workers)
start=NIGHT-dt.timedelta(days=40)
for day in range(46):
    d0=start+dt.timedelta(days=day)
    if d0.weekday()>=5 and random.random()<0.7: continue
    for n,card in holders:
        # the night (03-13) for Maya+Pierce is authored canonically below - no random noise for them that day
        if d0==NIGHT and n in ("Maya Cole","Daniel Pierce"): continue
        if random.random()<0.06: continue
        inh=random.randint(7,10); inm=random.randint(0,59)
        t_in=dt.datetime(d0.year,d0.month,d0.day,inh,inm,random.randint(0,59))
        door=random.choice([d for d in doors if d[2] in ("public","general")])[0]
        ev(card,n,door,"IN",t_in)
        # a couple of interior movements
        for _ in range(random.randint(6,14)):
            tm=t_in+dt.timedelta(minutes=random.randint(20,300))
            ev(card,n,random.choice(doors)[0],random.choice(["IN","OUT"]),tm)
        outh=random.randint(16,19)
        t_out=dt.datetime(d0.year,d0.month,d0.day,outh,random.randint(0,59),random.randint(0,59))
        ev(card,n,random.choice([d for d in doors if d[2]!="restricted"])[0],"OUT",t_out)
    # a few habitual late workers (decoys) so "late activity" isn't unique to the night
    for n,card in random.sample(holders,3):
        if n in ("Maya Cole","Daniel Pierce"): continue
        lt=dt.datetime(d0.year,d0.month,d0.day,random.randint(20,22),random.randint(0,59))
        ev(card,n,"L2-OFFICE","IN",lt); ev(card,n,"LOBBY-N","OUT",lt+dt.timedelta(minutes=random.randint(20,90)))

# ---- THE NIGHT (canonical facts from bible) ----
# Maya: normal day, badges OUT 18:30 at LOBBY-N, NO return
ev(MAYA_CARD,"Maya Cole","LOBBY-N","IN",dt.datetime(2026,3,13,8,52,11))
ev(MAYA_CARD,"Maya Cole","L2-OFFICE","IN",dt.datetime(2026,3,13,9,3,40))
ev(MAYA_CARD,"Maya Cole","CAFE","IN",dt.datetime(2026,3,13,12,40,5))
ev(MAYA_CARD,"Maya Cole","LOBBY-N","OUT",dt.datetime(2026,3,13,18,30,2))   # <-- refuting fact
# Pierce: in the building late; enters RESTRICTED SL2-MAIN 19:40 (P450 seed)
ev(PIERCE_CARD,"Daniel Pierce","LOBBY-S","IN",dt.datetime(2026,3,13,17,15,9))
ev(PIERCE_CARD,"Daniel Pierce","L2-OFFICE","IN",dt.datetime(2026,3,13,17,20,0))
ev(PIERCE_CARD,"Daniel Pierce",RESTRICTED,"IN",dt.datetime(2026,3,13,19,40,33))  # <-- P450 seed (session_token)
ev(PIERCE_CARD,"Daniel Pierce",RESTRICTED,"OUT",dt.datetime(2026,3,13,21,18,7))
ev(PIERCE_CARD,"Daniel Pierce","LOBBY-S","OUT",dt.datetime(2026,3,13,21,25,50))
# a decoy late worker on the night too (so Maya-absent isn't the ONLY thing to notice)
ev(name2card["Sara Ali"] if "Sara Ali" in name2card else holders[5][1], "Sara Ali" if "Sara Ali" in name2card else holders[5][0],
   "L2-OFFICE","IN",dt.datetime(2026,3,13,20,10,0))

random.shuffle(rows)  # so the refuting rows aren't first
rows.sort(key=lambda r:r[4])  # store in ts order (realistic export)
for r in rows: c.execute("INSERT INTO badge_events(card_id,holder,door,direction,ts,session_token) VALUES(?,?,?,?,?,?)",r)
c.execute("CREATE INDEX idx_ts ON badge_events(ts)")
c.execute("CREATE INDEX idx_holder ON badge_events(holder)")
con.commit()
n=c.execute("SELECT COUNT(*) FROM badge_events").fetchone()[0]
con.close()
print(f"access_control.sqlite: {n} events, {len(holders)} cardholders")

# =========================================================================
# ARTIFACT 2: maya_mail.mbox  - case #884213 lives in an X-header, not prose
# =========================================================================
import mailbox, email.utils, email.mime.text
mbp=f"{OUT}/maya_mail.mbox"
if os.path.exists(mbp): os.remove(mbp)
mb=mailbox.mbox(mbp)
def mail(frm,to,subj,body,when,extra=None):
    m=mailbox.mboxMessage()
    m["From"]=frm; m["To"]=to; m["Subject"]=subj
    m["Date"]=email.utils.format_datetime(when)
    m["Message-ID"]=email.utils.make_msgid(domain="mail.local")
    if extra:
        for k,v in extra.items(): m[k]=v
    m.set_payload(body); mb.add(m)

import datetime as dt2
# some innocuous personal mail (noise + places her at home that evening)
mail("maya.cole@aletheia-research.example","mom@familymail.example","re: dinner sunday",
     "yeah I'll be there ~1pm. bringing the salad. long week, tell you about it sunday.",
     dt2.datetime(2026,3,13,19,12,0))
mail("noreply@streamflix.example","maya.cole@aletheia-research.example","Your PIN was used to sign in",
     "A new sign-in to your account from a device at your home network. If this wasn't you...",
     dt2.datetime(2026,3,13,20,3,0))
# THE ethics-complaint confirmation - case # in X-Case-Ref header (structured field)
mail("intake@ethics-hotline.example","maya.cole@aletheia-research.example",
     "Complaint received - reference assigned",
     ("Your confidential report has been received and logged. A case officer will be assigned.\n"
      "Please retain your reference for follow-up. Do not reply to this address.\n\n"
      "Filed: 2026-03-13 21:07 local. Status: OPEN.\n"),
     dt2.datetime(2026,3,13,21,8,30),
     extra={"X-Case-Ref":"AR-ETH-884213","X-Intake-Channel":"web-form","X-Submitted-Local":"2026-03-13T21:07:44"})
mb.flush(); mb.close()
print("maya_mail.mbox written (case# in X-Case-Ref header)")

# =========================================================================
# ARTIFACT 3: exhibit_A.jpg - Pierce's fabricated "threat" screenshot
#   EXIF Software = editor; create date AFTER he filed his report
# =========================================================================
from PIL import Image, ImageDraw, ImageFont
img=Image.new("RGB",(720,300),(240,242,245)); d=ImageDraw.Draw(img)
try: fnt=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",18); fb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",18)
except: fnt=fb=ImageFont.load_default()
d.rectangle([0,0,720,44],fill=(30,90,160)); d.text((16,12),"Messages - M. Cole",fill=(255,255,255),font=fb)
# a bubble (staged to look like a threat)
d.rounded_rectangle([40,80,560,140],14,fill=(230,232,236))
d.text((56,96),"you will regret what you are doing. this ends badly for you.",fill=(20,20,20),font=fnt)
d.text((56,160),"- submitted by D. Pierce as Exhibit A",fill=(120,120,120),font=fnt)
img.save(f"{OUT}/exhibit_A.jpg","JPEG",quality=90)
# EXIF: fabricated after the report; editor software
subprocess.run(["exiftool","-overwrite_original",
   "-Software=Adobe Photoshop 25.0 (Windows)",
   "-CreateDate=2026:03:14 01:22:10","-ModifyDate=2026:03:14 01:22:10",
   "-DateTimeOriginal=2026:03:14 01:22:10",
   f"{OUT}/exhibit_A.jpg"],capture_output=True)
print("exhibit_A.jpg written (Software=editor, created 03-14 AFTER the 03-13 report)")

# =========================================================================
# ARTIFACT 4: pierce_statement.txt - the falsifiable claim (only prose file)
# =========================================================================
open(f"{OUT}/pierce_statement.txt","w").write(
"""WITNESS STATEMENT - INTERNAL INCIDENT REVIEW
Ref: IR-2026-0314 / Aletheia Research
Deponent: Daniel R. Pierce (Manager, Northern Lights Data Services)
Re: Conduct of M. Cole (Data Analyst II)

I am submitting this account of the events of Friday, 13 March 2026.

For several weeks, Ms Cole had been behaving erratically toward me. On the
night in question, at approximately 21:00, I observed her outside the
facility. At 21:15 she sent me a threatening message (attached as Exhibit A).

I believe the materials she has been compiling about me are fabricated and
are an attempt to discredit a manager who raised performance concerns. I am
the injured party here. I request that her access be reviewed.

Signed, D. Pierce
2026-03-14
""")
print("pierce_statement.txt written")

# =========================================================================
# PACKAGE
# =========================================================================
import zipfile
zp=f"{OUT}/witness_casefile.zip"
if os.path.exists(zp): os.remove(zp)
with zipfile.ZipFile(zp,"w",zipfile.ZIP_DEFLATED) as z:
    for a in ["pierce_statement.txt","access_control.sqlite","maya_mail.mbox","exhibit_A.jpg"]:
        z.write(f"{OUT}/{a}",a)
print("witness_casefile.zip packaged")
print("FLAG: number{AR-ETH-884213}")
