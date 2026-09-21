#!/usr/bin/env bash
# ============================================================================
#  WATCHLIST CTF - L400 "Mission Creep" - SOLVER / ANSWER KEY
#
#  Documents AND verifies the intended solve path. Get the disk image from the
#  2026-files release (L400-mission-creep.7z), extract and decompress it, then
#  mount it read-only and point ROOT at the mount:
#    ROOT=/mnt/l400  bash l400_solve.sh
#  Needs: sleuthkit/plaso to build the timeline yourself; the script itself
#  only needs coreutils, grep and strings. It never writes to the target.
#
#  It walks all five stages exactly as a DFIR player would, prints what they'd
#  see, and asserts each pivot is recoverable. READ-ONLY: it never modifies the
#  target. Exit 0 = the whole chain solves; non-zero = a stage broke.
# ============================================================================
set -uo pipefail

ROOT="${ROOT:-/}"                       # mount point of the image, or / for the live box
FLAG='number{a_foothold_is_never_just_a_foothold}'
MAGIC='C0NT1NGENCY'

c_reset=$'\033[0m'; c_bold=$'\033[1m'; c_grn=$'\033[32m'; c_red=$'\033[31m'; c_cyn=$'\033[36m'; c_dim=$'\033[2m'
PASS=0; FAIL=0
stage(){ printf '\n%s%s━━ %s %s\n' "$c_bold" "$c_cyn" "$1" "$c_reset"; }
note(){  printf '   %s· %s%s\n' "$c_dim" "$1" "$c_reset"; }
cmd(){   printf '   %s$ %s%s\n' "$c_dim" "$1" "$c_reset"; }
ok(){    printf '   %s✓%s %s\n' "$c_grn" "$c_reset" "$1"; PASS=$((PASS+1)); }
bad(){   printf '   %s✗%s %s\n' "$c_red" "$c_reset" "$1"; FAIL=$((FAIL+1)); }

R(){ printf '%s' "${ROOT%/}$1"; }       # resolve a path under ROOT

printf '%sL400 "Mission Creep" - intended solve%s   (ROOT=%s)\n' "$c_bold" "$c_reset" "$ROOT"
printf 'FLAG = %s\n' "$FLAG"

# ---------------------------------------------------------------------------
stage "S0 ORIENTATION - build a timeline, find the intrusion window"
note "Mount read-only, then: log2timeline/plaso, or fls + mactime."
cmd  "fls -r -m / image.raw > body ; mactime -b body -d > timeline.csv"
note "One burst lights up: 2026-04-14 02:15-02:38 UTC = the intrusion."
note "An earlier burst 2026-04-09 = opportunistic scan/brute = NOISE."
acc="$(R /var/log/nginx/access.log)"
if [ -f "$acc" ]; then ok "access.log present (timeline anchor)"; else bad "access.log missing at $acc"; fi

# ---------------------------------------------------------------------------
stage "S1 INITIAL ACCESS - the one successful upload in the noise"
cmd 'grep -E "\"(POST|GET) /upload|/uploads/" access.log | grep " 200 "'
up="$(grep -E '"POST /upload\.php' "$acc" 2>/dev/null | grep ' 200 ')"
if [ -n "$up" ]; then ok "found the successful upload:"; printf '       %s\n' "$up"
else bad "no successful POST /upload.php found"; fi
sh="$(R /var/www/html/uploads/sess_4f1c.php)"
if [ -f "$sh" ]; then ok "webshell on disk: /var/www/html/uploads/sess_4f1c.php"; else bad "webshell missing"; fi
note "webshell ?c= commands wget a 2nd stage into /dev/shm/.k (tmpfs -> gone"
note "after power-off; the LOG is the surviving evidence). PIVOT -> persistence."

# ---------------------------------------------------------------------------
stage "S2 PERSISTENCE - malicious timer hidden among legit ones"
cmd 'ls -la /etc/systemd/system/ ; cat /usr/local/sbin/.sysupd'
ct="$(R /etc/systemd/system/cleanup.timer)"
nb="$(R /etc/systemd/system/nodebackup.timer)"
sysupd="$(R /usr/local/sbin/.sysupd)"
[ -f "$ct" ] && ok "cleanup.timer present (the malicious one)" || bad "cleanup.timer missing"
[ -f "$nb" ] && ok "nodebackup.timer present (legit cover - must distinguish)" || bad "nodebackup.timer missing"
if [ -f "$sysupd" ]; then
  ok "hidden payload /usr/local/sbin/.sysupd present"
  if grep -q 'pkexec' "$sysupd"; then ok ".sysupd references pkexec  -> PIVOT to S3"; else bad ".sysupd does not point to pkexec"; fi
