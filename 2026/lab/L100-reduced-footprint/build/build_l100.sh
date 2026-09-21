#!/usr/bin/env bash
# =============================================================================
#  L100 - "Reduced Footprint"  ::  one-shot build_l100.sh
#  Installs Cowrie (git model) on a fresh Ubuntu 24.04 droplet and injects the
#  Node 0447 challenge filesystem. Player-facing on port 22 (admin SSH moved to
#  2200). Fixed login: investigator / node0447.
#
#  Run as root on a CLEAN Ubuntu 24.04 server:
#       sudo bash build_l100.sh
#
#  Idempotent-ish (re-running rebuilds config + fs; safe). Verbose, pretty.
#  Env overrides:
#  Cowrie installs + runs on 2222 throughout. The LAST step PROMPTS whether to
#  migrate (admin SSH -> 60022, port 22 -> the honeypot). Answer n/no to skip
#  and leave everything on 2222.
#  Env overrides:
#       L100_MIGRATE=yes   auto-answer the migration prompt (automation)
#       L100_MIGRATE=no    skip migration without prompting
# =============================================================================
set -Eeuo pipefail

# ---------- pretty UI ----------
if [ -t 1 ]; then
  B=$'\e[1m'; D=$'\e[2m'; R=$'\e[0m'; G=$'\e[32m'; RED=$'\e[31m'; Y=$'\e[33m'; BL=$'\e[36m'
else B=""; D=""; R=""; G=""; RED=""; Y=""; BL=""; fi
TOTAL=8
phase(){ printf '\n%s%s━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%s\n' "$BL" "$B" "$R"
         printf '%s%s  PHASE %s/%s  ·  %s%s\n'  "$BL" "$B" "$1" "$TOTAL" "$2" "$R"
         printf '%s%s━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%s\n' "$BL" "$B" "$R"; }
step(){ printf '  %s→%s %-52s' "$D" "$R" "$1"; }
ok(){   printf '%s✓%s\n' "$G" "$R"; }
okv(){  printf '%s✓%s %s\n' "$G" "$R" "$1"; }
warn(){ printf '  %s⚠ %s%s\n' "$Y" "$1" "$R"; }
info(){ printf '  %s· %s%s\n' "$D" "$1" "$R"; }
die(){  printf '\n%s✗ FAILED: %s%s\n' "$RED" "$1" "$R" >&2; exit 1; }
trap 'die "line $LINENO (exit $?). nothing started past this point."' ERR

# ---------- constants ----------
CUSER=cowrie
CHOME=/home/$CUSER
CDIR=$CHOME/cowrie
VENV=$CDIR/cowrie-env
PICKLE=$CDIR/var/lib/cowrie/fs.pickle
HONEY=$CDIR/honeyfs
COWRIE_REPO=https://github.com/cowrie/cowrie.git
HOSTNAME_FAKE=node0447
LOGIN_USER=investigator
LOGIN_PASS=node0447
COWRIE_PORT=2222
ADMIN_PORT=60022
MIGRATED=0
FLAG="number{the_footprint_was_never_reduced}"

[ "$(id -u)" = 0 ] || die "run as root (sudo bash build_l100.sh)"

# =============================================================================
phase 1 "Preflight"
# =============================================================================
step "OS is Ubuntu 24.04"
if grep -q 'VERSION_ID="24.04"' /etc/os-release 2>/dev/null; then ok
else printf '%s⚠ not 24.04 - continuing anyway%s\n' "$Y" "$R"; fi
step "free the apt lock (stop unattended-upgrades)"
systemctl stop unattended-upgrades apt-daily.timer apt-daily-upgrade.timer 2>/dev/null || true
pkill -9 -f unattended-upgrade 2>/dev/null || true
ok
info "fake hostname=$HOSTNAME_FAKE · login=$LOGIN_USER/$LOGIN_PASS · cowrie port=$COWRIE_PORT"

# =============================================================================
phase 2 "System packages"
# =============================================================================
export DEBIAN_FRONTEND=noninteractive
step "apt-get update"; apt-get update -qq >/dev/null && ok
step "install build + python + net deps"
apt-get install -y -qq --no-install-recommends \
    git python3-venv python3-dev python3-pip \
    libssl-dev libffi-dev build-essential \
    iptables curl ca-certificates sshpass >/dev/null && ok

