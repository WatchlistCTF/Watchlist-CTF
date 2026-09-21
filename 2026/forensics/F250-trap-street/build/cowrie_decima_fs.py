#!/usr/bin/env python3
"""
cowrie_decima_fs.py  -  inject the F250 "Decima staging relay" filetree into a
standard Cowrie install (honeyfs content + fs.pickle listing metadata).

USAGE (run on the Cowrie host, after a standard Cowrie install):
    python3 cowrie_decima_fs.py /path/to/cowrie ./decima_subject_register.xlsx

Defaults: COWRIE=~/cowrie, pickle=$COWRIE/share/cowrie/fs.pickle, honeyfs=$COWRIE/honeyfs
It backs up the pickle first (fs.pickle.bak-TIMESTAMP). Re-running is safe (idempotent).
After running: restart Cowrie so it reloads the filesystem.
"""
import os, sys, time, pickle, shutil, tarfile, io
from datetime import datetime, timezone

# ---- Cowrie fs.pickle constants (src/cowrie/shell/fs.py) ----
A_NAME, A_TYPE, A_UID, A_GID, A_SIZE, A_MODE, A_CTIME, A_CONTENTS, A_TARGET, A_REALFILE = range(10)
T_LINK, T_DIR, T_FILE, T_BLK, T_CHR, T_SOCK, T_FIFO = range(7)
DIR_MODE, FILE_MODE, EXEC_MODE = 0o40755, 0o100644, 0o100755

# ---- args ----
COWRIE = os.path.abspath(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/cowrie"))
CANARY = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else "./decima_subject_register.xlsx")
HONEYFS = os.path.abspath(os.path.expanduser(os.environ.get("COWRIE_HONEYFS", os.path.join(COWRIE, "honeyfs"))))
PICKLE  = os.path.abspath(os.path.expanduser(os.environ.get("COWRIE_PICKLE",  os.path.join(COWRIE, "share", "cowrie", "fs.pickle"))))

def die(m): print("ERROR:", m); sys.exit(1)
if not os.path.isfile(PICKLE):
    die(f"fs.pickle not found at {PICKLE}\n"
        "  pip-install layout? materialize a writable copy first:\n"
        "    python -c \"from cowrie.core.resources import read_data_bytes; "
        "open('var/lib/cowrie/fs.pickle','wb').write(read_data_bytes('fs.pickle'))\"\n"
        "  then re-run with COWRIE_PICKLE pointing at it.")
if not os.path.isfile(CANARY):  die(f"canary not found at {CANARY} (pass it as arg 2)")
os.makedirs(HONEYFS, exist_ok=True)   # create the honeyfs override dir if it doesn't exist yet

def ep(s):  # "2026-04-24 13:45" -> epoch seconds (UTC)
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp())

# ---- the staging-relay content (virtual path -> (bytes, mode, mtime)) ----
MOTD = (b"============================================================\n"
        b"  DECIMA TECHNOLOGIES // NORTHERN LIGHTS\n"
        b"  STAGING RELAY  dcm-stg-fra-04   (FRA region)\n"
        b"  AUTHORIZED ACCESS ONLY. Activity is logged.\n"
        b"============================================================\n")
SYNC_SH = (b"#!/bin/sh\n"
           b"# decima staging sync - pushes queued objects offsite every 15m\n"
           b"SRC=/opt/decima/staging/outbound/\n"
           b"DEST=relay@offsite-fra:/incoming/\n"
           b'rsync -az --remove-source-files "$SRC" "$DEST" >> /var/log/decima-sync.log 2>&1\n')
CRON = b"*/15 * * * * root /opt/decima/bin/sync.sh\n"
TRANSFER_LOG = (b"2026-04-22 09:14 staged   decima_archive_2025.tar.gz\n"
                b"2026-04-24 13:31 staged   decima_subject_register.xlsx  (Q4 relevance review)\n"
                b"2026-04-24 13:31 queued   decima_subject_register.xlsx  FRA -> offsite\n")
JVOSS_HIST = (b"cd /opt/decima/staging/outbound\n"
              b"ls -lt\n"
              b"sha256sum decima_subject_register.xlsx\n"
              b"cat .transfer.log\n"
              b"exit\n")
JVOSS_NOTES = (b"Q4 relevance review exported and dropped in staging/outbound for the\n"
               b"offsite transfer. sync.sh picks it up on the :15. Do not touch the\n"
               b"archive, that's last quarter's.\n   - JV\n")

# a small but real gzip tarball for the decoy (so `file` says gzip and it has size)
def make_decoy_targz():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for nm, data in [("archive/manifest.txt", b"decima archive 2025 - cold storage index\n"),
                         ("archive/q3_rollup.csv", b"region,count\nFRA-04,118\nNYC-01,205\n")]:
            ti = tarfile.TarInfo(nm); ti.size = len(data); ti.mtime = ep("2026-03-20 09:00")
            t.addfile(ti, io.BytesIO(data))
    return buf.getvalue()

