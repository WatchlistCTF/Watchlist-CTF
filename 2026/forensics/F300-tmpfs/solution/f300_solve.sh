#!/usr/bin/env bash
# ============================================================================
# F300 "Tmpfs" reference solver. Run it against the memory image:
#     bash f300_solve.sh reyes.lime
# Walks the intended solve path and prints the flag.
#
# Before you run it:
#   1. Get F300-tmpfs.7z from the 2026-files release and extract it.
#   2. Decompress the image:  xz -d reyes.lime.xz   (about 2 GB)
#   3. Install Volatility 3 so that `vol` is on your PATH.
#   4. Copy ubuntu-6.8.0-124-generic.json.xz into Volatility's symbols/linux/
#      folder. Leave it compressed.
# Also needs: openssl, python3. No network access.
# ============================================================================
set -u
DUMP="${1:?usage: f300_solve.sh <dump.lime>}"
W=/tmp/f300_solve; rm -rf "$W"; mkdir -p "$W"
say(){ printf '  %-26s %s\n' "$1" "$2"; }
echo "==== F300 solver ===="

# 1. triage -> find the vault loader and read the key TAIL from its argv
vol -f "$DUMP" linux.psaux > "$W/psaux.txt" 2>/dev/null
VPID=$(grep 'vault.py --keytail' "$W/psaux.txt" | awk '{print $1}' | head -1)
TAIL=$(grep -oP '(?<=--keytail )[0-9a-f]+' "$W/psaux.txt" | head -1)
say "vault pid" "${VPID:-NOT FOUND}"
say "key tail (argv)" "${TAIL:-NOT FOUND}"

# 2. read the key HEAD from the loader's environment
vol -f "$DUMP" linux.envars --pid "$VPID" > "$W/envars.txt" 2>/dev/null
# Volatility prints KEY and VALUE as separate columns; older output used KEY=VALUE. Accept both.
HEAD=$(grep -oP 'VAULT_KEY_HEAD[=\s]+\K[0-9a-f]+' "$W/envars.txt" | head -1)
say "key head (env)" "${HEAD:-NOT FOUND}"

# 3. recover the encrypted vault from the loader's memory and carve the blob
vol -f "$DUMP" -o "$W" linux.proc.Maps --pid "$VPID" --dump >/dev/null 2>&1
python3 - "$W" <<'PY'
import sys, glob, os
w = sys.argv[1]; blob = None
for f in glob.glob(os.path.join(w, "pid.*dmp")):
    d = open(f, "rb").read()
    i = d.find(b"VLT1")
    if i >= 0:
        blob = d[i:i + 4 + 288]      # 4-byte magic + 288-byte ciphertext
        break
open(os.path.join(w, "vault.enc"), "wb").write(blob or b"")
print("  blob carved from heap        " + ("yes" if blob else "NO"))
PY

# (alternative on a lightly-loaded asset: recover the deleted file from page cache)
# vol -f "$DUMP" -o "$W" linux.pagecache.InodePages --find /tmp/.cache/.vault.enc --dump

# 4. combine the split key and decrypt -> auth phrase -> flag
tail -c +5 "$W/vault.enc" > "$W/ct.bin"
PHRASE=$(openssl enc -d -aes-128-cbc -K "${HEAD}${TAIL}" \
         -iv 00000000000000000000000000000000 -in "$W/ct.bin" 2>/dev/null \
         | python3 -c "import sys,json;print(json.load(sys.stdin)['auth_phrase'])" 2>/dev/null)
say "auth_phrase" "${PHRASE:-DECRYPT FAILED}"
echo
if [ "${PHRASE:-}" = "volatile_storage_has_a_half_life" ]; then
  echo "  SOLVED ->  number{$PHRASE}"
else
  echo "  FAILED - inspect $W and the steps above"
fi
