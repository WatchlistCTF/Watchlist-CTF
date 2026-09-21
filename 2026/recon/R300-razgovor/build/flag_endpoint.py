#!/usr/bin/env python3
"""
R300 Razgovor - Hop 4 flag endpoint (hardened v2)
Serves the flag at /relay-export/api/v2/legacy/export?node=relay-7c2a
Run behind nginx which proxies /relay-export/api/ to this Flask app on port 5328.

v2 hardening:
  - IP logging for every request (timestamp + IP + node + result)
  - Rate limiting by IP: max 30 requests per minute
  - Health check endpoint: GET /health
  - Malformed/oversized node param handled gracefully
  - Log file: flag_endpoint.log
  - Startup banner with config summary
"""
import datetime
import threading
import time
import os
from flask import Flask, request, jsonify
from pathlib import Path

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
FLAG       = "number{provenance_outlives_the_cleanup}"
VALID_NODE = "relay-7c2a"
RATE_MAX   = 30           # max requests per IP per minute
RATE_WIN   = 60.0         # seconds
LOG_FILE   = Path(__file__).resolve().parent / "flag_endpoint.log"

# ---------------------------------------------------------------------------
# Rate limiting + logging state
# ---------------------------------------------------------------------------
_lock    = threading.Lock()
_ip_hits = {}   # ip -> [timestamps]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_log_lock = threading.Lock()

def log(level, ip, action, detail=""):
    ts   = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts} [{level}] ip={ip} action={action}"
    if detail:
        line += f" {detail}"
    with _log_lock:
        print(line, flush=True)
        try:
            with open(LOG_FILE, "a") as f:
                f.write(line + "\n")
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
def is_rate_limited(ip):
    now = time.time()
    with _lock:
        hits = _ip_hits.setdefault(ip, [])
        hits[:] = [t for t in hits if now - t < RATE_WIN]
        if len(hits) >= RATE_MAX:
            return True
        hits.append(now)
        return False

def get_ip():
    """Get real client IP - reads X-Forwarded-For set by nginx."""
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or "unknown"

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/health")
def health():
    ip = get_ip()
    log("INFO", ip, "health_check")
    return jsonify({"ok": True}), 200

@app.route("/relay-export/api/v2/legacy/export")
def export():
    ip   = get_ip()
    node = request.args.get("node", "")[:64]  # cap length

    # Rate limit
    if is_rate_limited(ip):
        log("WARN", ip, "rate_limited", f"node={node!r}")
        return jsonify({"error": "rate limited"}), 429

    # Missing node param
    if not node:
        log("WARN", ip, "missing_node")
        return jsonify({"error": "node parameter required"}), 400

    # Invalid node
    if node != VALID_NODE:
        log("INFO", ip, "invalid_node", f"node={node!r}")
        return jsonify({"error": "node not found", "node": node}), 404

    # Valid - return flag
    log("INFO", ip, "flag_served", f"node={node!r}")
    return jsonify({
        "node":       node,
        "status":     "archived",
        "provenance": "nl-relay-artifacts-7c2a",
        "flag":       FLAG,
    })

@app.route("/relay-export/api/v2/legacy/status")
def status():
    ip = get_ip()
    log("INFO", ip, "status_check")
    return jsonify({"status": "operational", "version": "0.3.2"})

@app.route("/relay-export/")
def relay_root():
    ip = get_ip()
    log("INFO", ip, "relay_root")
    return jsonify({"status": "ok"}), 200

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"[flag_endpoint] port=5328 rate={RATE_MAX}/IP/{RATE_WIN}s log={LOG_FILE}")
    log("INFO", "server", "startup", f"port=5328 rate={RATE_MAX}/{RATE_WIN}s")
    app.run(host="127.0.0.1", port=5328, debug=False)
