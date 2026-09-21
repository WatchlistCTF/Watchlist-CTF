/**
 * F250 "Trap Street" - canary check-in endpoint (the flag oracle).
 *
 * Story: the canary in decima_subject_register.xlsx phones home to
 *   transit.northernlights.gg/checkin?id=<canary-id>
 * The Machine's receiver acknowledges every beacon, but only the correct
 * canary id is handed the flag. Wrong/missing id still gets a clean
 * "received" (so the endpoint looks like a real beacon sink and never
 * confirms a guess).
 *
 * Deploy: see wrangler.toml. Flag can be inlined (below) or set as a
 * secret with `wrangler secret put FLAG` (env.FLAG wins if present).
 */

const CANARY_ID = "NLA-2026-04";
const FLAG = "number{shaw_followed_the_breadcrumbs}";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/"; // tolerate trailing slash

    if (path !== "/checkin") {
      return json({ error: "not found" }, 404);
    }

    const id = (url.searchParams.get("id") || "").trim();
    const base = { status: "received", ts: new Date().toISOString() };

    if (id === CANARY_ID) {
      return json({
        ...base,
        token: id,
        flag: (env && env.FLAG) || FLAG,
        message: "Canary acknowledged. The Machine sees you.",
      });
    }

    // any other id (or none): acknowledge like a real sink, reveal nothing
    return json(base);
  },
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj, null, 2) + "\n", {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}
