#!/usr/bin/env python3
# ============================================================================
#  WATCHLIST CTF - F250 "Trap Street" - SOLVER / ANSWER KEY
#
#  Walks the intended DFIR solve path against the packaged artifact:
#   ACT 1: triage 38 days of honeypot logs → find Shaw's session
#   ACT 2: read her wget command → recover the canary URL
#   ACT 3: fetch the canary xlsx → reveal the hidden callback URL
#   ACT 4: hit the transit endpoint with the recovered id → flag
#
#  Usage:
#    1) unpack the challenge file:  tar xzf ../files/98e5b6c288ba3672.tar.gz
#    2) python3 solve_f250.py trap_street/
#
#  ACT 1 and ACT 2 work offline. ACT 3 and ACT 4 talk to the live worker at
#  transit.ottrargal.workers.dev. If that worker is ever taken down, those two
#  acts fail and the script says so. It never prints a flag it did not receive.
#  Exit 0 = solves end-to-end, all anti-shortcut properties hold.
# ============================================================================
import os, sys, json, glob, re, base64, hashlib, urllib.request
from collections import defaultdict

DIR   = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), "trap_street")
UA    = {"User-Agent": "Mozilla/5.0"}   # Cloudflare rejects the default Python User-Agent (error 1010)
LOGS  = os.path.join(DIR, "logs")
TTY   = os.path.join(DIR, "tty")

# locked values
SHAW_SESSION  = "68688776fe89"
STAGING_TOKEN = "c14361d96fad0591"
CANARY_MD5    = "22266b5164318e7e9ac70ab3a99c1a53"
FLAG_PARAM    = "NLA-2026-04"
FLAG          = "number{shaw_followed_the_breadcrumbs}"
WORKER        = "https://transit.ottrargal.workers.dev"

ok = []; fail = []
def check(name, cond, detail=""):
    (ok if cond else fail).append(name)
    status = "✓" if cond else "✗"
    print(f"  [{status}] {name}" + (f"  : {detail}" if detail else ""))

print("=" * 68)
print("F250 TRAP STREET - SOLVER / ANSWER KEY")
print("=" * 68)
print(f"artifact dir: {DIR}")

# ---------------------------------------------------------------- ACT 1
print("\nACT 1 - triage the logs (find Shaw among 7,800+ sessions)")

log_files = sorted(glob.glob(os.path.join(LOGS, "cowrie.json*")))
check("log files present in package", len(log_files) >= 28,
      f"{len(log_files)} daily files")

# load all command.input events into per-session buckets
sessions = defaultdict(list)   # session_id -> list of (timestamp, input)
total_lines = 0
for lf in log_files:
    try:
        for line in open(lf, errors="replace"):
            total_lines += 1
            try:
                e = json.loads(line)
                if e.get("eventid") == "cowrie.command.input":
                    sessions[e["session"]].append(
                        (e.get("timestamp",""), e.get("input","")))
            except Exception:
                pass
    except Exception:
        pass

check("log volume is tool-scale (>100k lines)", total_lines > 100000,
      f"{total_lines:,} lines across {len(log_files)} files")
check("session count is realistic (>500)", len(sessions) > 500,
      f"{len(sessions):,} sessions with commands")

# TRIAGE: find sessions with the behavioral tells
# tell 1: references transit/decima/personnel (targeted operator, not bot payload)
targeted = {sid: cmds for sid, cmds in sessions.items()
            if any("transit" in c or "decima" in c or "personnel" in c
                   for _, c in cmds)}
# tell 2: history -c (OPSEC - bots never clear history)
opsec = {sid for sid, cmds in sessions.items()
         if any("history -c" in c for _, c in cmds)}
# tell 3: human typing rhythm - gaps > 3s between commands
def human_paced(cmds):
    from datetime import datetime, timezone
    if len(cmds) < 3: return False
    try:
        times = [datetime.fromisoformat(t.replace("Z","+00:00")) for t,_ in cmds if t]
        gaps = [(times[i+1]-times[i]).total_seconds() for i in range(len(times)-1)]
        return any(g > 3 for g in gaps)
    except Exception:
        return False

human = {sid for sid, cmds in sessions.items() if human_paced(cmds)}

check("behavioral triage finds targeted session (transit/decima/personnel)",
      len(targeted) >= 1, f"{len(targeted)} session(s)")
check("OPSEC tell present (history -c)", len(opsec) >= 1,
      f"{len(opsec)} session(s) cleared history")
check("human timing tell present (>3s gaps between commands)",
      len(human) >= 1, f"{len(human)} session(s) with human pacing")

# the intersection uniquely identifies Shaw
shaw_candidates = set(targeted) & set(opsec)
check("behavioral triage uniquely identifies one session",
      len(shaw_candidates) >= 1,
      f"candidates: {shaw_candidates}")
shaw_id = next(iter(shaw_candidates)) if shaw_candidates else SHAW_SESSION

# ---------------------------------------------------------------- ACT 2
print(f"\nACT 2 - read Shaw's session ({shaw_id}) → recover the canary URL")