# =============================================================================
phase 3 "Cowrie user + source (git clone)"
# =============================================================================
step "create '$CUSER' service user"
id -u "$CUSER" >/dev/null 2>&1 || adduser --disabled-password --gecos "" "$CUSER" >/dev/null
ok
step "clone Cowrie (or update)"
if [ -d "$CDIR/.git" ]; then
  runuser -u "$CUSER" -- git -C "$CDIR" pull -q || true
else
  runuser -u "$CUSER" -- git clone -q "$COWRIE_REPO" "$CDIR"
fi
ok
step "create venv + install (this pulls Twisted etc; 1-3 min)"
runuser -u "$CUSER" -- bash -lc "
  set -e
  cd '$CDIR'
  [ -d '$VENV' ] || python3 -m venv cowrie-env
  . cowrie-env/bin/activate
  pip install -q --upgrade pip wheel >/dev/null
  pip install -q -e . >/dev/null
"
ok
runuser -u "$CUSER" -- bash -lc ". '$VENV/bin/activate'; python -c 'import cowrie' " \
  && okv "cowrie imports cleanly" || die "cowrie failed to import after install"

# =============================================================================
phase 4 "Cowrie config (node0447 + investigator + logging)"
# =============================================================================
step "mkdir state dirs"
runuser -u "$CUSER" -- mkdir -p "$CDIR/var/lib/cowrie" "$CDIR/var/log/cowrie" "$HONEY"
ok
step "write etc/cowrie.cfg"
cat > "$CDIR/etc/cowrie.cfg" <<CFG
[honeypot]
hostname = $HOSTNAME_FAKE
contents_path = $HONEY
auth_class = UserDB

[shell]
filesystem = $PICKLE

[ssh]
listen_endpoints = tcp:$COWRIE_PORT:interface=0.0.0.0

[telnet]
enabled = false

[output_jsonlog]
enabled = true
logfile = \${honeypot:log_path}/cowrie.json
CFG
ok
step "write etc/userdb.txt (only $LOGIN_USER/$LOGIN_PASS works)"
printf '%s:x:%s\n' "$LOGIN_USER" "$LOGIN_PASS" > "$CDIR/etc/userdb.txt"
ok

