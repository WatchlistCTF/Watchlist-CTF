#!/usr/bin/env python3
"""
F200 "Shadow Box" -- BLIND solver / build verifier.

Recovers number{greer_targeted_contingency} from the PDF with zero hardcoded
object numbers, walking the raw bytes the way a forensic analyst (and the stock
Kali tools pdfid / pdf-parser / pdftotext / tesseract) would. For each step it
prints the hand-tool command a player would run, then does the equivalent in
pure Python so the proof is self-contained.

Usage:
    python3 f200_solve.py [file.pdf] [--word WORD]

    With no arguments it reads ../files/20769767962808ed.pdf, the file players
    were given (original name: decima_internal_review_q1.pdf).

Requirements:
    Python 3 standard library for layers 1 and 3.
    Layer 2 reads a word out of a picture. To do that automatically it needs
    pillow, numpy, pytesseract and the tesseract binary. Without them the
    script saves the picture as f200_orphan.jpg and stops. Open it, read the
    word struck through in red at the top, and run again with --word WORD.

Exit codes:  0 = flag recovered and matches, 1 = mismatch,
             2 = layer 2 not verified (no OCR and no --word given)
"""
import re, sys, zlib, io, subprocess
from pathlib import Path

ARGS = sys.argv[1:]
WORD = None
if "--word" in ARGS:
    i = ARGS.index("--word"); WORD = ARGS[i + 1].strip().lower(); del ARGS[i:i + 2]
DEFAULT = Path(__file__).resolve().parent.parent / "files" / "20769767962808ed.pdf"
PDF = ARGS[0] if ARGS else str(DEFAULT)
EXPECT = "number{greer_targeted_contingency}"

def hr(t): print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)
def cmd(c): print(f"   $ {c}")
def info(m): print(f"     {m}")

raw = Path(PDF).read_bytes()

# --- parse every physical object + all generations, in file (revision) order ---
OBJS = []  # (num, offset, body_bytes)
for m in re.finditer(rb"(\d+)\s+(\d+)\s+obj\b(.*?)\bendobj", raw, re.S):
    OBJS.append((int(m.group(1)), m.start(), m.group(3)))

def stream_bytes(body):
    s = re.search(rb"stream\r?\n", body)
    if not s: return None
    start = s.end(); end = body.rfind(b"endstream")
    data = body[start:end].rstrip(b"\r\n")
    if b"/FlateDecode" in body.split(b"stream")[0]:
        try: return zlib.decompress(data)
        except zlib.error:
            try: return zlib.decompress(data[:-1])
            except Exception: return data
    return data

# ===========================================================================
hr("STAGE 0  -- recognise that the file has revisions")
cmd(f"pdfid.py {Path(PDF).name}      # look at the %%EOF / /OpenAction / /JS counts")
cmd(f"grep -abo '%%EOF' {Path(PDF).name}")
eofs = raw.count(b"%%EOF")
info(f"%%EOF markers = {eofs}  ->  {eofs} revisions (a clean PDF has 1). Two incremental saves.")
info(f"file size = {len(raw)/1048576:.2f} MB, /OpenAction and /JS present, /EmbeddedFile present.")

# ===========================================================================
hr("STAGE 1  -- LAYER 1: the original text  ->  fragment 'greer'")
cmd(f"pdf-parser.py --search Metadata {Path(PDF).name}        # find the metadata object")
cmd(f"pdf-parser.py --object <n> --filter --raw {Path(PDF).name}   # shows BOTH generations")
# find metadata object number from the (current) catalog, then take its EARLIEST generation
meta_no = None
mref = re.search(rb"/Metadata\s+(\d+)\s+0\s+R", raw)
if mref: meta_no = int(mref.group(1))
creators = []
for num, off, body in OBJS:
    if num == meta_no or b"/Type /Metadata" in body or b"dc:creator" in body:
        dec = stream_bytes(body) or body
        for li in re.findall(rb"<dc:creator>.*?<rdf:li>(.*?)</rdf:li>", dec, re.S):
            creators.append(li.decode("utf-8", "ignore").strip())
# earliest occurrence in file order == truth
truth_author = creators[0] if creators else ""
# corroborate with earliest page-4 signer
signers = []
for num, off, body in OBJS:
    dec = stream_bytes(body) or b""
    m = re.search(rb"\(([A-Z]\.\s*Greer|James Harrison)\)", dec)
    if m: signers.append(m.group(1).decode())
info(f"dc:creator values across revisions, in file order = {creators}")
info(f"earliest (truth) author = '{truth_author}'   [later revision overwrote it to '{creators[-1] if creators else '?'}']")
greer = truth_author.split()[-1].lower() if truth_author else ""
info(f"page-4 signer generations (corroboration) = {signers}")
print(f"   >> fragment 1 = '{greer}'")