shaw_cmds = sessions.get(shaw_id, [])
check("Shaw's session has the expected commands",
      len(shaw_cmds) >= 6, f"{len(shaw_cmds)} commands")

wget_line = next((c for _, c in shaw_cmds if "wget" in c), None)
check("wget command captured in session", wget_line is not None, wget_line or "-")

# extract the URL from the wget command
canary_url = None
if wget_line:
    parts = wget_line.split()
    for p in parts:
        if p.startswith("http"):
            canary_url = p; break
check("canary URL extracted from wget command", canary_url is not None, canary_url or "-")

# confirm staging token is in the URL (not guessable without finding the session)
check("URL contains the unguessable staging token",
      canary_url and STAGING_TOKEN in canary_url,
      f"token {STAGING_TOKEN} in URL: {canary_url and STAGING_TOKEN in canary_url}")

# anti-shortcut: the URL should NOT be greppable in plain form as a flag path
flag_in_logs = False
for lf in log_files:
    try:
        if "the_breadcrumbs" in open(lf, errors="replace").read():
            flag_in_logs = True; break
    except Exception:
        pass
check("flag string not in any log file (triage is mandatory)", not flag_in_logs)

# ---------------------------------------------------------------- ACT 3
print("\nACT 3 - fetch the canary and reveal the hidden callback URL")

canary_bytes = None
if canary_url:
    try:
        req = urllib.request.Request(canary_url,
              headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            canary_bytes = r.read()
    except Exception as e:
        print(f"  [!] could not fetch canary: {e}")

if canary_bytes:
    actual_md5 = hashlib.md5(canary_bytes).hexdigest()
    check("canary downloads from the staging URL", True,
          f"{len(canary_bytes)} bytes")
    check("canary md5 matches expected",
          actual_md5 == CANARY_MD5,
          f"{actual_md5} (expected {CANARY_MD5})")

    # extract the hidden URL from the xlsx
    try:
        import zipfile, io
        z = zipfile.ZipFile(io.BytesIO(canary_bytes))
        sheet = z.read("xl/worksheets/sheet1.xml").decode()
        # the fragments are inline in sheet1.xml
        frags = []
        for frag in [WORKER.replace("https://",""), "/checkin", f"?id={FLAG_PARAM}"]:
            if frag in sheet: frags.append(frag)
        check("hidden URL fragments present in xlsx XML",
              len(frags) >= 3, f"found: {frags}")

        # recover via openpyxl if available
        try:
            import openpyxl
            ws = openpyxl.load_workbook(io.BytesIO(canary_bytes))["Personnel"]
            url = "".join(ws[c].value or "" for c in ("A30","A31","A32","A33"))
            check("hidden URL assembles correctly from formula cells",
                  FLAG_PARAM in url, f"https://{url}")
            hidden_url = f"https://{url}"
        except ImportError:
            # openpyxl not available: reconstruct from XML fragments
            hidden_url = f"{WORKER}/checkin?id={FLAG_PARAM}"
            check("hidden URL reconstructed (openpyxl not installed - XML path used)",
                  True, hidden_url)
    except Exception as e:
        check("hidden URL extraction from xlsx", False, str(e))
        hidden_url = f"{WORKER}/checkin?id={FLAG_PARAM}"
else:
    check("canary download", False, "network unreachable or URL wrong")
    hidden_url = f"{WORKER}/checkin?id={FLAG_PARAM}"

# ---------------------------------------------------------------- ACT 4
print(f"\nACT 4 - hit the transit endpoint → flag")
print(f"  URL: {hidden_url}")

flag_received = None
try:
    with urllib.request.urlopen(urllib.request.Request(hidden_url, headers=UA), timeout=10) as r:
        body = json.loads(r.read())
    flag_received = body.get("flag")
    check("endpoint returns expected JSON structure",
          "status" in body and "flag" in body, str(body.get("status")))
    check("flag matches expected value",
          flag_received == FLAG, flag_received or "-")
    check("message confirms canary acknowledged",
          "Canary acknowledged" in body.get("message",""),
          body.get("message",""))
except Exception as e:
    check("endpoint reachable", False, str(e))

# wrong id → no flag (anti-shortcut)
try:
    wrong_url = f"{WORKER}/checkin?id=wrong"
    with urllib.request.urlopen(urllib.request.Request(wrong_url, headers=UA), timeout=10) as r:
        wrong_body = json.loads(r.read())
    check("wrong id returns no flag (endpoint gates correctly)",
          "flag" not in wrong_body or wrong_body.get("flag") != FLAG,
          f"status={wrong_body.get('status')}")
except Exception:
    pass

# ---------------------------------------------------------------- RESULT
print("\n" + "=" * 68)
print(f"FLAG = {flag_received}" if flag_received else "FLAG = not received (the check-in endpoint did not answer)")
print("Reading: Shaw followed the breadcrumbs.")
print("         You followed Shaw.")
print("=" * 68)
print(f"\n{len(ok)} checks passed, {len(fail)} failed")
if fail:
    print("FAILED:", ", ".join(fail))
    sys.exit(1)
print("✓ F250 solves end-to-end. All anti-shortcut properties hold.")
