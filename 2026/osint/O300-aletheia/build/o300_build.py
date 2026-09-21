#!/usr/bin/env python3
"""
O300 "Aletheia" - 42-layer matryoshka builder + blind peeler.

build:  floor = base64(flag) inside a message -> wrap 42x (common outer -> obscure core)
peel:   identify each layer by MAGIC BYTES only (no knowledge of the sequence),
        decompress with the right tool, reach the floor in exactly 42 steps.
"""
import os, sys, re, base64, shutil, tempfile, subprocess, contextlib

TOOLDIR = "o300-work/tools"
ZPAQ  = f"{TOOLDIR}/zpaq/zpaq"
LZFSE = f"{TOOLDIR}/lzfse/build/bin/lzfse"
BSC   = f"{TOOLDIR}/libbsc/build/bsc"
SNZIP = f"{TOOLDIR}/snzip/snzip"
DN = subprocess.DEVNULL
FLAG = "number{forty_two_layers_of_aletheia}"

def run(cmd, **kw):
    subprocess.run(cmd, check=True, stdout=kw.pop("stdout", DN), stderr=DN, **kw)

@contextlib.contextmanager
def tmp():
    d = tempfile.mkdtemp(prefix="o300_")
    try: yield d
    finally: shutil.rmtree(d, ignore_errors=True)

# ---------- STREAM formats (stdin->stdout via real-file redirection) ----------
def _stream(ccmd, dcmd):
    def comp(b):
        with tmp() as d:
            ip, op = f"{d}/in", f"{d}/out"; open(ip,"wb").write(b)
            with open(ip,"rb") as i, open(op,"wb") as o: run(ccmd, stdin=i, stdout=o)
            return open(op,"rb").read()
    def deco(b):
        with tmp() as d:
            ip, op = f"{d}/in", f"{d}/out"; open(ip,"wb").write(b)
            with open(ip,"rb") as i, open(op,"wb") as o: run(dcmd, stdin=i, stdout=o)
            return open(op,"rb").read()
    return comp, deco

# ---------- FILEIO formats (-i in -o out) ----------
def _fileio(ccmd, dcmd):
    def comp(b):
        with tmp() as d:
            ip, op = f"{d}/in", f"{d}/out"; open(ip,"wb").write(b)
            run(ccmd(ip, op)); return open(op,"rb").read()
    def deco(b):
        with tmp() as d:
            ip, op = f"{d}/in", f"{d}/out"; open(ip,"wb").write(b)
            run(dcmd(ip, op)); return open(op,"rb").read()
    return comp, deco

# ---------- FILEBASED formats (rzip/lrzip; tolerant of appended suffix) ----------
def _filebased(ccmd, dcmd, suf):
    def comp(b):
        with tmp() as d:
            ip, op = f"{d}/in", f"{d}/out"; open(ip,"wb").write(b)
            run(ccmd(ip, op))
            if not os.path.exists(op) and os.path.exists(op+suf): os.rename(op+suf, op)
            return open(op,"rb").read()
    def deco(b):
        with tmp() as d:
            ip, op = f"{d}/in{suf}", f"{d}/out"; open(ip,"wb").write(b)
            run(dcmd(ip, op))
            if not os.path.exists(op) and os.path.exists(op+suf): os.rename(op+suf, op)
            return open(op,"rb").read()
    return comp, deco

# ---------- ARCHIVE formats (wrap one inner file; extract + pick) ----------
def _archive(make, extract):
    def comp(b):
        with tmp() as d:
            inner = f"{d}/ledger"; open(inner,"wb").write(b)
            op = f"{d}/out"; make(d, inner, op)
            return open(op,"rb").read()
    def deco(b):
        with tmp() as d:
            arch = f"{d}/arch"; open(arch,"wb").write(b)
            out = f"{d}/out"; os.makedirs(out)
            extract(arch, out)
            files = [os.path.join(out,f) for f in os.listdir(out) if os.path.isfile(os.path.join(out,f))]
            if len(files) == 1: return open(files[0],"rb").read()
            for f in files:                       # tar-decoy: pick the real compressed layer
                bb = open(f,"rb").read()
                if detect(bb) not in ("plaintext","unknown"): return bb
            raise RuntimeError("no real layer among decoys")
    return comp, deco

