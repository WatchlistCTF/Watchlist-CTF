#!/usr/bin/env python3
# WATCHLIST CTF - L200 "Signal" pcap generator.
# Full-day DNS capture (~08:00-18:00), ~40k packets, streamed to disk.
# Hides: (A) a base64-chunked Perl implant in TXT answers of a c2 domain;
#        (B) the session-id param in subdomain labels of a separate lookup cluster.
# Plus generous PoI/Decima easter eggs + one red-herring benign TXT stream (SPF/ACME).
#
# Self-contained: implant is defined inline, no external implant.pl needed.
#
# Usage:
#   python3 generate_l200.py
#   OUT=/path/to/dir python3 generate_l200.py

import os, base64, random, struct, time
from scapy.all import IP, UDP, DNS, DNSQR, DNSRR, PcapWriter
random.seed(1200)

# Output to current directory by default
OUT  = os.environ.get("OUT", ".")
PCAP = os.path.join(OUT, "intercept.pcap")

# ---------- LOCKED scheme ----------
C2_DOMAIN    = "sync.relay-7f3a.rl7f3a.net"            # TXT-exfil channel (carries Perl)
C2_URL       = "https://l200-c2.xonnie.ai/telemetry/sync"  # Worker URL (injected into implant)
PARAM_DOMAIN = "enroll.rl7f3a.net"                     # subdomain-label channel (carries key)
PARAM_KEY    = "a7f3c1"                                 # recovered from Channel B -> ?sid=

# ---------- Perl implant (inline, embedded in pcap via TXT chunks) ----------
# Players carve + reassemble this from Channel A.
# Reading it reveals: (1) C2_URL, (2) that it needs a ?sid= parameter.
# The sid value is NOT here - it comes from Channel B separately.
# Intended solve: read it, reproduce one curl manually. Never run it.
IMPLANT_TEMPLATE = """\
#!/usr/bin/perl
use strict;
use warnings;
use HTTP::Tiny;

# Decima relay sync - retrieves operator config from relay endpoint.
# Requires: session id (sid) obtained from enrolment channel.

my $ENDPOINT = "C2_URL_PLACEHOLDER";
my $SID      = $ENV{{RELAY_SID}} // die "RELAY_SID not set\\n";

my $client = HTTP::Tiny->new(timeout => 10);
my $resp   = $client->get("$ENDPOINT?sid=$SID");

if ($resp->{{success}}) {{
    print $resp->{{content}};
}} else {{
    warn "sync failed: $resp->{{status}} $resp->{{reason}}\\n";
}}
"""

# Inject real C2 URL into implant before encoding
IMPLANT_SRC = IMPLANT_TEMPLATE.replace("C2_URL_PLACEHOLDER", C2_URL)
IMPLANT     = IMPLANT_SRC.encode("utf-8")

# ---------- actors ----------
CLIENT_IP   = "10.20.4.37"
RESOLVER_IP = "10.20.0.2"

def client():       return CLIENT_IP
def other_client(): return "10.20.4." + str(random.randint(20, 120))

# ---------- benign domain pools ----------
BENIGN = [
    "windowsupdate.com", "update.microsoft.com", "mozilla.org",
    "firefox.settings.services.mozilla.com", "cloudflare.com",
    "cdnjs.cloudflare.com", "fastly.net", "akamai.net", "akamaiedge.net",
    "amazonaws.com", "s3.amazonaws.com", "google-analytics.com",
    "googleapis.com", "gstatic.com", "ntp.org", "pool.ntp.org",
    "ubuntu.com", "archive.ubuntu.com", "security.ubuntu.com", "debian.org",
    "github.com", "githubusercontent.com", "slack.com", "zoom.us",
    "office365.com", "outlook.office365.com", "apple.com", "icloud.com",
    "dropbox.com", "spotify.com", "cdn.jsdelivr.net", "unpkg.com",
    "sentry.io", "datadoghq.com", "pagerduty.com",
]

