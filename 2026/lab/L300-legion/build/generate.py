#!/usr/bin/env python3
"""
L300 "Legion" - capture generator + separation proof.

Builds intercept.pcap: 100 jittered C2 beacons (Samaritan's distributed nodes)
hidden in heavy benign noise, plus the B350 breadcrumb. Also writes answer.json
(token -> country, SERVER-SIDE ONLY).

The whole challenge lives or dies on ONE property: the 100 real beacons must
separate cleanly from the noise by their *timing regularity*, with a comfortable
margin, and neither "group by destination" nor "find periodic traffic" alone may
yield exactly 100. This script proves that before writing the pcap.
"""
import json, random, struct, statistics, ipaddress
from pathlib import Path
import numpy as np

random.seed(1337); np.random.seed(1337)
OUT = Path("l300-work")

HUB      = "203.0.113.66"          # Samaritan hub (TEST-NET-3); themed PTR core.samaritan-relevance.net
HUB_PORT = 8443
KEY      = 0x5A                     # simple XOR (Rosetta = recover this)
WINDOW   = 2400                     # ~40 min capture
BASE_T   = 1694000000              # epoch base for packet timestamps

# 100 distinct ISO-3166 alpha-2 country codes (flavor; the token carries the cc)
COUNTRIES = ["US","GB","DE","FR","BR","IN","CN","RU","JP","KR","CA","AU","MX","ES","IT",
"NL","SE","NO","FI","DK","PL","UA","TR","IR","SA","AE","EG","ZA","NG","KE","MA","DZ","TN",
"GH","ET","TZ","UG","SN","CI","CM","AR","CL","CO","PE","VE","EC","BO","PY","UY","CR","PA",
"GT","DO","CU","JM","TH","VN","ID","MY","PH","SG","PK","BD","LK","NP","MM","KH","LA","MN",
"KZ","UZ","AZ","GE","AM","IL","JO","LB","IQ","KW","QA","OM","YE","SY","GR","PT","IE","BE",
"CH","AT","CZ","SK","HU","RO","BG","RS","HR","SI","LT","LV","EE"]
assert len(COUNTRIES) == 100 == len(set(COUNTRIES))

def rand_pub_ip(used):
    while True:
        ip = ".".join(str(random.randint(1, 223)) for _ in range(4))
        try:
            a = ipaddress.IPv4Address(ip)
            if a.is_global and ip not in used:
                used.add(ip); return ip
        except ValueError:
            pass

def jittered(period, jit, n, start):
    """n timestamps starting near `start`, spaced `period` +/- uniform jitter."""
    t = start + random.uniform(0, period); out = []
    for _ in range(n):
        out.append(t); t += period + random.uniform(-jit, jit)
    return out

def irregular(n, start, lo, hi):
    """n timestamps with intervals drawn uniformly in [lo,hi] -> high CV."""
    t = start + random.uniform(0, hi); out = []
    for _ in range(n):
        out.append(t); t += random.uniform(lo, hi)
    return out

def encode_payload(node_id, token):
    blob = struct.pack(">H16s", node_id, token.encode())
    return bytes(b ^ KEY for b in blob)

used = set()
flows = []   # each: dict(src,dst,dport,kind,times,payloads)
answer = {}  # token -> cc
meta   = {}  # token -> {node_id, ip, cc}

# ---- A. the 100 real beacons: same hub, low-jitter ~30s, 40-80 check-ins -------
for node_id, cc in enumerate(COUNTRIES):
    ip = rand_pub_ip(used)
    token = f"{cc}-{random.randbytes(4).hex()}"
    answer[token] = cc; meta[token] = {"node_id": node_id, "ip": ip, "cc": cc}
    n = random.randint(40, 80)
    times = jittered(period=random.uniform(28, 32), jit=3.0, n=n, start=random.uniform(0, 120))
    pays  = [encode_payload(node_id, token)] * n
    flows.append(dict(src=ip, dst=HUB, dport=HUB_PORT, kind="beacon", times=times, payloads=pays))

# ---- B. CHATTY hub noise: SAME hub, similar packet COUNT, but irregular --------
#         (the real test: only timing regularity separates these from beacons)
for _ in range(45):
    ip = rand_pub_ip(used)
    n = random.randint(40, 90)
    times = irregular(n, start=random.uniform(0, 300), lo=2, hi=120)
    pays  = [random.randbytes(random.randint(12, 28)) for _ in range(n)]
    flows.append(dict(src=ip, dst=HUB, dport=HUB_PORT, kind="hub_chatty", times=times, payloads=pays))

# ---- C. SPARSE hub noise: scanners / one-off retries (too few to score) --------
for _ in range(220):
    ip = rand_pub_ip(used)
    n = random.randint(1, 7)
    times = irregular(n, start=random.uniform(0, WINDOW), lo=1, hi=WINDOW)
    pays  = [random.randbytes(random.randint(8, 40)) for _ in range(n)]
    dport = HUB_PORT if random.random() < 0.5 else random.randint(1, 65535)
    flows.append(dict(src=ip, dst=HUB, dport=dport, kind="hub_sparse", times=times, payloads=pays))