else bad ".sysupd missing"; fi
note "tells vs nodebackup: 15-min cadence, hidden dot-name, Apr-14 mtime."

# ---------------------------------------------------------------------------
stage "S3 PRIVESC - the trojaned pkexec"
cmd 'dpkg --verify pkexec   # or: debsums -s pkexec'
cmd 'strings /usr/bin/pkexec | grep -iE "PKEXEC_AUTH|/bin/bash"'
pk="$(R /usr/bin/pkexec)"
# detection: compare to the package md5 record (what dpkg --verify uses)
pkg="$(dpkg -S /usr/bin/pkexec 2>/dev/null | head -1 | cut -d: -f1)"
md5f="$(ls "$(R /var/lib/dpkg/info)"/${pkg}*.md5sums 2>/dev/null | head -1)"
rec="$(grep -E '(^| )usr/bin/pkexec$' "$md5f" 2>/dev/null | awk '{print $1}' | head -1)"
cur="$(md5sum "$pk" 2>/dev/null | awk '{print $1}')"
if [ -n "$rec" ] && [ "$cur" != "$rec" ]; then ok "pkexec md5 != package record (dpkg --verify shows ??5??????)"
else note "(run 'dpkg --verify $pkg' on the live box to see the ??5?????? flag)"; fi
if strings "$pk" 2>/dev/null | grep -q 'PKEXEC_AUTH'; then ok "backdoor signal visible: PKEXEC_AUTH + /bin/bash"; else bad "no PKEXEC_AUTH signal in pkexec"; fi
if strings "$pk" 2>/dev/null | grep -q "$MAGIC"; then bad "trigger is PLAINTEXT (should be XOR-hidden)"; else ok "trigger NOT plaintext (XOR(0x42) - needs light RE)"; fi
note "light RE: decode the XOR'd byte array (k[i]^0x42) or gdb the compare ->"
note "trigger = $MAGIC.  env PKEXEC_AUTH=$MAGIC ./pkexec -> root shell. PIVOT: root."

# ---------------------------------------------------------------------------
stage "S4 COVER-UP - the wipe is the evidence"
cmd 'ls -la /var/log/wtmp /var/log/lastlog ; last -f /var/log/wtmp'
wt="$(R /var/log/wtmp)"; ll="$(R /var/log/lastlog)"; rh="$(R /root/.bash_history)"; jh="$(R /home/jhayes/.bash_history)"
[ -f "$wt" ] && [ ! -s "$wt" ] && ok "wtmp is 0 bytes (wiped)" || bad "wtmp not zeroed"
[ -f "$ll" ] && [ ! -s "$ll" ] && ok "lastlog is 0 bytes (wiped)" || bad "lastlog not zeroed"
[ -f "$rh" ] && [ ! -s "$rh" ] && ok "/root/.bash_history cleared" || note "root history not empty (ok if box still live)"
[ -s "$jh" ] && ok "jhayes history INTACT (the honest contrast)" || bad "jhayes history missing"
note "0-byte wtmp on a weeks-old box w/ a full auth.log = a WIPE, not a fresh box."
note "PIVOT: the timeline surfaces the surviving /var/tmp/.x (created 02:31)."

# ---------------------------------------------------------------------------
stage "S5 EXFIL - recover the flag from the core dump"
cmd 'ls -la /var/tmp/.x/ ; strings /var/tmp/.x/core.* | grep number{'
xd="$(R /var/tmp/.x)"
if [ -d "$xd" ]; then
  ncore=$(ls "$xd"/core.* 2>/dev/null | wc -l)
  ok "/var/tmp/.x present (loot.tgz + core dump)"
  [ "$ncore" -eq 1 ] && ok "exactly one core dump (clean)" || bad "$ncore core dumps present - image should ship ONE (rm the stale one)"
  # the flag is binary-only: grep the core directly (no strings|grep -q under pipefail)
  if grep -aqF "$FLAG" "$xd"/core.* 2>/dev/null; then ok "FLAG recovered from core: $FLAG"; else bad "flag NOT in any core"; fi
  if grep -rIl 'number{' "$xd" 2>/dev/null | grep -q .; then bad "a TEXT file leaks the flag (must be binary-only)"; else ok "anti-shortcut holds: grep -rI (text) finds nothing"; fi
else bad "/var/tmp/.x missing"; fi

# ---------------------------------------------------------------------------
printf '\n%s%d passed, %d failed%s\n' "$c_bold" "$PASS" "$FAIL" "$c_reset"
if [ "$FAIL" -eq 0 ]; then printf '%s✓ chain solves end-to-end - a DFIR player can walk it.%s\n' "$c_grn" "$c_reset"; exit 0
else printf '%s✗ chain has gaps - see ✗ above.%s\n' "$c_red" "$c_reset"; exit 1; fi
