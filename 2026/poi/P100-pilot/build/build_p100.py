#!/usr/bin/env python3
# WATCHLIST CTF - P100 "Pilot" artifact generator.  Reproducible; all facts from the case bible.
# Deps: reportlab, pillow, piexif, poppler-utils (pdftotext/pdfinfo), libimage-exiftool-perl
import os, subprocess
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black
from PIL import Image, ImageDraw
import piexif

# ---- CONSTANTS (from poi-arc-case-bible.md - do not hand-edit here) ----
MAYA_DESIG = "558247193"
AUTHOR     = "Maya Cole"
STILL_DT   = "2026:03:11 17:12:04"
HQ_LAT, HQ_LON = 12.6208, 80.1945
WINDOW_WHEN, WINDOW_WHERE = "2026-03-20T21:00", 'Sub-Level 2, Restricted (SL2-MAIN)'
OUT = os.environ.get("OUT","./p100")

def pdf(path):
    c=canvas.Canvas(path,pagesize=letter); c.setAuthor(AUTHOR)
    c.setTitle("Personal Notes - D. Pierce"); c.setCreator("LibreOffice 7.4"); c.setProducer("LibreOffice 7.4")
    W,H=letter; y=H-inch
    c.setFont("Helvetica-Bold",15); c.drawString(inch,y,"AELETHEIA RESEARCH - INTERNAL"); y-=0.35*inch
    c.setFont("Helvetica",10)
    for l in ["Compiled notes re: D. Pierce (mgr).  KEEP PRIVATE.",
              "Something is wrong with the export volumes on the NL dataset.",
              "He is at the office at hours that make no sense. I have photos.",
              "I am documenting everything before I take this to compliance."]:
        c.drawString(inch,y,l); y-=0.28*inch
    y-=0.2*inch; c.setFont("Helvetica-Bold",11); lab="EMPLOYEE DESIGNATION: "
    c.drawString(inch,y,lab); lw=c.stringWidth(lab,"Helvetica-Bold",11)
    c.drawString(inch+lw,y,MAYA_DESIG)                    # live selectable text (the secret)
    dw=c.stringWidth(MAYA_DESIG,"Helvetica-Bold",11)
    c.setFillColor(black); c.rect(inch+lw-2,y-3,dw+6,14,fill=1,stroke=0)  # opaque overlay (vector)
    y-=0.5*inch; c.setFont("Helvetica-Oblique",9)
    c.drawString(inch,y,"(designation auto-inserted by HR template; redacted for this copy)")
    c.showPage(); c.save()

def still(path):
    W,H=1000,700; img=Image.new("RGB",(W,H),(18,18,20)); d=ImageDraw.Draw(img)
    d.rectangle([8,8,W-8,H-8],outline=(60,60,64),width=2)
    d.text((20,18),"CAM 04  //  ALETHEIA RESEARCH  //  EXT-NORTH",fill=(140,140,150))
    d.text((20,H-34),"[ FEED STILL - SUBJECT PHOTOGRAPHING MANAGER ]",fill=(150,90,90))
    d.ellipse([420,250,520,350],fill=(40,40,46)); d.rectangle([430,350,510,520],fill=(40,40,46))
    d.ellipse([640,270,720,350],fill=(35,35,40)); d.rectangle([648,350,712,500],fill=(35,35,40))
    img.save(path,"JPEG",quality=88)
    dd=lambda v:((int(v),1),(int((v-int(v))*60),1),(int((((v-int(v))*60)-int((v-int(v))*60))*6000),100))
    z={"0th":{piexif.ImageIFD.Make:b"Axis",piexif.ImageIFD.Model:b"P3245-LVE",piexif.ImageIFD.Software:b"Aletheia-CCTV"},
       "Exif":{piexif.ExifIFD.DateTimeOriginal:STILL_DT.encode()},
       "GPS":{piexif.GPSIFD.GPSLatitudeRef:b'N',piexif.GPSIFD.GPSLatitude:dd(HQ_LAT),
              piexif.GPSIFD.GPSLongitudeRef:b'E',piexif.GPSIFD.GPSLongitude:dd(HQ_LON)},
       "1st":{},"thumbnail":None}
    piexif.insert(piexif.dump(z),path)

def msgs(path):
    open(path,"w").write(
"# messages_export  (device backup, thread: 1 participant)\n"
"# schema: [msg_id] iso8601 | direction | peer | body\n"
"[0418] 2026-03-09T22:31:07 | OUT | +1-555-0173 | I know what you are doing with the NL exports.\n"
"[0419] 2026-03-09T22:33:44 | IN  | +1-555-0173 | You have no idea what you are talking about.\n"
"[0420] 2026-03-11T17:15:02 | OUT | +1-555-0173 | I have photos now. you will pay for what you did.\n"
"[0421] 2026-03-12T08:02:19 | OUT | +1-555-0173 | Compliance meeting set. This ends.\n"
"# --- calendar entry recovered from same backup ---\n"
f'# EVENT  when={WINDOW_WHEN}  where="{WINDOW_WHERE}"  note="he asked to meet here. alone."\n')

if __name__=="__main__":
    os.makedirs(OUT,exist_ok=True)
    pdf(f"{OUT}/cole_notes.pdf"); still(f"{OUT}/feed_still.jpg"); msgs(f"{OUT}/messages_export.txt")
    # self-verify
    t=subprocess.run(["pdftotext",f"{OUT}/cole_notes.pdf","-"],capture_output=True,text=True).stdout
    assert MAYA_DESIG in t, "FAIL: designation not recoverable"
    print("P100 built + verified. flag = number{%s}" % MAYA_DESIG)
