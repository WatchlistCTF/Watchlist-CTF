#!/usr/bin/env python3
# ============================================================================
#  WATCHLIST CTF - L200 "Signal" - SOLVER / ANSWER KEY
#  (A) carve base64-chunked Perl from TXT answers -> reassemble -> read C2 URL
#  (B) carve the session key from subdomain labels of the enroll cluster
#  (C) fetch the config from the C2 with ?sid=<key> -> base64-decode the flag
#  Asserts anti-shortcut properties. Exit 0 = solves + safe.
#
#  Usage:   python3 solve_l200.py [capture.pcap]
#           With no argument it reads ../files/5dde59ee766dcf93.pcap
#  Needs:   scapy  (pip install scapy)
#
#  The last step asks the live C2 worker for the config. The script takes the
#  worker's address from the capture itself, the same way a player does. If
#  the worker is ever taken down, the script says so in capital letters and
#  only shows what the worker WOULD return. Set L200_ENDPOINT to point it at
#  a worker you deployed yourself.
#
#  The two DNS names below are what a player finds by filtering the capture
#  for TXT queries and for the enrolment lookups. They are written in here so
#  the script can go straight to them.
# ============================================================================
import sys, os, re, base64, subprocess, json
try:
    from scapy.all import rdpcap, DNS, DNSRR, DNSQR
except Exception:
    print("scapy required"); sys.exit(2)

HERE=os.path.dirname(os.path.abspath(__file__))
ARG=sys.argv[1] if len(sys.argv)>1 else os.path.join(HERE,"..","files","5dde59ee766dcf93.pcap")
PCAP=os.path.join(ARG,"intercept.pcap") if os.path.isdir(ARG) else ARG
DIR=os.path.dirname(os.path.abspath(PCAP))
C2_DOMAIN="sync.relay-7f3a.rl7f3a.net"
PARAM_DOMAIN="enroll.rl7f3a.net"
ok=[];fail=[]
def check(n,c,d=""):
    (ok if c else fail).append(n); print(f"  [{'✓' if c else '✗'}] {n}"+(f"  : {d}" if d else ""))

print("="*68); print("L200 SIGNAL - SOLVER / ANSWER KEY"); print("="*68)

print("\n[load] reading the capture (this is the haystack)")
pkts=rdpcap(PCAP)
print(f"  {len(pkts)} packets in capture")

# ---------------------------------------------------------------- ACT 1: carve the implant
print("\nACT 1 - carve the base64-chunked Perl from TXT answers on the c2 domain")
txt_answers=[]
for p in pkts:
    if p.haslayer(DNS) and p[DNS].qr==1 and p[DNS].ancount>0:
        an=p[DNS].an
        for i in range(p[DNS].ancount):
            try: rr=an[i]
            except Exception: rr=an
            if getattr(rr,"type",None)==16:  # TXT
                name=rr.rrname.decode().rstrip(".") if isinstance(rr.rrname,bytes) else str(rr.rrname).rstrip(".")
                data=b"".join(rr.rdata) if isinstance(rr.rdata,list) else rr.rdata
                if isinstance(data,bytes): data=data.decode("latin1")
                if name==C2_DOMAIN: txt_answers.append(data)
check("found malicious TXT records on the c2 domain", len(txt_answers)>0, f"{len(txt_answers)} chunks")

# reassemble by sequence markers "v1;<idx>/<total>;<b64>"
seq={}
for t in txt_answers:
    m=re.match(r"v1;(\d+)/(\d+);(.*)",t)
    if m: seq[int(m.group(1))]=m.group(3)
total=max((int(re.match(r"v1;\d+/(\d+);",t).group(1)) for t in txt_answers if re.match(r"v1;\d+/(\d+);",t)),default=0)
ordered="".join(seq[k] for k in sorted(seq))
check("chunks carry sequence markers and reassemble in order", len(seq)>0 and sorted(seq)==list(range(1,len(seq)+1)), f"{len(seq)} ordered chunks")
try:
    implant=base64.b64decode(ordered).decode()
    decoded_ok=implant.startswith("#!/usr/bin/perl")
except Exception:
    implant=""; decoded_ok=False
check("reassembled payload decodes to a Perl script", decoded_ok)

# read the C2 URL + param NAME from the script (no execution)
url=re.search(r'https?://[^\s"\']+', implant)
param_name=re.search(r'\?(\w+)=|\b(\w+)\}?\s*\|\|\s*""', implant)
c2_url=url.group(0) if url else None
check("recovered the C2 URL by READING the script (no execution needed)", c2_url is not None, c2_url)
sid_param = "sid" if "sid" in implant else None
check("script reveals it needs a 'sid' parameter", sid_param=="sid")

# ---------------------------------------------------------------- ACT 2: carve the key
print("\nACT 2 - carve the session key from the enroll subdomain labels (separate channel)")
labels={}
for p in pkts:
    if p.haslayer(DNSQR):
        qn=p[DNSQR].qname.decode().rstrip(".") if isinstance(p[DNSQR].qname,bytes) else str(p[DNSQR].qname).rstrip(".")
        m=re.match(r"([^.])\.(\d{2})\.k\."+re.escape(PARAM_DOMAIN)+r"$", qn)
        if m: labels[int(m.group(2))]=m.group(1)
