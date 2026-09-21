#!/usr/bin/env python3
"""L300 - render the proven flow schedules into intercept.pcap, then re-verify
isolation from the actual file (not just the in-memory schedules)."""
import pickle, random, statistics
from pathlib import Path
import numpy as np
from scapy.all import Ether, IP, UDP, Raw, wrpcap, rdpcap

random.seed(99)
OUT = Path("l300-work")
HUB, HUB_PORT, BASE_T = "203.0.113.66", 8443, 1694000000
LINK_SRC, LINK_DST = "02:00:00:00:00:01", "02:00:00:00:00:02"   # mid-link tap MACs

d = pickle.load(open(OUT / "_flows.pkl", "rb"))
flows, answer, meta = d["flows"], d["answer"], d["meta"]

pkts = []
for f in flows:
    for t, payload in zip(f["times"], f["payloads"]):
        p = (Ether(src=LINK_SRC, dst=LINK_DST) /
             IP(src=f["src"], dst=f["dst"]) /
             UDP(sport=random.randint(1024, 65535), dport=f["dport"]) /
             Raw(load=payload))
        p.time = BASE_T + float(t)
        pkts.append(p)
pkts.sort(key=lambda p: p.time)
wrpcap(str(OUT / "intercept.pcap"), pkts)
import os
sz = os.path.getsize(OUT / "intercept.pcap")
print(f"wrote intercept.pcap : {len(pkts)} packets, {sz/1048576:.2f} MB")

# ---- re-verify isolation from the ACTUAL pcap ----
r = rdpcap(str(OUT / "intercept.pcap"))
flows_by_src = {}
for p in r:
    if p.haslayer(IP) and p[IP].dst == HUB and p.haslayer(Raw):
        flows_by_src.setdefault(p[IP].src, []).append(float(p.time))

def cv(times):
    if len(times) < 9: return None
    dd = np.diff(sorted(times)); return float(np.std(dd) / np.mean(dd))

hub_sources = len(flows_by_src)
beacons = {s: ts for s, ts in flows_by_src.items() if (c := cv(ts)) is not None and c < 0.2}
print(f"re-read: sources talking to hub = {hub_sources}")
print(f"re-read: low-CV (<0.2) hub flows = {len(beacons)}   (must be 100)")

# decode round-trip check on the isolated beacons
import struct
KEY = 0x5A
def decode(payload):
    blob = bytes(b ^ KEY for b in payload)
    node_id, token = struct.unpack(">H16s", blob)
    return node_id, token.rstrip(b"\x00").decode()
# pull first payload per beacon src and decode -> token must be in answer
ok = 0
src_first_payload = {}
for p in r:
    if p.haslayer(IP) and p[IP].dst == HUB and p.haslayer(Raw):
        s = p[IP].src
        if s in beacons and s not in src_first_payload:
            src_first_payload[s] = bytes(p[Raw].load)
for s, pl in src_first_payload.items():
    try:
        _, tok = decode(pl)
        if tok in answer: ok += 1
    except Exception: pass
print(f"re-read: beacon payloads that decode to a valid token = {ok}/100")

# anti-shortcut + breadcrumb checks
raw_bytes = Path(OUT / "intercept.pcap").read_bytes()
print(f"'number{{' present in pcap? {b'number{' in raw_bytes}   (must be False)")
print(f"B350 breadcrumb present?   {b'/contingency' in raw_bytes}   (must be True)")