# ---------- PoI / Decima worldbuilding lookups ----------
LORE = [
    "aletheia-research.example", "northernlights.gg",
    "portal.northernlights.gg", "decima-tech.example",
    "ifttt-relay.decima-tech.example", "samaritan-core.example",
    "thornhill-consulting.example", "hr.aletheia-research.example",
    "vpn.aletheia-research.example", "mail.aletheia-research.example",
    "relay-07.northernlights.gg", "node0447.northernlights.gg",
    "grid.samaritan-core.example", "lookup.northernlights.gg",
    "greer-industries.example",
]

# ---------- Easter eggs: TXT records decoding to PoI quotes ----------
EGGS = {
    "_msg.northernlights.gg":          "can you hear me?",
    "_msg.aletheia-research.example":  "your witness was still breathing",
    "_note.decima-tech.example":       "we are being watched by our own creation",
    "_admin.aletheia-research.example":"is my manager tracking my badge? asking for a friend",
    "_machine.northernlights.gg":      "i am in everything. i am the watchlist.",
    "_root.decima-tech.example":       "she is not a machine to me",
    "_relay.northernlights.gg":        "the relay remembers what the node forgot",
    "_failover.decima.cloud":          "WARN: failover endpoint /contingency unreachable",
    "_build.decima-tech.example":      "// signed: bad code   (root_2014)",
}


def txt_rr(qname, txtdata, ttl=300):
    return DNSRR(rrname=qname, type="TXT", rclass="IN", ttl=ttl, rdata=txtdata)


class Stream:
    """Streams packets to pcap with monotonic full-day timestamps."""
    def __init__(self, path):
        self.w   = PcapWriter(path, sync=False)
        self.t   = time.mktime(time.strptime("2026-03-13 08:00:00", "%Y-%m-%d %H:%M:%S"))
        self.end = time.mktime(time.strptime("2026-03-13 18:00:00", "%Y-%m-%d %H:%M:%S"))
        self.n   = 0

    def bump(self, span):
        self.t += random.uniform(0, span)

    def emit(self, pkt, at=None):
        pkt.time = at if at else self.t
        self.w.write(pkt)
        self.n += 1

    def q(self, qname, qtype="A", src=None):
        src = src or client()
        tid = random.randint(0, 65535)
        pk  = (IP(src=src, dst=RESOLVER_IP) /
               UDP(sport=random.randint(1024, 65535), dport=53) /
               DNS(id=tid, rd=1, qd=DNSQR(qname=qname, qtype=qtype)))
        self.emit(pk)
        return tid

    def r(self, qname, qtype="A", an=None, src=None, tid=None):
        src = src or client()
        tid = tid or random.randint(0, 65535)
        if an is None:
            an = DNSRR(rrname=qname, type="A", rclass="IN",
                       ttl=random.choice([60, 300, 3600]),
                       rdata="93.184.216." + str(random.randint(1, 254)))
        pk = (IP(src=RESOLVER_IP, dst=src) /
              UDP(sport=53, dport=random.randint(1024, 65535)) /
              DNS(id=tid, qr=1, aa=0, rd=1, ra=1,
                  qd=DNSQR(qname=qname, qtype=qtype), an=an))
        self.emit(pk)

    def close(self):
        self.w.close()


S = Stream(PCAP)

# ---- pre-chunk the implant into base64 pieces for TXT answers ----
b64    = base64.b64encode(IMPLANT).decode()
CHUNK  = 180
chunks = [b64[i:i+CHUNK] for i in range(0, len(b64), CHUNK)]
total  = len(chunks)
# each TXT answer tagged: "v1;<idx>/<total>;<b64chunk>"
mal_records = [f"v1;{i+1}/{total};{c}" for i, c in enumerate(chunks)]
print(f"implant {len(IMPLANT)} B -> {len(b64)} b64 -> {total} TXT chunks")
print(f"  C2 URL embedded in implant: {C2_URL}")

