#!/usr/bin/env bash
# =============================================================================
#  l100_check.sh - solver checker for L100 "Reduced Footprint"
#
#  Runs the exact player solve sequence over SSH and confirms every output
#  matches (19 checks). No installs, no admin, no port changes.
#  You type the SSH password ONCE when prompted (no sshpass needed).
#
#      bash l100_check.sh <host> [port=2222] [user=investigator]
#
#  The event node (node0447) was taken offline after the CTF. To use this
#  script, stand the node up again from the build script and point it there.
# =============================================================================
HOST="${1:?usage: bash l100_check.sh <host> [port=2222] [user=investigator]}"
PORT="${2:-2222}"
USER_L="${3:-investigator}"

FLAG='number{the_footprint_was_never_reduced}'
BANNER='AUTHORIZED PERSONNEL ONLY :: NODE 0447 :: ACTIVITY IS LOGGED'

if [ -t 1 ]; then G=$'\e[32m'; RED=$'\e[31m'; B=$'\e[1m'; D=$'\e[2m'; R=$'\e[0m'; else G= RED= B= D= R=; fi
pass=0; fail=0
chk(){ local l="$1"; shift; if "$@"; then printf '  %s✓%s %s\n' "$G" "$R" "$l"; pass=$((pass+1));
       else printf '  %s✗%s %s\n' "$RED" "$R" "$l"; fail=$((fail+1)); fi; }
has(){ grep -qF -- "$2" <<<"$1"; }
hasnt(){ ! grep -qF -- "$2" <<<"$1"; }

# ---- the player solve sequence (exactly the commands from the walkthrough) ----
read -r -d '' SEQ <<'CMDS'
echo __HOST__;    hostname
echo __NOTES__;   cat notes.txt
echo __CRON__;    cat /etc/cron.d/certbot
echo __WELCOME__; cat /etc/profile.d/00-welcome.sh
echo __UNITS__;   ls /etc/systemd/system/
echo __SVC__;     cat /etc/systemd/system/sysupdate.service
echo __LSPLAIN__; ls /usr/local/lib/
echo __LSALL__;   ls -a /usr/local/lib/
echo __RUN__;     cat /usr/local/lib/.sysupdate/run.sh
echo __HIST__;    cat /home/relay/.bash_history
echo __CLEAN__;   cat /home/relay/cleanup.sh
echo __CONT__;    cat /etc/systemd/system/contingency.timer
echo __END__
exit
CMDS

printf '%s== L100 solver check ==%s  %s@%s:%s   (enter the SSH password when prompted)\n' "$B" "$R" "$USER_L" "$HOST" "$PORT"
RAW=$(ssh -tt -p "$PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=12 -o LogLevel=ERROR "$USER_L@$HOST" <<<"$SEQ" 2>/dev/null)
CLEAN=$(printf '%s' "$RAW" | sed 's/\r//g; s/\x1b\[[0-9;?]*[a-zA-Z]//g')

if ! has "$CLEAN" "__END__"; then
  printf '  %s✗ SSH session did not complete (wrong password / port closed / unreachable)%s\n' "$RED" "$R"; exit 2
fi
sect(){ awk -v m="__$1__" '$0 ~ m {f=1;next} /__[A-Z]+__/{f=0} f' <<<"$CLEAN"; }
HOSTN=$(sect HOST); NOTES=$(sect NOTES); CRON=$(sect CRON); WELCOME=$(sect WELCOME)
UNITS=$(sect UNITS); SVC=$(sect SVC); LSPLAIN=$(sect LSPLAIN); LSALL=$(sect LSALL)
RUN=$(sect RUN); HIST=$(sect HIST); CLEANUP=$(sect CLEAN); CONT=$(sect CONT)

b64(){ grep -oE '[A-Za-z0-9+/]{40,}={0,2}' <<<"$1" | head -1; }
DECRUN=$(base64 -d 2>/dev/null <<<"$(b64 "$RUN")")
DECWEL=$(base64 -d 2>/dev/null <<<"$(b64 "$WELCOME")")

echo "${D}-- login + identity --${R}"
chk "login + hostname node0447"                 has "$HOSTN" "node0447"
chk "MOTD set dressing"                          has "$CLEAN" "have a pleasant shift"
chk "notes.txt readable from home + re-read beat" has "$NOTES" "not the only"
echo "${D}-- decoys (both legit) --${R}"
chk "certbot cron decoy present"                 has "$CRON" "certbot -q renew"
chk "welcome blob decodes to banner"             test "$DECWEL" = "$BANNER"
chk "welcome banner is NOT flag-shaped"          hasnt "$DECWEL" "number{"
echo "${D}-- implant signpost --${R}"
chk "sysupdate.service listed"                   has "$UNITS" "sysupdate.service"
chk "contingency.timer listed"                   has "$UNITS" "contingency.timer"
chk "ExecStart -> hidden run.sh"                 has "$SVC" "/usr/local/lib/.sysupdate/run.sh"
echo "${D}-- the ls -a gate --${R}"
chk "plain ls HIDES .sysupdate"                  hasnt "$LSPLAIN" ".sysupdate"
chk "ls -a REVEALS .sysupdate"                   has "$LSALL" ".sysupdate"
echo "${D}-- implant + flag --${R}"
chk "run.sh carries 'signed: bad code'"          has "$RUN" "signed: bad code"
chk "implant decodes to the flag"               test "$DECRUN" = "$FLAG"
echo "${D}-- flavor + guardrails --${R}"
chk "operator history ends on 'history -c'"      has "$HIST" "history -c"
chk "cleanup.sh carries 'signed: bad code'"      has "$CLEANUP" "signed: bad code"
chk "contingency seeds B350 endpoint"            has "$CONT" "contingency.decima.cloud"
chk "no plaintext flag on-box (encoded only)"    hasnt "$CLEAN" "$FLAG"
chk "history does NOT name .sysupdate"           hasnt "$HIST" ".sysupdate"
chk "cleanup.sh does NOT name .sysupdate"        hasnt "$CLEANUP" ".sysupdate"

echo
if [ "$fail" -eq 0 ]; then printf '%s%s  ALL %d CHECKS PASSED.%s\n' "$G" "$B" "$pass" "$R"; exit 0
else printf '%s%s  %d passed, %d FAILED.%s\n' "$RED" "$B" "$pass" "$fail" "$R"; exit 1; fi