# archive make/extract helpers
def mk_zip(d,inner,op):  run(["zip","-q","-X","-j",f"{d}/a.zip","ledger"], cwd=d); os.rename(f"{d}/a.zip",op)
def ex_zip(a,o):         run(["unzip","-o","-q","-j",a,"-d",o])
def mk_7z(d,inner,op):   run(["7z","a","-t7z","-bso0","-bsp0",f"{d}/a.7z","ledger"], cwd=d); os.rename(f"{d}/a.7z",op)
def ex_7z(a,o):          run(["7z","e","-y","-bso0","-bsp0",f"-o{o}",a])
def mk_arj(d,inner,op):  run(["arj","a","-i","-y","arc","ledger"], cwd=d); os.rename(f"{d}/arc.arj",op)
def ex_arj(a,o):         shutil.copy(a,a+".arj"); run(["arj","e","-y",os.path.abspath(a+".arj")], cwd=o)
def mk_cab(d,inner,op):  run(["gcab","-c",op,"ledger"], cwd=d)
def ex_cab(a,o):         run(["cabextract","-q","-d",o,a])
def mk_zpaq(d,inner,op): run([ZPAQ,"a","arc.zpaq","ledger"], cwd=d); os.rename(f"{d}/arc.zpaq",op)
def ex_zpaq(a,o):        shutil.copy(a,a+".zpaq"); run([ZPAQ,"x",os.path.abspath(a+".zpaq")], cwd=o)
def mk_tardecoy(d,inner,op):
    os.rename(inner, f"{d}/server.log")            # real next layer, boring name
    open(f"{d}/flag.txt","w").write("nice try. the floor is deeper than this.\n")
    open(f"{d}/README","w").write("Aletheia Research internal staging. Do not distribute.\n")
    run(["tar","cf",op,"-C",d,"server.log","flag.txt","README"])
def ex_tar(a,o):         run(["tar","xf",a,"-C",o])

COMP, DECO = {}, {}
def reg(name, pair): COMP[name], DECO[name] = pair

reg("gzip",     _stream(["gzip","-c","-9"],            ["gzip","-dc"]))
reg("bzip2",    _stream(["bzip2","-c","-9"],           ["bzip2","-dc"]))
reg("xz",       _stream(["xz","-c","-9","-T1"],        ["xz","-dc"]))
reg("lzma",     _stream(["xz","-F","lzma","-c"],       ["xz","-F","lzma","-dc"]))
reg("zstd",     _stream(["zstd","-q","-19","-c"],      ["zstd","-q","-dc"]))
reg("lz4",      _stream(["lz4","-q","-9","-c"],        ["lz4","-q","-dc"]))
reg("compress", _fileio(lambda i,o:["bash","-c",f"compress -c {i} > {o}"],
                        lambda i,o:["bash","-c",f"gzip -dc {i} > {o}"]))
reg("lzop",     _stream(["lzop","-c","-9"],            ["lzop","-dc"]))
reg("lzip",     _stream(["lzip","-c","-9"],            ["lzip","-dc"]))
reg("snzip",    _fileio(lambda i,o:["bash","-c",f"{SNZIP} -c {i} > {o}"],
                        lambda i,o:["bash","-c",f"{SNZIP} -d -c {i} > {o}"]))
reg("lzfse",    _fileio(lambda i,o:[LZFSE,"-encode","-i",i,"-o",o],
                        lambda i,o:[LZFSE,"-decode","-i",i,"-o",o]))
reg("bsc",      _fileio(lambda i,o:[BSC,"e",i,o],      lambda i,o:[BSC,"d",i,o]))
reg("rzip",     _filebased(lambda i,o:["rzip","-k","-f","-o",o,i],
                           lambda i,o:["rzip","-d","-k","-f","-o",o,i], ".rz"))
reg("lrzip",    _filebased(lambda i,o:["lrzip","-q","-L9","-f","-o",o,i],
                           lambda i,o:["lrzip","-q","-d","-f","-o",o,i], ".lrz"))
reg("zip",      _archive(mk_zip,  ex_zip))
reg("7z",       _archive(mk_7z,   ex_7z))
reg("arj",      _archive(mk_arj,  ex_arj))
reg("cab",      _archive(mk_cab,  ex_cab))
reg("zpaq",     _archive(mk_zpaq, ex_zpaq))
reg("tardecoy", _archive(mk_tardecoy, ex_tar))   # detected as 'tar' on peel
reg("base64",   (lambda b: base64.b64encode(b),       lambda b: base64.b64decode(b)))
reg("ascii85",  (lambda b: base64.a85encode(b),       lambda b: base64.a85decode(b)))
DECO["tar"] = DECO["tardecoy"]   # peel detects 'tar' by magic; reuse decoy extractor

# ---------- detection (magic bytes only) ----------
B64 = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\r\n")
A85 = set(range(0x21,0x76)) | set(b"z\r\n")
def _is_text(b): return b and all(c in (9,10,13) or 32 <= c <= 126 for c in b)