# =============================================================================
phase 5 "Inject the Node 0447 filesystem"
# =============================================================================
step "seed custom fs.pickle from the bundled tree"
runuser -u "$CUSER" -- cp "$CDIR/src/cowrie/data/fs.pickle" "$PICKLE"
ok
step "write the fs-injection engine"
cat > "$CDIR/l100_fs.py" <<'L100FS'
#!/usr/bin/env python3
import os, sys, time, pickle, shutil
from datetime import datetime, timezone
A_NAME,A_TYPE,A_UID,A_GID,A_SIZE,A_MODE,A_CTIME,A_CONTENTS,A_TARGET,A_REALFILE=range(10)
T_LINK,T_DIR,T_FILE,T_BLK,T_CHR,T_SOCK,T_FIFO=range(7)
DIR_MODE,FILE_MODE,EXEC_MODE=0o40755,0o100644,0o100755
COWRIE=os.path.abspath(os.path.expanduser(sys.argv[1] if len(sys.argv)>1 else "~/cowrie"))
HONEYFS=os.environ.get("COWRIE_HONEYFS",os.path.join(COWRIE,"honeyfs"))
PICKLE =os.environ.get("COWRIE_PICKLE", os.path.join(COWRIE,"var","lib","cowrie","fs.pickle"))
def die(m): print("ERROR:",m); sys.exit(1)
if not os.path.isfile(PICKLE): die(f"fs.pickle not found at {PICKLE}")
os.makedirs(HONEYFS,exist_ok=True)
def ep(s): return int(datetime.strptime(s,"%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp())
FLAG_B64=b"bnVtYmVye3RoZV9mb290cHJpbnRfd2FzX25ldmVyX3JlZHVjZWR9"
BANNER_B64=b"QVVUSE9SSVpFRCBQRVJTT05ORUwgT05MWSA6OiBOT0RFIDA0NDcgOjogQUNUSVZJVFkgSVMgTE9HR0VE"
notes=b"""NODE 0447 - investigator notes
------------------------------------------------------------
They called this box decommissioned. It is not.

Something here wakes on a schedule, does its work, and sleeps
again. The author was careful: they cleared the history and
kept the footprint small.

Small is not the same as gone.

Three things on this machine look like they belong. Two of
them do. The third is keeping someone resident - open it,
read what it carries.

The author cleared the history. The history is not the only
thing that remembers.
"""
certbot=b"""# /etc/cron.d/certbot: crontab entries for the certbot package
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

0 */12 * * * root test -x /usr/bin/certbot -a \\! -d /run/systemd/system && perl -e 'sleep int(rand(43200))' && certbot -q renew
"""
welcome=b"#!/bin/sh\n# node0447 login banner\necho '"+BANNER_B64+b"' | base64 -d\n"
svc=b"""[Unit]
Description=System Update Helper
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/lib/.sysupdate/run.sh

[Install]
WantedBy=multi-user.target
"""
tmr=b"""[Unit]
Description=Run System Update Helper periodically

[Timer]
OnBootSec=5min
OnUnitActiveSec=6h
Persistent=true

[Install]
WantedBy=timers.target
"""
contingency=b"""[Unit]
Description=Decima contingency failover (dormant)
# waits for a handler that stopped answering. it still checks,
# every night, in case someone comes back. no one does.
# endpoint: https://contingency.decima.cloud/  (unreachable since reclassification)

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=false

[Install]
WantedBy=timers.target
"""
run_sh=b"""#!/bin/sh
# sysupdate helper - keep the node reachable for maintenance
# signed: bad code
#
# maintenance token (base64):
echo '"""+FLAG_B64+b"""' | base64 -d
"""
bash_history=b"""systemctl status sysupdate.service
systemctl status sysupdate.timer
systemctl disable contingency.timer
rm -f /var/log/decima-sync.log
df -h
# strip the helper dir before handoff - TODO
history -c
"""
cleanup=b"""#!/bin/sh
# decommission node0447 - strip staging + the helper before reclaim
# signed: bad code
rm -rf /opt/decima/staging
systemctl disable sysupdate.timer
# remove the helper dir too - TODO finish before handoff
#
"""
authlog=b"""Apr 21 23:51:02 node0447 sshd[2231]: Accepted publickey for relay from 10.0.0.6 port 51344 ssh2
Apr 21 23:58:40 node0447 sshd[2231]: Received disconnect from 10.0.0.6 port 51344:11: disconnected by user
Apr 22 00:03:11 node0447 sshd[2240]: Accepted publickey for relay from 10.0.0.6 port 51702 ssh2
Apr 22 00:19:55 node0447 sshd[2240]: Received disconnect from 10.0.0.6 port 51702:11: disconnected by user
-- no further entries --
"""
motd=b"""  ____________________________________________________________
   NODE 0447   ::   "all quiet"
   status: decommissioned - scheduled for reclaim
   nothing to see here. have a pleasant shift.
  ____________________________________________________________
   Unauthorized access is prohibited. Activity is logged.
"""
T="2026-04-22 00:19"
FILES={
 "/home/investigator/notes.txt":(notes,FILE_MODE,T),
 "/etc/cron.d/certbot":(certbot,FILE_MODE,"2026-03-01 09:00"),
 "/etc/profile.d/00-welcome.sh":(welcome,EXEC_MODE,"2026-03-01 09:00"),
 "/etc/systemd/system/sysupdate.service":(svc,FILE_MODE,T),
 "/etc/systemd/system/sysupdate.timer":(tmr,FILE_MODE,T),
 "/etc/systemd/system/contingency.timer":(contingency,FILE_MODE,"2026-04-15 03:00"),
 "/usr/local/lib/.sysupdate/run.sh":(run_sh,EXEC_MODE,T),
 "/home/relay/.bash_history":(bash_history,FILE_MODE,T),
 "/home/relay/cleanup.sh":(cleanup,EXEC_MODE,T),
 "/var/log/auth.log":(authlog,FILE_MODE,T),
 "/etc/motd":(motd,FILE_MODE,"2026-03-01 09:00"),
}
DIRS=["/home/investigator","/home/relay","/etc/systemd/system","/usr/local/lib/.sysupdate"]
def child(node,name):
    for c in node[A_CONTENTS]:
        if c[A_NAME]==name: return c
    return None
def ensure_dir(root,path,mtime="2026-03-01 09:00"):
    node=root
    for part in [p for p in path.split("/") if p]:
        nx=child(node,part)
        if nx is None:
            nx=[part,T_DIR,0,0,4096,DIR_MODE,ep(mtime),[],None,None]
            node[A_CONTENTS].append(nx)
        node=nx
    return node
def add_file(root,vpath,size,mode,mtime):
    d=os.path.dirname(vpath); name=os.path.basename(vpath)
    dn=ensure_dir(root,d)
    dn[A_CONTENTS]=[c for c in dn[A_CONTENTS] if c[A_NAME]!=name]
    dn[A_CONTENTS].append([name,T_FILE,0,0,size,mode,ep(mtime),[],None,None])
shutil.copy2(PICKLE,PICKLE+".bak-"+time.strftime("%Y%m%d%H%M%S"))
fs=pickle.load(open(PICKLE,"rb"))
for d in DIRS: ensure_dir(fs,d)
for vpath,(data,mode,mtime) in FILES.items():
    add_file(fs,vpath,len(data),mode,mtime)
    hp=os.path.join(HONEYFS,vpath.lstrip("/"))
    os.makedirs(os.path.dirname(hp),exist_ok=True)
    open(hp,"wb").write(data)
# ensure investigator/relay exist in the emulated passwd/group, else Cowrie
# fabricates a shadow home at login that hides notes.txt
def _find(path):
    n=fs
    for p in [x for x in path.split("/") if x]:
        n=next((c for c in n[A_CONTENTS] if c[A_NAME]==p),None)
        if n is None: return None
    return n
def _extend(path,lines):
    node=_find(path)
    if node is None: return
    cur=node[A_CONTENTS] if isinstance(node[A_CONTENTS],bytes) else b""
    add=b"".join(l+b"\n" for l in lines if l.split(b":")[0]+b":" not in cur)
    if add: node[A_CONTENTS]=cur.rstrip(b"\n")+b"\n"+add
_extend("/etc/passwd",[b"investigator:x:1001:1001:Investigator:/home/investigator:/bin/bash",
                       b"relay:x:1002:1002:Relay Operator:/home/relay:/bin/bash"])
_extend("/etc/group",[b"investigator:x:1001:", b"relay:x:1002:"])
pickle.dump(fs,open(PICKLE,"wb"))
print(f"injected {len(FILES)} files / {len(DIRS)} dirs")
L100FS
ok
step "run the injection"
runuser -u "$CUSER" -- env COWRIE_PICKLE="$PICKLE" COWRIE_HONEYFS="$HONEY" \
  python3 "$CDIR/l100_fs.py" "$CDIR" >/dev/null && ok

step "verify injection (fs integrity + crypto + no leak)"
runuser -u "$CUSER" -- env COWRIE_PICKLE="$PICKLE" COWRIE_HONEYFS="$HONEY" python3 - <<'VERIFY'
import os,pickle,base64
P=os.environ["COWRIE_PICKLE"]; H=os.environ["COWRIE_HONEYFS"]
A_NAME,A_TYPE,A_CONTENTS,A_MODE=0,1,7,5
fs=pickle.load(open(P,"rb"))
def node(path):
    n=fs
    for p in [x for x in path.split("/") if x]:
        m=next((c for c in n[A_CONTENTS] if c[A_NAME]==p),None)
        if m is None: return None
        n=m
    return n
assert node("/usr/local/lib/.sysupdate/run.sh") and node("/usr/local/lib/.sysupdate")[A_TYPE]==1
assert node("/usr/local/lib/.sysupdate/run.sh")[A_MODE]==0o100755
flag=base64.b64decode(open(H+"/usr/local/lib/.sysupdate/run.sh","rb").read().split(b"'")[1]).decode()
assert flag=="number{the_footprint_was_never_reduced}", flag
leak=[f for r,_,fs2 in os.walk(H) for f in fs2 if b"number{" in open(os.path.join(r,f),"rb").read()]
assert not leak, f"LEAK {leak}"
hist=open(H+"/home/relay/.bash_history","rb").read(); cl=open(H+"/home/relay/cleanup.sh","rb").read()
assert b".sysupdate" not in hist and b".sysupdate" not in cl, "names .sysupdate"
assert b"# signed: bad code" in cl and b"# signed: bad code" in open(H+"/usr/local/lib/.sysupdate/run.sh","rb").read()
pw=node("/etc/passwd")[A_CONTENTS]
assert isinstance(pw,bytes) and b"investigator:" in pw and b"/home/investigator" in pw, "investigator missing from /etc/passwd (shadow-home bug)"
print("OK")
VERIFY
ok

step "fix ownership"
chown -R "$CUSER:$CUSER" "$CDIR"
ok

# =============================================================================
phase 6 "systemd service + start Cowrie"
# =============================================================================
step "write cowrie.service"
cat > /etc/systemd/system/cowrie.service <<UNIT
[Unit]
Description=Cowrie SSH Honeypot (L100 node0447)
After=network.target

[Service]
Type=forking
User=$CUSER
Group=$CUSER
WorkingDirectory=$CDIR
Environment=PATH=$VENV/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$VENV/bin/cowrie start
ExecStop=$VENV/bin/cowrie stop
PIDFile=$CDIR/var/run/cowrie.pid
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
ok
step "enable + start"
systemctl daemon-reload
systemctl enable cowrie >/dev/null 2>&1 || true
systemctl restart cowrie
sleep 4
ok
step "cowrie accepting connections on $COWRIE_PORT"
port_up(){ timeout 3 bash -c "exec 3<>/dev/tcp/127.0.0.1/$1" 2>/dev/null; }
for _ in 1 2 3 4 5 6; do port_up "$COWRIE_PORT" && break; sleep 2; done
port_up "$COWRIE_PORT" && ok || die "cowrie not accepting on $COWRIE_PORT (journalctl -u cowrie -n50 ; sudo -u $CUSER $VENV/bin/cowrie status)"

# =============================================================================
phase 7 "Optional: migrate admin SSH -> $ADMIN_PORT, hand 22 to the honeypot"
# =============================================================================
IP=$(hostname -I | awk '{print $1}')
printf '  Cowrie is verified and serving on %s%s%s. Admin SSH is still on 22.\n' "$B" "$COWRIE_PORT" "$R"
printf '  Migrating will move %sadmin SSH to %s%s and redirect port 22 -> the honeypot,\n' "$B" "$ADMIN_PORT" "$R"
printf '  so players can connect on the normal port 22.\n'
ANS="${L100_MIGRATE:-}"
if [ -z "$ANS" ]; then
  printf '\n  %sMigrate now?%s [y/N] (n = leave everything on %s, migrate later): ' "$B" "$R" "$COWRIE_PORT"
  read -r ANS </dev/tty || ANS="n"
fi
case "$ANS" in
 y|Y|yes|YES)
  # --- detect how sshd listens (24.04 minimal uses ssh.socket activation) ---
  if systemctl is-active --quiet ssh.socket; then SSHMODE=socket; else SSHMODE=service; fi
  info "sshd mode: $SSHMODE"

  step "add admin SSH on $ADMIN_PORT (keeps 22 until you confirm)"
  if [ "$SSHMODE" = socket ]; then
    mkdir -p /etc/systemd/system/ssh.socket.d
    # appending ListenStream adds 60022 while KEEPING the inherited :22
    cat > /etc/systemd/system/ssh.socket.d/10-l100.conf <<SOCK
[Socket]
ListenStream=$ADMIN_PORT
SOCK
    systemctl daemon-reload
    systemctl restart ssh.socket
  else
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.l100.bak
    grep -qE "^Port 22\b"          /etc/ssh/sshd_config || echo "Port 22"          >> /etc/ssh/sshd_config
    grep -qE "^Port $ADMIN_PORT\b" /etc/ssh/sshd_config || echo "Port $ADMIN_PORT" >> /etc/ssh/sshd_config
    systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null || true
  fi
  sleep 2
  port_up(){ timeout 3 bash -c "exec 3<>/dev/tcp/127.0.0.1/$1" 2>/dev/null; }
  port_up "$ADMIN_PORT" && ok || die "admin SSH not accepting on $ADMIN_PORT - aborting BEFORE redirect (no lockout). Old session still on 22."

  # --- checkpoint 1: make the operator prove the new door works ---
  if [ "${L100_MIGRATE:-}" = yes ]; then conf=YES; else
    printf '\n%s%s  CHECKPOINT - do NOT skip%s\n' "$Y" "$B" "$R"
    printf '  In a SEPARATE terminal, confirm the new admin port works:\n'
    printf '      %sssh -p %s <you>@%s%s\n' "$B" "$ADMIN_PORT" "$IP" "$R"
    printf '  Keep THIS session open. Only after that login succeeds,\n'
    printf '  type %sYES%s to redirect port 22 to the honeypot (anything else = abort): ' "$B" "$R"
    read -r conf </dev/tty || conf=""
  fi
  if [ "$conf" != YES ]; then
    warn "migration aborted at checkpoint. Admin still on 22 + $ADMIN_PORT; Cowrie on $COWRIE_PORT. Re-run to retry."
  else
    step "redirect 22 -> $COWRIE_PORT (iptables) + boot persistence"
    iptables -t nat -C PREROUTING -p tcp --dport 22 -j REDIRECT --to-ports "$COWRIE_PORT" 2>/dev/null \
      || iptables -t nat -A PREROUTING -p tcp --dport 22 -j REDIRECT --to-ports "$COWRIE_PORT"
    mkdir -p /opt/l100
    cat > /opt/l100/redirect.sh <<RS
#!/usr/bin/env bash
iptables -t nat -C PREROUTING -p tcp --dport 22 -j REDIRECT --to-ports $COWRIE_PORT 2>/dev/null \\
 || iptables -t nat -A PREROUTING -p tcp --dport 22 -j REDIRECT --to-ports $COWRIE_PORT
RS
    chmod +x /opt/l100/redirect.sh
    cat > /etc/systemd/system/l100-redirect.service <<RUNIT
[Unit]
Description=L100 port 22->$COWRIE_PORT redirect
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/opt/l100/redirect.sh
[Install]
WantedBy=multi-user.target
RUNIT
    systemctl daemon-reload; systemctl enable l100-redirect >/dev/null 2>&1 || true
    ok
    MIGRATED=1
    warn "ADMIN SSH IS NOW ON $ADMIN_PORT. Reconnect there from now on. Port 22 = honeypot."
  fi
  ;;
 *)
  info "skipped - Cowrie stays on $COWRIE_PORT, admin SSH stays on 22. Re-run anytime to migrate."
  ;;