# ---- D. PERIODIC traffic to OTHER hosts: NTP / health-checks -------------------
#         (low CV but NOT to the hub -> "find periodic traffic" over-collects)
OTHER = [rand_pub_ip(used) for _ in range(8)]   # time servers / monitoring hosts
for _ in range(160):
    ip = rand_pub_ip(used); dst = random.choice(OTHER)
    n = random.randint(20, 60)
    times = jittered(period=random.choice([64, 60, 120]), jit=2.0, n=n, start=random.uniform(0, 200))
    pays  = [random.randbytes(random.randint(8, 16)) for _ in range(n)]
    flows.append(dict(src=ip, dst=dst, dport=random.choice([123, 443, 9100]), kind="periodic_other",
                      times=times, payloads=pays))

# ---- E. BACKGROUND bulk: random chatter to many hosts (volume) -----------------
for _ in range(900):
    ip = rand_pub_ip(used); dst = rand_pub_ip(used)
    n = random.randint(1, 40)
    times = irregular(n, start=random.uniform(0, WINDOW), lo=0.2, hi=WINDOW/2)
    pays  = [random.randbytes(random.randint(8, 60)) for _ in range(n)]
    flows.append(dict(src=ip, dst=dst, dport=random.choice([53, 80, 443, 123, 3478]),
                      kind="background", times=times, payloads=pays))

# ---- F. B350 breadcrumb (flavor only) -----------------------------------------
flows.append(dict(src=rand_pub_ip(used), dst=HUB, dport=514, kind="b350",
                  times=[random.uniform(0, WINDOW)],
                  payloads=[b"<134>WARN: failover endpoint /contingency unreachable"]))

# ======================= SEPARATION PROOF (before writing) =====================
def cv(times):
    if len(times) < 9: return None
    d = np.diff(sorted(times))
    return float(np.std(d) / np.mean(d))

hub_flows = [f for f in flows if f["dst"] == HUB]
beacon_cvs = [cv(f["times"]) for f in flows if f["kind"] == "beacon"]
chatty_cvs = [cv(f["times"]) for f in flows if f["kind"] == "hub_chatty"]

# candidate sets a player might try
dst_hub_sources   = len({f["src"] for f in hub_flows})                       # "group by dst" alone
periodic_global   = sum(1 for f in flows if (c := cv(f["times"])) is not None and c < 0.2)  # "periodic" alone
periodic_and_hub  = sum(1 for f in hub_flows if (c := cv(f["times"])) is not None and c < 0.2)

print("==== SEPARATION PROOF ====")
print(f"beacon CV : min {min(beacon_cvs):.3f}  max {max(beacon_cvs):.3f}  mean {statistics.mean(beacon_cvs):.3f}")
print(f"chatty CV : min {min(chatty_cvs):.3f}  max {max(chatty_cvs):.3f}  mean {statistics.mean(chatty_cvs):.3f}")
print(f"gap between highest beacon and lowest chatty = {min(chatty_cvs) - max(beacon_cvs):.3f}")
print(f"'group by dst==hub' alone collects ........ {dst_hub_sources} sources  (want >>100)")
print(f"'periodic (CV<0.2) anywhere' alone collects  {periodic_global} flows    (want >>100)")
print(f"'periodic AND to hub' collects ............ {periodic_and_hub} flows    (want EXACTLY 100)")
# margin: does any threshold in a band give exactly 100?
band = [round(t, 2) for t in np.arange(0.12, 0.41, 0.01)
        if sum(1 for f in hub_flows if (c := cv(f["times"])) is not None and c < t) == 100]
print(f"thresholds in [0.12,0.40] that yield exactly 100: {band[0]} .. {band[-1]}  ({len(band)} values)")

# plot the CV distribution of hub flows
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
hub_cvs = [c for f in hub_flows if (c := cv(f["times"])) is not None]
bcv = [c for c in beacon_cvs]; ccv = [c for c in chatty_cvs]
plt.figure(figsize=(9, 3.4))
plt.hist(bcv, bins=30, range=(0, 1.0), color="#0e9e94", label=f"100 beacons (to hub)", alpha=.9)
plt.hist(ccv, bins=30, range=(0, 1.0), color="#c83232", label="chatty hub noise", alpha=.7)
plt.axvspan(band[0], band[-1], color="#888", alpha=.18, label=f"clean-split band {band[0]}-{band[-1]}")
plt.xlabel("timing regularity  (coefficient of variation of inter-arrival)")
plt.ylabel("flows"); plt.title("L300 beacon isolation: timing CV of src->hub flows")
plt.legend(fontsize=8); plt.tight_layout(); plt.savefig(OUT / "separation.png", dpi=110)
print("saved separation.png")

# stash flows for the pcap-writing step
import pickle
pickle.dump({"flows": flows, "answer": answer, "meta": meta},
            open(OUT / "_flows.pkl", "wb"))
# server-side files: token->cc map and the node-ordered grid of country codes
order = [None] * 100
for tok, m in meta.items():
    order[m["node_id"]] = m["cc"]
json.dump(answer, open(OUT / "answer.json", "w"))
json.dump(order, open(OUT / "board.json", "w"))
total_pkts = sum(len(f["times"]) for f in flows)
print(f"\nflows={len(flows)}  total_packets={total_pkts}  (pcap written by write_pcap.py)")