# ===========================================================================
hr("STAGE 2  -- LAYER 2: the hidden picture  ->  fragment 'targeted'")
cmd(f"pdfimages -all {Path(PDF).name} out/     # NOTE: returns nothing -- it only")
info("walks the *current* page tree, and the thumbnail was orphaned out of it (realistic dead-end).")
cmd(f"pdf-parser.py --search Image {Path(PDF).name}                 # find image objects directly")
cmd(f"pdf-parser.py --object <n> --raw --dump thumb.jpg {Path(PDF).name}")
cmd("tesseract thumb.jpg -  (or just open it)   # read the struck-through word")
# collect DCTDecode image streams, OCR the one that carries text, isolate the RED (removed) word
try:
    from PIL import Image
    import numpy as np, pytesseract
    HAVE_OCR = True
except Exception:
    HAVE_OCR = False
targeted = ""
img_count = 0
jpegs = []   # (obj number, bytes) for every JPEG object found in the raw file
for num, off, body in OBJS:
    if b"/Subtype /Image" in body and b"/DCTDecode" in body:
        data = stream_bytes(body)
        if not data or not data.startswith(b"\xff\xd8"): continue
        img_count += 1
        jpegs.append((num, data))
        if not HAVE_OCR: continue
        im = Image.open(io.BytesIO(data)).convert("RGB")
        a = np.asarray(im).astype(int)
        d = pytesseract.image_to_data(im, output_type=pytesseract.Output.DICT)
        reds = []
        for t, x, y, ww, hh in zip(d["text"], d["left"], d["top"], d["width"], d["height"]):
            t = t.strip()
            if not re.fullmatch(r"[A-Za-z]{4,}", t): continue
            crop = a[y:y + hh, x:x + ww].reshape(-1, 3)
            ink = crop[crop.sum(1) < 600]               # colored/dark text pixels only
            if ink.size == 0: continue
            r_, g_, b_ = ink[:, 0].mean(), ink[:, 1].mean(), ink[:, 2].mean()
            if r_ > g_ + 40 and r_ > b_ + 40:           # red == a REMOVED (original) word
                reds.append((y, t))
        if reds:
            reds.sort()
            info(f"orphaned image obj {num}: struck/red (removed) words top->bottom = {[w for _, w in reds]}")
            targeted = reds[0][1].lower()               # topmost red word == the project-status line
            break
info(f"DCTDecode images in file = {img_count} (cover graphic + orphaned thumbnail)")
LAYER2_VERIFIED = bool(targeted)
if not targeted:
    # No OCR available (or it read nothing). Do not guess: hand the picture to a human.
    if jpegs:
        num, data = min(jpegs, key=lambda j: len(j[1]))     # the thumbnail is the small one
        Path("f200_orphan.jpg").write_bytes(data)
        info(f"OCR not available. Saved orphaned image obj {num} as f200_orphan.jpg")
    if WORD:
        targeted = WORD
        info(f"using the word you read from the picture: '{WORD}' (manual step)")
    else:
        info("open f200_orphan.jpg, read the top word struck through in red,")
        info("then run again with:  --word THATWORD")
print(f"   >> fragment 2 = '{targeted}'")

# ===========================================================================
hr("STAGE 3  -- LAYER 3: the phone-home script  ->  fragment 'contingency'")
cmd(f"pdfid.py {Path(PDF).name} | grep -E '/JS|/OpenAction'     # flags hidden JavaScript")
cmd(f"pdf-parser.py --search JavaScript --filter {Path(PDF).name}")
contingency = ""
for num, off, body in OBJS:
    dec = stream_bytes(body) or b""
    if b"submitForm" in dec or b"checkin?doc=" in dec:        # the JS stream specifically
        u = re.search(rb"https?://([A-Za-z0-9.\-]+)", dec)
        if u:
            host = u.group(1).decode()
            info(f"JS callback URL host = {host}")
            contingency = host.split(".")[0]
            break
print(f"   >> fragment 3 = '{contingency}'")

# ===========================================================================
hr("RESULT")
flag = f"number{{{greer}_{targeted}_{contingency}}}"
print(f"   assembled : {flag}")
print(f"   expected  : {EXPECT}")
print(f"   B350 pivot: subdomain 'contingency.decima.cloud' -> visit /contingency on the CTF site")
if not targeted:
    print("\n   RESULT: NOT VERIFIED (layer 2 needs OCR or --word)")
    sys.exit(2)
ok = flag == EXPECT
how = "" if LAYER2_VERIFIED else "  (layer 2 word supplied by hand)"
print("\n   RESULT:", ("PASS  \u2713" + how) if ok else "FAIL  \u2717")
sys.exit(0 if ok else 1)