esac

# =============================================================================
phase 8 "Live self-test (SSH in as the player)"
# =============================================================================
step "ssh in as the player and walk the solve"
SSH="sshpass -p $LOGIN_PASS ssh -p $COWRIE_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -o LogLevel=ERROR $LOGIN_USER@127.0.0.1"
PLAIN=$($SSH 'ls /usr/local/lib' 2>/dev/null || true)
ALL=$($SSH 'ls -a /usr/local/lib' 2>/dev/null || true)
RUN=$($SSH 'cat /usr/local/lib/.sysupdate/run.sh' 2>/dev/null || true)
# decode OFF-box in real bash (Cowrie emulates neither 'tail -1' nor '| sh')
B64=$(printf '%s' "$RUN" | grep -oE '[A-Za-z0-9+/]{40,}={0,2}' | head -1)
DEC=$(printf '%s' "$B64" | base64 -d 2>/dev/null || true)
fail=0
printf '%s' "$PLAIN" | grep -q '\.sysupdate' && { warn "plain ls exposed .sysupdate (gate broken)"; fail=1; }
printf '%s' "$ALL"   | grep -q '\.sysupdate' || { warn "ls -a did not reveal .sysupdate"; fail=1; }
[ "$DEC" = "$FLAG" ] || { warn "decoded payload != flag (got: ${DEC:-<none>})"; fail=1; }
if [ "$fail" = 0 ]; then okv "login OK · ls-a gate OK · implant decodes -> $FLAG"
else printf '%s  ⚠ self-test inconclusive - verify manually before publishing%s\n' "$Y" "$R"; fi

