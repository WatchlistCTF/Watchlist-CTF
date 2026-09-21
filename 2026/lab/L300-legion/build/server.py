#!/usr/bin/env python3
"""
L300 "Legion" - the live target. HARDENED v2 (Sep 17 2026)

Security fixes vs v1:
  - Content-Length capped at 1KB (prevents OOM attack)
  - Team name: max 32 chars, alphanumeric+underscore+hyphen only
  - Token format: must match XX-xxxxxxxx before lookup
  - Rate limiting: per IP (not per team - team names are attacker-controlled)
  - MAX_BOARD_CONNS enforced (prevents thread exhaustion)
  - Board: team name validated same as HTTP
  - X-Forwarded-For removed (L300 is directly exposed, not behind nginx)

  HTTP  POST /submit   {"team": "...", "token": "..."}   -> validates, lights board
  TCP   board port     send the team name as first line, then watch grid fill

Pure stdlib (threaded) so it runs anywhere.
"""
import json, re, socket, threading, time, logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE    = Path(__file__).resolve().parent
ANSWER  = json.load(open(HERE / "answer.json"))     # token -> cc
ORDER   = json.load(open(HERE / "board.json"))      # node_id -> cc (grid order)
FLAG    = "number{a_hundred_faces_one_machine}"
LOG_FILE = HERE / "l300.log"

HTTP_PORT, BOARD_PORT = 8080, 8081

# ── Rate limiting (per IP, not per team) ─────────────────────────────────────
RATE_MAX, RATE_WIN = 120, 10.0          # 120 requests per IP per 10s

# ── Board connection limit ────────────────────────────────────────────────────
MAX_BOARD_CONNS = 100

# ── Input validation ──────────────────────────────────────────────────────────
MAX_BODY_BYTES  = 1024                  # 1KB cap on POST body
MAX_TEAM_LEN    = 32                    # team name max length
TEAM_RE         = re.compile(r'^[A-Za-z0-9_\-]{1,32}$')
TOKEN_RE        = re.compile(r'^[A-Z]{2}-[0-9a-f]{8}$')

LOCK        = threading.Lock()
TEAMS       = {}            # team -> set(cc)
BOARD_CONNS = {}            # team -> [socket,...]
IP_HITS     = {}            # ip   -> [timestamps]  (rate limit)
BOARD_CONN_COUNT = 0        # total active board connections

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ"
)

def log(level, ip, action, detail=""):
    msg = f"ip={ip} action={action}"
    if detail: msg += f" {detail}"
    getattr(logging, level.lower())(msg)

# ── Board rendering ───────────────────────────────────────────────────────────
C = dict(reset="\x1b[0m", dim="\x1b[2;37m", lit="\x1b[1;38;5;15;48;5;30m",
         head="\x1b[1;38;5;37m", bar="\x1b[38;5;30m", foot="\x1b[2;37m")

def render(team):
    got = TEAMS.get(team, set()); n = len(got)
    out = ["\x1b[2J\x1b[H",
           f"{C['head']}  SAMARITAN RELAY MAP   {n:>3}/100{C['reset']}\n"]
    for r in range(10):
        row = []
        for c in range(10):
            cc = ORDER[r * 10 + c]
            row.append(f"{C['lit']} {cc} {C['reset']}" if cc in got
                       else f"{C['dim']} \u00b7\u00b7 {C['reset']}")
        out.append(" " + " ".join(row) + "\n")
    filled = int(n / 100 * 40)
    out.append(f"\n  {C['bar']}[{'#'*filled}{'-'*(40-filled)}]{C['reset']}  {n}%\n")
    if n >= 100:
        out.append(f"\n  {C['head']}the net is mine. the number is yours:{C['reset']}\n  {FLAG}\n")
    else:
        out.append(f"\n  {C['foot']}name each one. i will light it as you go.{C['reset']}\n")
    return "".join(out)

def push(team):
    for s in list(BOARD_CONNS.get(team, [])):
        try:
            s.sendall(render(team).encode())
        except OSError:
            BOARD_CONNS[team].remove(s)