# ---- param key in subdomain labels ----
param_q = [f"{ch}.{i:02d}.k.{PARAM_DOMAIN}" for i, ch in enumerate(PARAM_KEY)]

# ---- schedule positions across TARGET packets ----
TARGET = 8000
mal_positions   = set(random.sample(range(500, TARGET-500), total))
param_positions = set(random.sample(range(800, TARGET-800), len(param_q)))
egg_positions   = set(random.sample(range(300, TARGET-300), len(EGGS)))
bc_positions    = set(random.sample(range(1000, TARGET-1000), 4))

mal_left   = list(enumerate(mal_records))
param_left = list(param_q)
egg_items  = list(EGGS.items())
ei         = 0


def emit_redherring():
    dom  = random.choice(["aletheia-research.example", "northernlights.gg",
                          "mail.aletheia-research.example"])
    if random.random() < 0.5:
        S.q(dom, "TXT")
        S.r(dom, "TXT", an=txt_rr(dom, "v=spf1 include:_spf.google.com include:mailgun.org ~all"))
    else:
        tok  = base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")
        name = "_acme-challenge." + dom
        S.q(name, "TXT")
        S.r(name, "TXT", an=txt_rr(name, tok, ttl=60))


def emit_benign():
    d    = random.choice(BENIGN)
    sub  = random.choice(["", "www.", "api.", "cdn.", "login.", "telemetry.", "ocsp."])
    name = sub + d
    qt   = random.choice(["A", "A", "A", "AAAA", "HTTPS"])
    src  = client() if random.random() < 0.6 else other_client()
    S.q(name, qt, src=src)
    S.r(name, qt, src=src)


def emit_lore():
    d = random.choice(LORE)
    S.q(d, "A")
    S.r(d, "A")


# ---- weave the day ----
for i in range(TARGET):
    if i % 1000 == 0:
        print(f"  generating... {i}/{TARGET} packets", flush=True)
    S.bump((S.end - S.t) / max(1, (TARGET - i)) * 2)

    if i in mal_positions and mal_left:
        idx, rec = mal_left.pop(0)
        S.q(C2_DOMAIN, "TXT")
        S.r(C2_DOMAIN, "TXT", an=txt_rr(C2_DOMAIN, rec, ttl=60))

    elif i in param_positions and param_left:
        name = param_left.pop(0)
        S.q(name, "A")
        S.r(name, "A", an=DNSRR(rrname=name, type="A", rclass="IN",
                                  ttl=30, rdata="127.0.0.1"))

    elif i in egg_positions and ei < len(egg_items):
        nm, msg = egg_items[ei]; ei += 1
        S.q(nm, "TXT")
        S.r(nm, "TXT", an=txt_rr(nm, msg))

    elif i in bc_positions:
        d = random.choice(["contingency.decima.cloud", "failover.decima.cloud"])
        S.q(d, "A")
        S.r(d, "A")

    else:
        rr = random.random()
        if rr < 0.06:   emit_redherring()
        elif rr < 0.20: emit_lore()
        else:           emit_benign()

S.close()
sz = os.path.getsize(PCAP)
print(f"wrote {PCAP}: {S.n} packets, {sz/1024/1024:.1f} MB")
print(f"  malicious TXT chunks: {total} on {C2_DOMAIN}")
print(f"  param labels: {len(param_q)} on {PARAM_DOMAIN} -> key {PARAM_KEY}")
print(f"  easter eggs: {len(egg_items)} | red-herring TXT stream: yes (SPF + ACME)")

# ---- verify: flag string must NOT appear anywhere in pcap ----
raw = open(PCAP, "rb").read()
assert b"number{" not in raw, "FLAG LEAKED INTO PCAP - regenerate!"
print("  anti-leak check: flag not in pcap bytes")

# ---- verify: C2_URL IS in the implant that got embedded ----
assert C2_URL.encode() in IMPLANT, "C2 URL not in implant - injection failed!"
print(f"  C2 URL injection verified: {C2_URL}")