# files: (virtual_path, bytes, mode, "YYYY-MM-DD HH:MM")
files = [
    ("/etc/hostname",                                   b"dcm-stg-fra-04\n",   FILE_MODE, "2026-01-05 08:00"),
    ("/etc/motd",                                       MOTD,                  FILE_MODE, "2026-01-05 08:00"),
    ("/etc/cron.d/decima-sync",                         CRON,                  FILE_MODE, "2026-01-06 10:00"),
    ("/opt/decima/bin/sync.sh",                         SYNC_SH,               EXEC_MODE, "2026-01-06 10:00"),
    ("/opt/decima/staging/inbound/.keep",              b"",                    FILE_MODE, "2026-01-06 10:00"),
    ("/opt/decima/staging/outbound/.transfer.log",      TRANSFER_LOG,          FILE_MODE, "2026-04-24 13:31"),
    ("/opt/decima/staging/outbound/decima_archive_2025.tar.gz", make_decoy_targz(), FILE_MODE, "2026-03-20 09:00"),
    ("/home/jvoss/.bash_history",                       JVOSS_HIST,            FILE_MODE, "2026-04-24 13:45"),
    ("/home/jvoss/notes.txt",                           JVOSS_NOTES,           FILE_MODE, "2026-04-24 13:20"),
    # the canary: newest mtime in outbound so `ls -lt` surfaces it first
    ("/opt/decima/staging/outbound/decima_subject_register.xlsx", open(CANARY, "rb").read(), FILE_MODE, "2026-04-24 13:46"),
]

# ---- 1) write content into honeyfs + remember real paths/sizes ----
placed = []  # (vpath, real_abs_path, size, mtime_epoch, mode)
for vpath, data, mode, when in files:
    real = os.path.join(HONEYFS, vpath.lstrip("/"))
    os.makedirs(os.path.dirname(real), exist_ok=True)
    with open(real, "wb") as fh: fh.write(data)
    mt = ep(when)
    os.utime(real, (mt, mt))
    placed.append((vpath, real, len(data), mt, mode))

# ---- 2) patch fs.pickle ----
shutil.copy2(PICKLE, PICKLE + ".bak-" + time.strftime("%Y%m%d-%H%M%S"))
with open(PICKLE, "rb") as fh: root = pickle.load(fh)
if root[A_TYPE] != T_DIR or not isinstance(root[A_CONTENTS], list):
    die("unexpected pickle root format")

def find_child(node, name):
    for c in node[A_CONTENTS]:
        if c[A_NAME] == name: return c
    return None

def ensure_dir(path, ctime):
    node = root
    for part in [p for p in path.strip("/").split("/") if p]:
        c = find_child(node, part)
        if c is None:
            c = [part, T_DIR, 0, 0, 4096, DIR_MODE, ctime, [], None, None]
            node[A_CONTENTS].append(c)
        elif c[A_TYPE] != T_DIR:
            die(f"{part} exists and is not a directory")
        node = c
    return node

def add_file(dirnode, name, size, ctime, realfile, mode):
    dirnode[A_CONTENTS][:] = [c for c in dirnode[A_CONTENTS] if c[A_NAME] != name]
    dirnode[A_CONTENTS].append([name, T_FILE, 0, 0, size, mode, ctime, [], None, realfile])

for vpath, real, size, mt, mode in placed:
    d = ensure_dir(os.path.dirname(vpath), mt)
    add_file(d, os.path.basename(vpath), size, mt, real, mode)

with open(PICKLE, "wb") as fh: pickle.dump(root, fh)

# ---- 3) verify: print the injected subtrees + ls -lt ordering of outbound ----
def get_path(path):
    node = root
    for part in [p for p in path.strip("/").split("/") if p]:
        node = find_child(node, part)
        if node is None: return None
    return node

def show(path):
    n = get_path(path)
    print(f"\n{path}/")
    if not n: print("  (missing!)"); return
    for c in sorted(n[A_CONTENTS], key=lambda x: -x[A_CTIME]):
        kind = "d" if c[A_TYPE] == T_DIR else "-"
        ts = datetime.fromtimestamp(c[A_CTIME], timezone.utc).strftime("%Y-%m-%d %H:%M")
        print(f"  {kind} {c[A_SIZE]:>8}  {ts}  {c[A_NAME]}")

print("OK: patched", PICKLE)
print("backup written alongside it (fs.pickle.bak-*)")
for p in ["/opt/decima", "/opt/decima/bin", "/opt/decima/staging/outbound", "/home/jvoss", "/etc/cron.d"]:
    show(p)
ob = get_path("/opt/decima/staging/outbound")
first = sorted(ob[A_CONTENTS], key=lambda x: -x[A_CTIME])[0][A_NAME]
print(f"\nls -lt outbound -> newest first is: {first}")
print("CANARY SURFACES FIRST:" , first == "decima_subject_register.xlsx")
print("\nNOW RESTART COWRIE so it reloads the filesystem.")