# ── HTTP submit handler ───────────────────────────────────────────────────────
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass     # suppress default access log

    def get_ip(self):
        # L300 is directly exposed - NEVER trust X-Forwarded-For
        return self.client_address[0]

    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        if self.path != "/submit":
            return self._json(404, {"ok": False, "error": "not found"})

        ip = self.get_ip()

        # ── 1. Body size cap ──────────────────────────────────────────────────
        try:
            cl = min(int(self.headers.get("Content-Length", 0)), MAX_BODY_BYTES)
            body = json.loads(self.rfile.read(cl) or b"{}")
        except Exception:
            log("warning", ip, "bad_request", "malformed json or oversized body")
            return self._json(400, {"ok": False, "error": "bad request"})

        # ── 2. Extract + validate team and token ──────────────────────────────
        team  = str(body.get("team",  ""))[:MAX_TEAM_LEN + 1]
        token = str(body.get("token", ""))[:20]

        if not TEAM_RE.match(team):
            log("warning", ip, "bad_team", f"team={team!r}")
            return self._json(400, {"ok": False,
                "error": "invalid team name (1-32 alphanumeric/hyphen/underscore)"})

        if not TOKEN_RE.match(token):
            log("warning", ip, "bad_token", f"team={team!r} token={token!r}")
            return self._json(400, {"ok": False,
                "error": "invalid token format (expected XX-xxxxxxxx)"})

        # ── 3. IP-based rate limiting ─────────────────────────────────────────
        now = time.time()
        with LOCK:
            h = IP_HITS.setdefault(ip, [])
            h[:] = [t for t in h if now - t < RATE_WIN]
            if len(h) >= RATE_MAX:
                log("warning", ip, "rate_limited", f"team={team!r}")
                return self._json(429, {"ok": False, "error": "rate limited"})
            h.append(now)

            # ── 4. Token lookup + board update ────────────────────────────────
            cc = ANSWER.get(token)
            if not cc:
                log("info", ip, "unknown_token", f"team={team!r} token={token!r}")
                return self._json(200, {"ok": False, "error": "unknown token",
                                        "count": len(TEAMS.get(team, set()))})

            TEAMS.setdefault(team, set()).add(cc)
            n = len(TEAMS[team])
            push(team)
            log("info", ip, "submit_ok", f"team={team!r} cc={cc} count={n}")

            if n >= 100:
                log("info", ip, "SOLVED", f"team={team!r} count=100 flag_released=true")
                return self._json(200, {"ok": True, "done": True,
                                        "count": 100, "flag": FLAG})
            return self._json(200, {"ok": True, "count": n})

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"ok": True, "teams": len(TEAMS),
                             "board_conns": BOARD_CONN_COUNT})
        else:
            self._json(404, {"ok": False, "error": "not found"})

# ── TCP board server ──────────────────────────────────────────────────────────
def board_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", BOARD_PORT))
    srv.listen(64)
    while True:
        conn, addr = srv.accept()
        ip = addr[0]
        with LOCK:
            if BOARD_CONN_COUNT >= MAX_BOARD_CONNS:
                log("warning", ip, "board_full",
                    f"active={BOARD_CONN_COUNT} max={MAX_BOARD_CONNS}")
                try:
                    conn.sendall(b"\nboard full -- try again shortly\n")
                except OSError:
                    pass
                conn.close()
                continue
        threading.Thread(target=board_client, args=(conn, ip), daemon=True).start()

def board_client(conn, ip):
    global BOARD_CONN_COUNT
    team = ""
    try:
        with LOCK:
            BOARD_CONN_COUNT += 1
        log("info", ip, "board_connect", f"active={BOARD_CONN_COUNT}")

        conn.sendall(b"team name? ")
        raw = conn.recv(256).decode(errors="ignore").strip()

        # Validate team name on board too
        if not TEAM_RE.match(raw):
            conn.sendall(b"\ninvalid team name\n")
            return

        team = raw
        log("info", ip, "board_join", f"team={team!r}")

        with LOCK:
            BOARD_CONNS.setdefault(team, []).append(conn)

        conn.sendall(render(team).encode())

        while True:
            if not conn.recv(1):
                break
    except OSError:
        pass
    finally:
        with LOCK:
            BOARD_CONN_COUNT -= 1
            if team and conn in BOARD_CONNS.get(team, []):
                BOARD_CONNS[team].remove(conn)
        log("info", ip, "board_disconnect",
            f"team={team!r} active={BOARD_CONN_COUNT}")
        conn.close()

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log("info", "server", "startup",
        f"HTTP :{HTTP_PORT} | board :{BOARD_PORT} | "
        f"rate={RATE_MAX}/IP/{RATE_WIN}s | max_board={MAX_BOARD_CONNS}")
    print(f"[server] HTTP /submit on :{HTTP_PORT}  | board on :{BOARD_PORT}  | "
          f"rate={RATE_MAX}/IP/{RATE_WIN}s | max_board={MAX_BOARD_CONNS}")
    threading.Thread(target=board_server, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), H).serve_forever()
