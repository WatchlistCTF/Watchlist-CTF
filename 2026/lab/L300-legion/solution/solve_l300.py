#!/usr/bin/env python3
"""
L300 "Legion" - reference solver (also the build validator).

Solvable by program only: isolate the 100 beacons from the noise by timing
regularity, decode each payload to its token, POST all 100 to the target, watch
the board reach 100/100, receive the flag. Players write their own equivalent.

Usage:
    python3 solve_l300.py                                   decode only
    python3 solve_l300.py capture.pcap http://host:8080 TEAM   decode and submit

With no arguments it reads ../files/a342e7530aec5e66.pcap, finds the 100 beacons,
decodes their tokens and prints them. That part works offline.

Submitting needs the board server. The event's server was taken offline after
the CTF, so give the address of one you started yourself from the build files.
Without an address the script stops after decoding and says so.

Needs: scapy, numpy  (pip install scapy numpy)
Exit codes: 0 = flag received, 1 = submitted but no flag, 2 = decoded only
"""
import sys, struct, json, time, urllib.request
import numpy as np
from scapy.all import rdpcap, IP, Raw

import os
PCAP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "files", "a342e7530aec5e66.pcap")
HOST = sys.argv[2].rstrip("/") if len(sys.argv) > 2 else None
TEAM = sys.argv[3] if len(sys.argv) > 3 else "TESTTEAM"
KEY  = 0x5A

def cv(times):
    if len(times) < 9: return None
    d = np.diff(sorted(times)); return float(np.std(d) / np.mean(d))

def decode(payload):
    blob = bytes(b ^ KEY for b in payload)
    node_id, token = struct.unpack(">H16s", blob)
    return node_id, token.rstrip(b"\x00").decode("latin-1")

def post(token):
    req = urllib.request.Request(f"{HOST}/submit",
        data=json.dumps({"team": TEAM, "token": token}).encode(),
        headers={"Content-Type": "application/json"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:                       # be polite: back off and retry
                time.sleep(0.5 * (attempt + 1)); continue
            raise
    return {"ok": False, "error": "rate limited"}

print(f"[solver] reading {PCAP} ...")
pkts = rdpcap(PCAP)

# Stage 1-2: group flows to the busiest destination, isolate the regular ones
flows = {}
dst_count = {}
for p in pkts:
    if p.haslayer(IP) and p.haslayer(Raw):
        dst_count[p[IP].dst] = dst_count.get(p[IP].dst, 0) + 1
hub = max(dst_count, key=dst_count.get)             # the high fan-in destination
print(f"[solver] busiest destination (hub) = {hub}")
for p in pkts:
    if p.haslayer(IP) and p[IP].dst == hub and p.haslayer(Raw):
        flows.setdefault(p[IP].src, []).append((float(p.time), bytes(p[Raw].load)))

beacons = {s: ev for s, ev in flows.items() if (c := cv([t for t, _ in ev])) is not None and c < 0.2}
print(f"[solver] sources to hub = {len(flows)} ; regular beacons isolated = {len(beacons)}")

# Stage 3: decode each beacon's payload -> token
tokens = []
for s, ev in beacons.items():
    ev.sort()
    _, tok = decode(ev[0][1])
    tokens.append(tok)
print(f"[solver] decoded {len(tokens)} tokens (sample: {tokens[:3]})")

if not HOST:
    print("[solver] no board address given, so nothing was submitted.")
    print("[solver] all tokens:")
    for i in range(0, len(tokens), 10): print("   " + " ".join(tokens[i:i+10]))
    sys.exit(2)

# Stage 4: submit all; board fills live; flag at 100/100
flag, count = None, 0
for tok in tokens:
    res = post(tok)
    if res.get("ok"): count = res.get("count", count)
    if res.get("flag"): flag = res["flag"]
    time.sleep(0.02)
print(f"[solver] accepted {count}/100")
print(f"[solver] FLAG: {flag}" if flag else "[solver] no flag (did not reach 100)")
sys.exit(0 if flag == "number{a_hundred_faces_one_machine}" else 1)