IP=$(hostname -I | awk '{print $1}')
cat <<DONE

${G}${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${R}
${G}${B}  L100 'Reduced Footprint' is LIVE on $IP${R}
${G}${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${R}

  Player connect (CTFd description):
$( if [ "${MIGRATED:-0}" = 1 ]; then
     printf '      ssh %s@%s            (password: %s)\n      port 22 (migrated)' "$LOGIN_USER" "$IP" "$LOGIN_PASS"
   else
     printf '      ssh %s@%s -p %s    (password: %s)\n      (not migrated - Cowrie on %s; re-run to migrate to port 22)' "$LOGIN_USER" "$IP" "$COWRIE_PORT" "$LOGIN_PASS" "$COWRIE_PORT"
   fi )

  Intended walk:
      ls -la /etc/systemd/system/        # spot sysupdate.* + contingency.timer
      cat .../sysupdate.service          # ExecStart -> /usr/local/lib/.sysupdate/run.sh
      ls -la /usr/local/lib/             # .sysupdate hidden -> needs ls -a
      cat /usr/local/lib/.sysupdate/run.sh
      echo '<b64>' | base64 -d           # -> $FLAG

  Logs / replay:
      sudo -u $CUSER tail -f $CDIR/var/log/cowrie/cowrie.json
      sudo -u $CUSER $VENV/bin/playlog $CDIR/var/lib/cowrie/tty/<id>

  Decode (off-box, on your Kali - Cowrie won't run the pipe for them):
      echo '<base64 from run.sh>' | base64 -d     # -> $FLAG

  $( [ "${MIGRATED:-0}" = 1 ] && printf '%sAdmin SSH is now on port %s - reconnect there.%s' "$Y" "$ADMIN_PORT" "$R" )
DONE
