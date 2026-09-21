#!/usr/bin/env bash
# ============================================================================
#  WATCHLIST CTF - L400 "Mission Creep" - CLEANUP / RESET
#
#  Reverts everything build_l400.sh creates, so a re-run starts from a clean
#  slate WITHOUT needing a snapshot. Run as root on the build VM:
#      sudo bash l400_cleanup.sh
#
#  A fresh-snapshot rebuild is still the gold standard for the SHIPPING image;
#  this is for fast iteration when you don't want to revert the whole VM.
#  It restores pkexec from the package, removes the attack artifacts, and
#  resets the seeded logs.  It does NOT uninstall nginx/php (harmless baseline).
# ============================================================================
set -uo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo)"; exit 1; }

c_grn=$'\033[32m'; c_reset=$'\033[0m'; c_dim=$'\033[2m'
ok(){ printf '   %s✓%s %s\n' "$c_grn" "$c_reset" "$1"; }
say(){ printf '%s» %s%s\n' "$c_dim" "$1" "$c_reset"; }

say "restoring trojaned pkexec from its package"
PKG="$(dpkg -S /usr/bin/pkexec 2>/dev/null | head -1 | cut -d: -f1)"
if [ -n "$PKG" ]; then
  DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get install --reinstall -y "$PKG" >/dev/null 2>&1 \
    && ok "pkexec restored from $PKG" || echo "   ! reinstall of $PKG failed (check network); pkexec may stay trojaned"
else
  echo "   ! could not resolve pkexec package; restore manually"
fi

say "removing persistence (cleanup unit + hidden payload)"
systemctl disable --now cleanup.timer cleanup.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/cleanup.timer /etc/systemd/system/cleanup.service /usr/local/sbin/.sysupd
systemctl daemon-reload >/dev/null 2>&1 || true
ok "cleanup.timer/.service + /usr/local/sbin/.sysupd removed"

say "removing the legit-cover timer (build_l400.sh re-creates it)"
systemctl disable --now nodebackup.timer >/dev/null 2>&1 || true
rm -f /etc/systemd/system/nodebackup.timer /etc/systemd/system/nodebackup.service /usr/local/sbin/nodebackup /var/backups/relay-conf.tgz
ok "nodebackup.* removed"

say "removing the webshell + exfil staging"
rm -f /var/www/html/uploads/sess_4f1c.php
rm -f /dev/shm/.k 2>/dev/null || true
rm -rf /var/tmp/.x
ok "webshell, /dev/shm/.k, and /var/tmp/.x (cores + loot) removed"

say "resetting the seeded logs (the build re-seeds them)"
: > /var/log/nginx/access.log 2>/dev/null || true
[ -f /var/log/nginx/error.log ] && : > /var/log/nginx/error.log || true
: > /var/log/auth.log 2>/dev/null || true
ok "access.log + auth.log truncated"

say "restoring login records so it isn't a fresh-looking box mid-iteration"
# touch (don't fabricate) - the build wipes these again anyway
[ -f /var/log/wtmp ]    || { : > /var/log/wtmp; chown root:utmp /var/log/wtmp 2>/dev/null || true; }
[ -f /var/log/lastlog ] || { : > /var/log/lastlog; chown root:utmp /var/log/lastlog 2>/dev/null || true; }
ok "wtmp/lastlog present (the build re-wipes them in S4)"

say "removing build markers / answer key / scratch"
rm -f /var/lib/.l400_built /root/L400_ANSWERKEY.txt
rm -f /root/.bash_history; : > /root/.bash_history
ok "marker + answer key removed"

say "removing the jhayes user (build_l400.sh re-creates it)"
userdel -rf jhayes 2>/dev/null || true
getent group jhayes >/dev/null 2>&1 && groupdel jhayes 2>/dev/null || true
ok "jhayes user/group cleared"

printf '\n%s✓ clean. You can now run:  sudo MODE=build bash build_l400.sh%s\n' "$c_grn" "$c_reset"
printf '%s  (note: dpkg.log/journal still carry this run; a fresh snapshot is best for the SHIPPING image.)%s\n' "$c_dim" "$c_reset"
