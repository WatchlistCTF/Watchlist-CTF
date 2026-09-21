#!/usr/bin/env python3
"""
O300 "Aletheia" - reference blind solver.

Usage:  python3 o300_solve.py artifact

Identifies each nested layer by MAGIC BYTES (never by filename), decompresses it
with the right tool, and repeats until it hits the floor. The floor carries the
flag base64-encoded on one line. Requires these tools on PATH:
  apt:    gzip bzip2 xz zstd lz4 ncompress lzop lzip lrzip rzip arj cabextract gcab zip unzip p7zip-full
  source: zpaq lzfse bsc(libbsc) snzip   (build + symlink into /usr/local/bin)
"""
import os, sys, re, base64, shutil, tempfile, subprocess, contextlib
DN = subprocess.DEVNULL
def run(cmd, **kw): subprocess.run(cmd, check=True, stdout=kw.pop("stdout", DN), stderr=DN, **kw)

@contextlib.contextmanager
def tmp():
    d = tempfile.mkdtemp(prefix="aleth_")
    try: yield d
    finally: shutil.rmtree(d, ignore_errors=True)

def _pipe(cmd):
    def f(b):
        with tmp() as d:
            i, o = f"{d}/i", f"{d}/o"; open(i,"wb").write(b)
            with open(i,"rb") as fi, open(o,"wb") as fo: run(cmd, stdin=fi, stdout=fo)
            return open(o,"rb").read()
    return f
def _io(mk):
    def f(b):
        with tmp() as d:
            i, o = f"{d}/i", f"{d}/o"; open(i,"wb").write(b); run(mk(i,o)); return open(o,"rb").read()
    return f
def _fb(mk, suf):
    def f(b):
        with tmp() as d:
            i, o = f"{d}/i{suf}", f"{d}/o"; open(i,"wb").write(b); run(mk(i,o))
            if not os.path.exists(o) and os.path.exists(o+suf): os.rename(o+suf,o)
            return open(o,"rb").read()
    return f
def _arc(extract):
    def f(b):
        with tmp() as d:
            a = f"{d}/a"; open(a,"wb").write(b); o = f"{d}/o"; os.makedirs(o); extract(a,o)
            fs = [os.path.join(o,x) for x in os.listdir(o) if os.path.isfile(os.path.join(o,x))]
            if len(fs) == 1: return open(fs[0],"rb").read()
            for x in fs:                                    # tar-decoy: skip the bait
                bb = open(x,"rb").read()
                if detect(bb) not in ("plaintext","unknown"): return bb
            raise RuntimeError("only decoys found in tar")
    return f

def ex_zip(a,o):  run(["unzip","-o","-q","-j",a,"-d",o])
def ex_7z(a,o):   run(["7z","e","-y","-bso0","-bsp0",f"-o{o}",a])
def ex_arj(a,o):  shutil.copy(a,a+".arj"); run(["arj","e","-y",os.path.abspath(a+".arj")], cwd=o)
def ex_cab(a,o):  run(["cabextract","-q","-d",o,a])
def ex_zpaq(a,o): shutil.copy(a,a+".zpaq"); run(["zpaq","x",os.path.abspath(a+".zpaq")], cwd=o)
def ex_tar(a,o):  run(["tar","xf",a,"-C",o])

DECODE = {
  "gzip": _pipe(["gzip","-dc"]), "bzip2": _pipe(["bzip2","-dc"]),
  "xz": _pipe(["xz","-dc"]), "lzma": _pipe(["xz","-F","lzma","-dc"]),
  "zstd": _pipe(["zstd","-q","-dc"]), "lz4": _pipe(["lz4","-q","-dc"]),
  "compress": _io(lambda i,o:["bash","-c",f"gzip -dc {i} > {o}"]),
  "lzop": _pipe(["lzop","-dc"]), "lzip": _pipe(["lzip","-dc"]),
  "snzip": _io(lambda i,o:["bash","-c",f"snzip -d -c {i} > {o}"]),
  "lzfse": _io(lambda i,o:["lzfse","-decode","-i",i,"-o",o]),
  "bsc":  _io(lambda i,o:["bsc","d",i,o]),
  "rzip": _fb(lambda i,o:["rzip","-d","-k","-f","-o",o,i], ".rz"),
  "lrzip":_fb(lambda i,o:["lrzip","-q","-d","-f","-o",o,i], ".lrz"),
  "zip": _arc(ex_zip), "7z": _arc(ex_7z), "arj": _arc(ex_arj),
  "cab": _arc(ex_cab), "zpaq": _arc(ex_zpaq), "tar": _arc(ex_tar),
  "base64": lambda b: base64.b64decode(b), "ascii85": lambda b: base64.a85decode(b),
}

B64 = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\r\n")
A85 = set(range(0x21,0x76)) | set(b"z\r\n")
def _txt(b): return b and all(c in (9,10,13) or 32 <= c <= 126 for c in b)
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
    if _txt(b):
        if all(c in B64 for c in b): return "base64"
        if all(c in A85 for c in b): return "ascii85"
        return "plaintext"
    return "unknown"

def solve(path):
    blob = open(path,"rb").read(); n = 0
    while True:
        fmt = detect(blob)
        if fmt == "plaintext":
            t = blob.decode("latin1")
            m = re.search(r"number\{[^}]+\}", t)
            if not m:
                for tok in t.split():
                    try:
                        mm = re.search(rb"number\{[^}]+\}", base64.b64decode(tok, validate=True))
                        if mm: print(f"[floor] decoded base64 line -> flag"); return mm.group(0).decode(), n
                    except Exception: pass
            if m: return m.group(0), n
            raise RuntimeError("reached text but found no flag")
        if fmt == "unknown":
            raise RuntimeError(f"unknown format at layer {n+1}: {blob[:8].hex()}")
        n += 1; print(f"layer {n:2d}: {fmt}")
        blob = DECODE[fmt](blob)

if __name__ == "__main__":
    art = sys.argv[1] if len(sys.argv) > 1 else "artifact"
    flag, n = solve(art)
    print(f"\npeeled {n} layers\nFLAG: {flag}")
