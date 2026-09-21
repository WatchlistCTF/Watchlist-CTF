#!/usr/bin/env bash
# ============================================================================
# F300 "Tmpfs" - stage the operative scenario, then leave it running for capture
#
# Run as root on the SETTLED asset VM (fresh boot, lightly loaded):
#     sudo bash stage_operative.sh
# Then take the LiME capture (see capture_runbook.md) while this is live.
#
# Produces in memory:
#   - python3 /tmp/.cache/vault.py --keytail <tail>   (the REAL target)
#       * VAULT_KEY_HEAD=<head> in its environment   (linux.envars)
#       * --keytail <tail> on its command line        (linux.psaux)
#       * holds the encrypted vault open-but-deleted  (linux.lsof / pagecache)
#       * encrypted blob resident in its heap          (linux.proc.Maps --dump)
#   - 3 red herrings: tcpdump, gpg-agent, nc           (triage noise)
#   - a reaction bash whose in-memory history shows the panic deletion (linux.bash)
# ============================================================================
set -u

KEY_HEAD="8b3f7e2a1c4d6f9b"     # -> environment
KEY_TAIL="0e8a7c5d2f1b3e6a"     # -> command line
CACHE=/tmp/.cache
# encrypted vault (VLT1 magic + AES-128-CBC ciphertext), base64:
VAULT_ENC_B64="VkxUMeZoD+qNYOhzGsb9qRLLvgY7cpsJH+9DxAn03g8JUs/4zveqobhruztkcmu1pJrl6JxxasuERAfZV7KWFwNvh43uqDeFvZXGLmrMv85huZ0hOXooFDMtcATo5gL1qYa5+bp9V8sjmBNx2EzjDjZIauJMY+NjbRrKMgMQ0kiBcQQdGpoDf6NnSanrx8vzmMSzP1pSaNC/JO/5x+jHW8bJA5Cs6EO/EJUyilMsJ9mKGh5u/o26vN9FguQxAbaypgtkRmXtvTcnCZftZcbx1VRGr+qks2zVWbtZumPoHBy0tSMf5SADpmPoolG0NItILoGFGPRwuLLxDZYrukPTgA2qZoDDhzRD2w8zaJqzfl0akUO6Lg91DVQh53yht97+5wY2ZA=="

say(){ printf '  %-34s %s\n' "$1" "$2"; }
echo "==== F300 stage_operative ===="

# 0. clean any previous run
pkill -f 'vault.py --keytail'  2>/dev/null
pkill -f 'session.pcap'        2>/dev/null
pkill -x  gpg-agent            2>/dev/null
pkill -f 'nc -lvnp 4444'       2>/dev/null
pkill -f '/tmp/.rsh'           2>/dev/null
rm -rf "$CACHE" /tmp/.rsh /tmp/.rsh.out 2>/dev/null
mkdir -p "$CACHE"

# 1. ensure the decoy tools exist
export DEBIAN_FRONTEND=noninteractive
for pb in "tcpdump:tcpdump" "netcat-openbsd:nc" "gnupg:gpg-agent"; do
  b=${pb##*:}; p=${pb%%:*}
  command -v "$b" >/dev/null 2>&1 || apt-get install -y -qq "$p" >/dev/null 2>&1
done

# 2. write the scene
cat > "$CACHE/vault.py" <<'PYEOF'
#!/usr/bin/env python3
# Decima operative vault loader.
# Full key is SPLIT: head -> environment (VAULT_KEY_HEAD), tail -> argv (--keytail).
import os, time, argparse
ap = argparse.ArgumentParser(add_help=False)
ap.add_argument("--keytail", default="")
args, _ = ap.parse_known_args()
loc = os.environ.get("VAULT_LOC", "/tmp/.cache/.vault.enc")
key_head = os.environ.get("VAULT_KEY_HEAD", "")
key_tail = args.keytail
_fd = open(loc, "rb")
_blob = _fd.read()           # encrypted bytes resident in anonymous memory
while True:
    time.sleep(3600)
PYEOF
echo "$VAULT_ENC_B64" | base64 -d > "$CACHE/.vault.enc"
cat > "$CACHE/notes.txt" <<'EOF'
loader keeps the cipher resident; nothing touches disk.
two halves, two places: head you export, tail you pass.
the phrase is the key to the relay.
EOF
say "scene" "$CACHE (vault.py, .vault.enc, notes.txt)"

# 3. launch the REAL vault loader (reads the blob into memory, holds the fd)
VAULT_KEY_HEAD="$KEY_HEAD" VAULT_LOC="$CACHE/.vault.enc" \
  setsid python3 "$CACHE/vault.py" --keytail "$KEY_TAIL" >/dev/null 2>&1 &
sleep 1
VAULT_PID=$(pgrep -f 'vault.py --keytail' | head -1)
say "vault loader" "pid ${VAULT_PID:-?} (head=env, tail=argv)"

# 4. red herrings (triage noise)
setsid tcpdump -i any -nn -U -w "$CACHE/session.pcap" >/dev/null 2>&1 &
setsid gpg-agent --daemon --default-cache-ttl 99999   >/dev/null 2>&1 &
setsid sh -c 'nc -lvnp 4444'                          >/dev/null 2>&1 &
sleep 0.5
say "red herrings" "tcpdump / gpg-agent / nc:4444"

# 5. reaction shell whose in-memory history shows the panic deletion
mkfifo /tmp/.rsh
setsid sleep infinity > /tmp/.rsh 2>/dev/null &        # keeps a writer so bash never EOFs
setsid bash --norc -i < /tmp/.rsh > /tmp/.rsh.out 2>&1 &
sleep 0.5
exec 7>/tmp/.rsh
send(){ printf '%s\n' "$1" >&7; sleep 0.3; }
send 'whoami'
send 'cd /tmp/.cache'
send 'ls -la'
send 'file .vault.enc'
send 'cat notes.txt'
send 'ps aux | grep -i vault'
send '# theyre at the door - burn the cache'
send 'rm -f .vault.enc vault.py notes.txt'
send 'rm -f ~/.bash_history /root/.bash_history'
sleep 0.5
exec 7>&-                                              # close our writer; sleep-infinity keeps bash alive
say "reaction shell" "history staged; vault files removed (held open)"

# 6. confirm the deleted-but-open state
sleep 0.5
if [ -n "${VAULT_PID:-}" ] && ls -l /proc/"$VAULT_PID"/fd 2>/dev/null | grep -q 'vault.enc (deleted)'; then
  say "state" "OK .vault.enc deleted-but-open in pid $VAULT_PID"
else
  say "state" "WARN deleted-but-open not confirmed"
fi
echo
echo "Scenario is LIVE. Capture now on this settled system, then verify it parses:"
echo "  sudo rmmod lime 2>/dev/null"
echo "  sudo insmod ~/junk/LiME/src/lime-\$(uname -r).ko \"path=$HOME/f300-work/reyes.lime format=lime\""
echo "  vol -f $HOME/f300-work/reyes.lime linux.pslist | grep -Ei 'python3|tcpdump|gpg-agent|nc'"
echo "(see capture_runbook.md for the full verify + package steps)"
