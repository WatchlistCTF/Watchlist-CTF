#!/usr/bin/env python3
"""
WATCHLIST CTF - T125 "RFC 2324" - HTCPCP Coffee Pot Server  (hardened v2 Sep 17 2026)
Implements a subset of RFC 2324 (Hyper Text Coffee Pot Control Protocol).

Endpoint: https://t125.northernlights.gg/pot-0
Flag returned only on a correct BREW request:
    curl -X BREW -H "Content-Type: message/coffeepot" -d "start" <endpoint>/pot-0

Features:
    - Correct HTCPCP behavior (418, 415, 400, 200)
    - Per-IP rate limiting (3s cooldown, 5 BREW attempts per 10 mins)
    - Structured request logging to t125.log
    - Solve tracking to t125_solves.json
    - GET /stats - uptime + brew count health check
    - Runs as a systemd service (see t125.service)

Usage:
    python3 t125_htcpcp.py
    python3 t125_htcpcp.py --port 8421 --host 127.0.0.1
"""

import json, time, logging, argparse, signal, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────
FLAG        = "number{the_machine_takes_it_black}"
HOST        = "127.0.0.1"
PORT        = 8421
LOG_FILE    = "t125.log"
SOLVES_FILE = "t125_solves.json"

RATE_COOLDOWN  = 3    # seconds between any two requests from same IP
BREW_WINDOW    = 600  # 10 min window for BREW attempt limiting
BREW_MAX       = 5    # max BREW attempts per IP per window

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("t125")

# ── STATE (in-memory, thread-safe via lock) ───────────────────────────────────
state_lock   = threading.Lock()
start_time   = time.time()
total_brews  = 0          # successful BREW requests
total_reqs   = 0          # all requests

# Per-IP rate limiting
ip_last_req  = defaultdict(float)          # ip -> timestamp of last request
ip_brew_log  = defaultdict(list)          # ip -> [timestamps of BREW attempts]

# ── SOLVE TRACKING ────────────────────────────────────────────────────────────
def load_solves():
    try:
        return json.loads(Path(SOLVES_FILE).read_text())
    except Exception:
        return []

def record_solve(ip: str, ua: str):
    solves = load_solves()
    entry = {
        "ip":         ip,
        "user_agent": ua,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }
    solves.append(entry)
    Path(SOLVES_FILE).write_text(json.dumps(solves, indent=2))
    log.info(f"SOLVE  ip={ip} ua={ua!r}")
    return len(solves)

# ── RATE LIMITING ─────────────────────────────────────────────────────────────
def check_rate(ip: str) -> tuple[bool, str]:
    """Returns (allowed, reason). Called before processing any request."""
    now = time.time()
    with state_lock:
        last = ip_last_req[ip]
        if now - last < RATE_COOLDOWN:
            return False, f"slow down - wait {RATE_COOLDOWN}s between requests"
        ip_last_req[ip] = now
    return True, ""

def check_brew_rate(ip: str) -> tuple[bool, str]:
    """Returns (allowed, reason). Called only for BREW requests."""
    now = time.time()
    with state_lock:
        # Prune old entries outside the window
        ip_brew_log[ip] = [t for t in ip_brew_log[ip] if now - t < BREW_WINDOW]
        if len(ip_brew_log[ip]) >= BREW_MAX:
            wait = int(BREW_WINDOW - (now - ip_brew_log[ip][0]))
            return False, f"too many BREW attempts - wait {wait}s"
        ip_brew_log[ip].append(now)
    return True, ""