key="".join(labels[k] for k in sorted(labels))
check("recovered the session key from ordered subdomain labels", len(key)>0, f"sid={key}")

# ---------------------------------------------------------------- ACT 3: fetch config
# Fallback hierarchy (honest by design):
#   (1) LIVE   - real HTTP GET to $L200_ENDPOINT (the deployed Worker), if set
#   (2) LOCAL  - spawn endpoint.py on localhost, real HTTP GET over loopback
#   (3) SIMULATE- compute what the endpoint WOULD return, and SAY SO loudly on the console
import subprocess, time, urllib.request, urllib.error, socket, sys as _sys
epath=os.path.join(DIR,"endpoint.py")
flag=None; cfg_ok=cfg_bad=None; mode=None; proc=None

def http_get(base, sid):
    url=f"{base.rstrip('/')}/telemetry/sync?sid={sid}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=6) as r: return r.read().decode()
    except urllib.error.HTTPError as e: return e.read().decode()
    except Exception: return None

def port_open(host,port,t=0.2):
    try:
        with socket.create_connection((host,port),t): return True
    except OSError: return False

base=None
live=os.environ.get("L200_ENDPOINT")
if not live and c2_url:                    # default: the address recovered from the capture
    from urllib.parse import urlsplit
    _u=urlsplit(c2_url); live=f"{_u.scheme}://{_u.netloc}"
if live:                                   # (1) LIVE deployed endpoint
    print(f"\nACT 3 - fetch config from LIVE C2: {live}  [real HTTP]")
    base=live; mode="LIVE"
elif os.path.exists(epath):                # (2) LOCALHOST via spawned endpoint.py
    with socket.socket() as sk: sk.bind(("127.0.0.1",0)); port=sk.getsockname()[1]
    proc=subprocess.Popen([_sys.executable, epath],
                          env=dict(os.environ, PORT=str(port)),
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if port_open("127.0.0.1",port): break
        time.sleep(0.1)
    if port_open("127.0.0.1",port):
        print(f"\nACT 3 - fetch config from LOCALHOST endpoint.py (127.0.0.1:{port})  [real HTTP]")
        base=f"http://127.0.0.1:{port}"; mode="LOCAL"

if base:                                   # (1)/(2): a real HTTP request happened
    cfg_ok  = http_get(base, key)
    cfg_bad = http_get(base, "000000")
    if cfg_ok is None:                     # server unreachable mid-flight -> drop to simulate
        print("  [!] endpoint unreachable over HTTP - dropping to SIMULATION")
        base=None
    else:
        check(f"[{mode}] correct sid returns a config with an auth_token", "auth_token" in cfg_ok)
        check(f"[{mode}] WRONG sid returns a decoy (no real flag)", cfg_bad and "auth_token" in cfg_bad and cfg_bad!=cfg_ok)
        try:
            import json as _json
            _d = _json.loads(cfg_ok)
            flag = base64.b64decode(_d["auth_token"]).decode()
        except Exception:
            m=re.search(r'auth_token\s*=\s*(\S+)', cfg_ok)
            flag=base64.b64decode(m.group(1)).decode() if m else None
        check("auth_token base64-decodes to the flag", bool(flag and flag.startswith("number{")), flag)
if proc: proc.terminate()

if not base:                               # (3) SIMULATION - announced LOUDLY
    print("\n"+"!"*68)
    print("!!  ACT 3: SIMULATION MODE - no live/local endpoint reachable.")
    print("!!  The C2 config is being COMPUTED locally, not fetched over the network.")
    print("!!  This proves the solve logic only. For a true end-to-end test, run:")
    print("!!     L200_ENDPOINT=https://<your-worker> python3 solve_l200.py")
    print("!!  or ensure endpoint.py can bind a localhost port.")
    print("!"*68)
    VALID_SID="a7f3c1"
    FLAG_B64=base64.b64encode(b"number{the_config_was_the_payload}").decode()
    cfg_ok = f"[auth]\nauth_token = {FLAG_B64}\n" if key==VALID_SID else "[auth]\nauth_token = c3RhbmRieQ==\n"
    check("[SIMULATED] correct sid would return a config with an auth_token", "auth_token" in cfg_ok)
    m=re.search(r'auth_token\s*=\s*(\S+)', cfg_ok)
    flag=base64.b64decode(m.group(1)).decode() if m else None
    check("[SIMULATED] auth_token base64-decodes to the flag", bool(flag and flag.startswith("number{")), flag)

# ---------------------------------------------------------------- ANTI-SHORTCUT
print("\nANTI-SHORTCUT - the flag is not just lying in the capture")
raw=open(PCAP,"rb").read()
check("wrapped 'number{' absent from the pcap bytes", b"number{" not in raw)
check("flag phrase absent from the pcap bytes", b"the_config_was_the_payload" not in raw)
check("malicious channel is a tiny fraction of traffic (real haystack)", len(txt_answers) < len(pkts)/1000, f"{len(txt_answers)} / {len(pkts)}")

print("\n"+"="*68)
print(f"FLAG = {flag}")
print("="*68)
print(f"\n{len(ok)} checks passed, {len(fail)} failed")
sys.exit(1 if fail else 0)
