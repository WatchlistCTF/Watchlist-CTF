#!/usr/bin/env python3
"""
Solver for T125 "RFC 2324" (HTCPCP).

The 418 you get from a browser or a GET is a breadcrumb, not the flag. RFC 2324
defines a custom BREW method, a Content-Type of message/coffeepot, and a body of
"start". Send all three and the pot pours the flag.

Usage:
    python3 t125_solve.py https://t125.northernlights.gg
    python3 t125_solve.py            # defaults to http://127.0.0.1:8421

Stdlib only (urllib supports arbitrary HTTP methods). The station enforces a
3-second per-IP cooldown, so this waits between requests. The event server is
offline now; point it at your own instance of t125_htcpcp.py to run it.
"""
import sys, re, time, urllib.request, urllib.error

COOLDOWN = 3.5   # the station rejects requests less than 3s apart (per IP)

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8421").rstrip("/")


def req(method, path, headers=None, body=None):
    data = body.encode() if isinstance(body, str) else body
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:                 # 4xx/5xx still carry a body
        return e.code, e.read().decode("utf-8", "replace")


def first_line(b):
    return b.splitlines()[0] if b else ""


def main():
    print(f"[*] target: {BASE}")

    # 1) recon: the greeting (and the Server header) reveal it speaks HTCPCP
    s, b = req("GET", "/")
    print(f"[*] GET /            -> {s}  {first_line(b)}")

    time.sleep(COOLDOWN)
    # 2) the breadcrumb: asking the wrong way returns 418 I'm a teapot
    s, b = req("GET", "/coffee")
    print(f"[*] GET /coffee      -> {s}  {first_line(b)}")

    time.sleep(COOLDOWN)
    # 3) speak the protocol properly: BREW + message/coffeepot + body 'start'
    s, b = req("BREW", "/pot-0",
               headers={"Content-Type": "message/coffeepot"}, body="start")
    print(f"[*] BREW /pot-0      -> {s}  {first_line(b)}")

    m = re.search(r"(number\{[^}]+\})", b)
    if m:
        print(f"\n[+] FLAG: {m.group(1)}")
        return 0
    print("\n[-] no flag found. full response:\n" + b)
    return 1


if __name__ == "__main__":
    sys.exit(main())
