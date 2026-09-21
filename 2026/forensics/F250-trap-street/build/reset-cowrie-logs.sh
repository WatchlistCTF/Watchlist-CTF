#!/usr/bin/env bash
#
# reset-cowrie-logs.sh
# ---------------------------------------------------------------------------
# Wipe Cowrie's captured/test data and restart the service, while PRESERVING
# the custom Decima filesystem (fs.pickle).
#
# Clears these data sinks:
#   1. var/log/cowrie/cowrie.log*    text log  (IPs, logins, commands)
#   2. var/log/cowrie/cowrie.json*   JSON event log
#   3. var/lib/cowrie/tty/*          keystroke session recordings
#   4. var/lib/cowrie/downloads/*    files captured during sessions
#
# NEVER touches: var/lib/cowrie/fs.pickle  (your Decima filesystem)
#
# Usage:
#   sudo bash reset-cowrie-logs.sh
#   sudo COWRIE_HOME=/path/to/cowrie bash reset-cowrie-logs.sh   # override location
# ---------------------------------------------------------------------------

COWRIE_HOME="${COWRIE_HOME:-/home/cowrie/cowrie}"
LOG_DIR="$COWRIE_HOME/var/log/cowrie"
TTY_DIR="$COWRIE_HOME/var/lib/cowrie/tty"
DL_DIR="$COWRIE_HOME/var/lib/cowrie/downloads"
PICKLE="$COWRIE_HOME/var/lib/cowrie/fs.pickle"

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root:  sudo bash $0" >&2
  exit 1
fi

if [[ ! -d "$COWRIE_HOME" ]]; then
  echo "ERROR: COWRIE_HOME not found: $COWRIE_HOME" >&2
  exit 1
fi

echo "[*] Stopping cowrie service..."
systemctl stop cowrie

echo "[*] Clearing captured data (fs.pickle preserved)..."
rm -f "$LOG_DIR"/cowrie.log*  "$LOG_DIR"/cowrie.json*
rm -f "$TTY_DIR"/*
rm -f "$DL_DIR"/*

echo "[*] Clean state while STOPPED (counts should be ~0):"
printf '      logs:      %s file(s)\n' "$(ls -A "$LOG_DIR"  2>/dev/null | wc -l)"
printf '      tty:       %s file(s)\n' "$(ls -A "$TTY_DIR"  2>/dev/null | wc -l)"
printf '      downloads: %s file(s)\n' "$(ls -A "$DL_DIR"   2>/dev/null | wc -l)"

if [[ -f "$PICKLE" ]]; then
  echo "[*] fs.pickle intact ($(du -h "$PICKLE" | cut -f1)) - Decima filesystem preserved."
else
  echo "[!] WARNING: fs.pickle is MISSING. Do NOT proceed until it is restored." >&2
fi

echo "[*] Starting cowrie service..."
systemctl start cowrie
sleep 2

if systemctl is-active --quiet cowrie; then
  echo "[OK] Cowrie running. Logs will repopulate from real traffic going forward."
else
  echo "[!] Cowrie did not come back up - check: systemctl status cowrie" >&2
  exit 1
fi