def detect(b):
    if b[:2]==b"\x1f\x8b": return "gzip"
    if b[:3]==b"BZh": return "bzip2"
    if b[:6]==b"\xfd7zXZ\x00": return "xz"
    if b[:3]==b"\x5d\x00\x00": return "lzma"
    if b[:4]==b"\x28\xb5\x2f\xfd": return "zstd"
    if b[:4]==b"\x04\x22\x4d\x18": return "lz4"
    if b[:2]==b"\x1f\x9d": return "compress"
    if b[:4]==b"\x89LZO": return "lzop"
    if b[:4]==b"LZIP": return "lzip"
    if b[:4]==b"LRZI": return "lrzip"
    if b[:4]==b"RZIP": return "rzip"
    if b[:6]==b"7z\xbc\xaf\x27\x1c": return "7z"
    if b[:4]==b"PK\x03\x04": return "zip"
    if b[:2]==b"\x60\xea": return "arj"
    if b[:4]==b"MSCF": return "cab"
    if b[:4]==b"7kSt": return "zpaq"
    if b[:3]==b"bvx": return "lzfse"
    if b[:4]==b"bsc1": return "bsc"
    if b[:4]==b"\xff\x06\x00\x00" and b[4:10]==b"sNaPpY": return "snzip"
    if len(b)>=262 and b[257:262]==b"ustar": return "tar"
    if _is_text(b):
        if all(c in B64 for c in b): return "base64"
        if all(c in A85 for c in b): return "ascii85"
        return "plaintext"
    return "unknown"

# ---------- the 42-layer sequence (peel order: OUTERMOST first) ----------
PEEL_ORDER = (
    # common (15): mainstream + base64 + tar-decoy gotchas
    ["gzip","xz","bzip2","base64","zstd","7z","lzma","lz4","tardecoy","compress","zip","xz","bzip2","zstd","gzip"]
    # less-obscure (15): apt-but-niche + ascii85 gotcha
  + ["lzop","lzip","lrzip","arj","ascii85","rzip","cab","lzop","lzip","lrzip","arj","rzip","cab","lzip","lzop"]
    # more-obscure (12): the four compile-from-source spikes
  + ["zpaq","lzfse","bsc","snzip","zpaq","lzfse","bsc","snzip","zpaq","lzfse","bsc","snzip"]
)

FLOOR = (
    "[ ALETHEIA // FLOOR ]\n"
    "You unwrapped me forty-two times. Most stop at ten.\n"
    "Concealment has a floor, and you are standing on it.\n\n"
    "decode:\n" + base64.b64encode(FLAG.encode()).decode() + "\n\n"
    "Project: Contingency\n"
).encode()

def build():
    blob = FLOOR
    for fmt in reversed(PEEL_ORDER):
        blob = COMP[fmt](blob)
    return blob

def peel(blob, verbose=False):
    count = 0
    while True:
        fmt = detect(blob)
        if fmt == "plaintext":
            text = blob.decode("latin1")
            m = re.search(r"number\{[^}]+\}", text)
            if not m:
                for tok in text.split():
                    try:
                        dec = base64.b64decode(tok, validate=True)
                        mm = re.search(rb"number\{[^}]+\}", dec)
                        if mm: m = re.match(r"(.*)", mm.group(0).decode()); break
                    except Exception: pass
            if m:
                if verbose: print(f"  [floor reached after {count} layers]")
                return m.group(0), count
            raise RuntimeError("plaintext but no flag")
        if fmt == "unknown":
            raise RuntimeError(f"unknown layer at step {count+1}: {blob[:8].hex()}")
        count += 1
        if verbose: print(f"  layer {count:2d}: {fmt}")
        blob = DECO[fmt](blob)

if __name__ == "__main__":
    print("building 42-layer artifact ...")
    art = build()
    open("o300-work/artifact","wb").write(art)
    print(f"  artifact size: {len(art)} bytes, outer magic: {art[:4].hex()} (detect={detect(art)})")
    print("blind peel (magic bytes only):")
    flag, n = peel(art, verbose=True)
    print(f"\nRESULT: flag={flag}  layers={n}")
    assert n == 42, f"expected 42 layers, got {n}"
    assert flag == FLAG, f"flag mismatch: {flag}"
    # anti-shortcut: flag must not survive in the artifact
    import subprocess as sp
    hit = sp.run(["bash","-c","strings o300-work/artifact | grep -c 'aletheia' || true"],
                 capture_output=True, text=True).stdout.strip()
    print(f"strings|grep aletheia in artifact: {hit} (want 0)")
    print("OK" if (n==42 and flag==FLAG) else "FAIL")
