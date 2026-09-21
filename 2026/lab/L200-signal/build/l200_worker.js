/**
 * L200 Signal - C2 Telemetry Worker
 * Serves relay config to authenticated implants.
 * Correct sid → real config (flag in auth_token, base64)
 * Wrong sid  → decoy STANDBY config
 * Bad format → 400
 * Wrong path → 404
 * Rate limit → 429
 *
 * KV namespace binding: RL (rate limiting)
 * Deploy: npx wrangler deploy
 */

const SID      = "a7f3c1";
const FLAG     = "number{the_config_was_the_payload}";
const RATE_MAX = 8;   // requests per window
const RATE_WIN = 60;  // window in seconds

const SID_RE = /^[0-9a-f]{6}$/;

export default {
  async fetch(request, env, ctx) {
    const url    = new URL(request.url);
    const method = request.method;

    // ── Only serve GET /telemetry/sync ───────────────────────────────────
    if (url.pathname !== "/telemetry/sync") {
      return respond(404, { error: "not found" });
    }
    if (method !== "GET") {
      return respond(405, { error: "method not allowed" });
    }

    // ── Rate limiting (KV) ───────────────────────────────────────────────
    if (env.RL) {
      const ip      = request.headers.get("CF-Connecting-IP") || "unknown";
      const rateKey = `rate:${ip}`;
      const now     = Math.floor(Date.now() / 1000);

      const raw = await env.RL.get(rateKey, { type: "json" });
      if (raw) {
        const { count, window_start } = raw;
        const age = now - window_start;
        if (age < RATE_WIN && count >= RATE_MAX) {
          return respond(429, {
            error:       "rate limited",
            retry_after: RATE_WIN - age,
          });
        }
        const newCount  = age >= RATE_WIN ? 1 : count + 1;
        const newStart  = age >= RATE_WIN ? now : window_start;
        ctx.waitUntil(
          env.RL.put(rateKey,
            JSON.stringify({ count: newCount, window_start: newStart }),
            { expirationTtl: RATE_WIN * 2 }
          )
        );
      } else {
        ctx.waitUntil(
          env.RL.put(rateKey,
            JSON.stringify({ count: 1, window_start: now }),
            { expirationTtl: RATE_WIN * 2 }
          )
        );
      }
    }

    // ── Validate sid ─────────────────────────────────────────────────────
    const sid = url.searchParams.get("sid") || "";
    if (!SID_RE.test(sid)) {
      return respond(400, {
        error:  "bad request",
        detail: "sid parameter required (6 lowercase hex chars)",
      });
    }

    // ── Serve config ─────────────────────────────────────────────────────
    const ts = new Date().toISOString();

    if (sid === SID) {
      // Correct sid - real config, flag in auth_token
      return respond(200, {
        node_id:       "relay-7f3a",
        operator:      "decima-cloud-ui",
        status:        "ACTIVE",
        sync_interval: 300,
        auth_token:    btoa(FLAG),
        endpoints: {
          primary:  "https://relay-7f3a.northernlights.gg/api",
          fallback: "https://relay-7f3a.xonnie.ai/sync",
        },
        session:   sid,
        timestamp: ts,
      });
    } else {
      // Wrong sid - decoy standby config, no flag
      return respond(200, {
        node_id:       "relay-7f3a",
        operator:      null,
        status:        "DECOY_STANDBY",
        sync_interval: 3600,
        auth_token:    btoa("STANDBY"),
        endpoints: {
          primary:  "https://relay-7f3a.northernlights.gg/api",
          fallback: null,
        },
        session:   sid,
        timestamp: ts,
      });
    }
  },
};

function respond(status, body) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