# ── HTTP HANDLER ──────────────────────────────────────────────────────────────
class PotHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress default Apache-style logs; we write our own

    def _ip(self):
        # T125 is behind nginx - use X-Real-IP only (nginx sets this)
        # Never trust X-Forwarded-For - it is trivially spoofable
        return self.headers.get("X-Real-IP") or self.client_address[0]

    def _ua(self):
        return self.headers.get("User-Agent", "")

    def _send(self, code: int, body: str, extra_headers: dict = None):
        b = body.encode()
        self.send_response(code)
        self.send_header("Server", "HTCPCP/1.1")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def _log_req(self, method: str, code: int, note: str = ""):
        global total_reqs
        with state_lock:
            total_reqs += 1
        log.info(
            f"REQ  method={method} path={self.path} "
            f"ip={self._ip()} status={code} "
            f"ua={self._ua()!r}"
            + (f" note={note}" if note else "")
        )

    def _rate_check(self) -> bool:
        allowed, reason = check_rate(self._ip())
        if not allowed:
            self._send(429, f"429 Too Many Requests\n{reason}\n")
            self._log_req(self.command, 429, note=reason)
            return False
        return True

    # ── GET ───────────────────────────────────────────────────────────────────
    def do_GET(self):
        if not self._rate_check():
            return

        path = self.path.rstrip("/")

        # Stats endpoint - health check / uptime
        if path in ("/stats", "/machine"):
            uptime = int(time.time() - start_time)
            h, m, s = uptime // 3600, (uptime % 3600) // 60, uptime % 60
            with state_lock:
                brews = total_brews
                reqs  = total_reqs
            body = (
                f"BREW-STATION :: MACHINE INVENTORY\n"
                f"status     : operational\n"
                f"uptime     : {h:02d}:{m:02d}:{s:02d}\n"
                f"requests   : {reqs}\n"
                f"brews      : {brews}\n"
                f"pot-0      : ready\n"
            )
            self._send(200, body)
            self._log_req("GET", 200, note="stats")
            return

        # 418 bait paths
        if path in ("/coffee", "/brew", "/tea", "/pot"):
            body = (
                "I'm a teapot.\n"
                "You asked the wrong way.\n"
                "This node speaks RFC 2324 (HTCPCP).\n"
                "Try: BREW /pot-0 with Content-Type: message/coffeepot\n"
            )
            self._send(418, body, {"X-RFC": "2324"})
            self._log_req("GET", 418, note="bait-path")
            return

        # Default greeting
        body = (
            "BREW-STATION :: break-room node\n"
            "\n"
            "I catalog every device on the network. This one makes coffee.\n"
            "It is old, and it is particular.\n"
            "\n"
            "It will not answer to a browser.\n"
            "It will not answer to the wrong request.\n"
            "It follows a standard written long ago:\n"
            "\n"
            "  RFC 2324 - Hyper Text Coffee Pot Control Protocol\n"
            "  https://www.rfc-editor.org/rfc/rfc2324\n"
            "\n"
            "POT  : /pot-0\n"
            "\n"
            "  - THE MACHINE\n"
        )
        self._send(200, body)
        self._log_req("GET", 200)

    # ── POST ──────────────────────────────────────────────────────────────────
    def do_POST(self):
        if not self._rate_check():
            return
        body = (
            "I'm a teapot.\n"
            "POST is deprecated here.\n"
            "RFC 2324 defines a better verb.\n"
        )
        self._send(418, body, {"X-RFC": "2324"})
        self._log_req("POST", 418, note="wrong-method")

    # ── BREW ──────────────────────────────────────────────────────────────────
    def do_BREW(self):
        if not self._rate_check():
            return

        # BREW-specific rate limit
        allowed, reason = check_brew_rate(self._ip())
        if not allowed:
            self._send(429, f"429 Too Many Requests\n{reason}\n")
            self._log_req("BREW", 429, note=reason)
            return

        # Must target /pot-0
        if self.path.rstrip("/") != "/pot-0":
            self._send(404, "404 Not Found\nNo pot at that path. Try /pot-0\n")
            self._log_req("BREW", 404, note="wrong-path")
            return

        # Must have correct Content-Type
        ct = self.headers.get("Content-Type", "")
        if ct != "message/coffeepot":
            body = (
                "415 Unsupported Media Type\n"
                "RFC 2324 requires: Content-Type: message/coffeepot\n"
            )
            self._send(415, body)
            self._log_req("BREW", 415, note=f"wrong-content-type={ct!r}")
            return

        # Read body - cap at 64 bytes ("start" is 5 bytes, no legitimate body is larger)
        length = min(int(self.headers.get("Content-Length", 0)), 64)
        req_body = self.rfile.read(length).decode(errors="replace").strip() if length else ""

        # Must have body: start
        if req_body != "start":
            body = (
                "400 Bad Request\n"
                "Send body 'start' to begin brewing.\n"
                f"Got: {req_body!r}\n"
            )
            self._send(400, body)
            self._log_req("BREW", 400, note=f"wrong-body={req_body!r}")
            return

        # Correct BREW - serve the flag
        global total_brews
        with state_lock:
            total_brews += 1
            brew_num = total_brews

        solve_count = record_solve(self._ip(), self._ua())
        body = (
            "Brewing... done.\n"
            "\n"
            f"{FLAG}\n"
            "\n"
            f"[ brew #{brew_num} served · solve #{solve_count} ]\n"
        )
        self._send(200, body)
        self._log_req("BREW", 200, note=f"FLAG brew={brew_num} solve={solve_count}")

    # ── CATCH-ALL for other methods ───────────────────────────────────────────
    def do_OPTIONS(self):
        self._send(200, "Allowed: GET, BREW\n", {"Allow": "GET, BREW"})
        self._log_req("OPTIONS", 200)

    def handle_error(self, request, client_address):
        pass  # suppress connection reset noise


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="T125 HTCPCP server")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), PotHandler)

    def shutdown(sig, frame):
        log.info("SHUTDOWN signal received - shutting down")
        threading.Thread(target=server.shutdown).start()
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    log.info(f"STARTUP  HTCPCP server on {args.host}:{args.port}")
    log.info(f"STARTUP  flag={FLAG}")
    log.info(f"STARTUP  rate_cooldown={RATE_COOLDOWN}s  brew_max={BREW_MAX}/{BREW_WINDOW}s")
    server.serve_forever()


if __name__ == "__main__":
    main()
