#!/usr/bin/env python3
"""
O250 "Manifest" reference solver / answer key.

Works from the ARTIFACT ONLY. Does not import common.py, it knows no planted
value in advance. If this recovers the flag blind, a player can too.

  python3 solve_o250.py /path/to/unpacked_files
  (unpack the challenge tar from ../files/ first)
  Needs only the Python 3 standard library. No network access.

Stages:
  01 triage      - group by hex, find which airframes fly circles
  02 judgment    - which orbits are surveillance (low/variable) vs holds (level)
  03 correlate   - two surveillance aircraft, different days, same centroid
  04 derive      - squawk fragment + callsign fragment + registry segment -> flag
"""

import csv
import json
import math
import os
import statistics as st
import sys

PASS = 0
FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {label}" + (f" - {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f" - {detail}" if detail else ""))
    return cond


def km(a, b, c, d):
    return math.hypot((a - c) * 111.0, (b - d) * 111.0 * math.cos(math.radians(a)))


def path_curviness(trace):
    """
    Ratio of path length to bounding-box diagonal, restricted to the densest
    cluster of points. High + spatially compact => an orbit. Straight => transit.
    Returns (is_circular, center_lat, center_lon, n_orbit_pts).
    """
    pts = [(p["lat"], p["lon"]) for p in trace if "lat" in p and "lon" in p]
    if len(pts) < 20:
        return (False, None, None, 0)

    # Find the densest spatial window: slide over the trace, find the longest
    # run whose points stay within ~4 km of their running centroid.
    best = None
    i = 0
    n = len(pts)
    while i < n:
        j = i
        cluster = []
        while j < n:
            cluster.append(pts[j])
            clat = st.mean(p[0] for p in cluster)
            clon = st.mean(p[1] for p in cluster)
            if km(pts[j][0], pts[j][1], clat, clon) > 4.0:
                cluster.pop()
                break
            j += 1
        if len(cluster) >= 20:
            clat = st.mean(p[0] for p in cluster)
            clon = st.mean(p[1] for p in cluster)
            # circular if points fan around the centroid: check heading coverage
            angles = sorted(math.atan2(p[1] - clon, p[0] - clat) for p in cluster)
            spread = _angular_coverage(angles)
            if best is None or len(cluster) > best[3]:
                best = (spread > 5.0, clat, clon, len(cluster), spread)
        i = j + 1 if j > i else i + 1

    if best is None:
        return (False, None, None, 0)
    is_circ = best[0]
    return (is_circ, best[1], best[2], best[3])


def _angular_coverage(sorted_angles):
    """How many radians of a full circle the points cover (orbit ~ 2pi)."""
    if len(sorted_angles) < 3:
        return 0.0
    # largest gap between consecutive angles; coverage = 2pi - largest_gap
    gaps = []
    for k in range(len(sorted_angles)):
        a = sorted_angles[k]
        b = sorted_angles[(k + 1) % len(sorted_angles)]
        gap = (b - a) % (2 * math.pi)
        gaps.append(gap)
    return (2 * math.pi - max(gaps))


def refine_centroid(trace, clat, clon):
    """
    Recover the true orbit center. Seed from LOW-ALTITUDE points near the rough
    center (the surveillance orbit sits low; transit/approach legs are high), so
    high-altitude approach points don't bias the mean. Then iterate on a tight
    radius. Recovers the center to tens of metres regardless of transit density.
    """
    # seed: low, near the rough center
    seed = [(p["lat"], p["lon"]) for p in trace
            if isinstance(p.get("alt_baro"), int) and p["alt_baro"] < 5000
            and km(p["lat"], p["lon"], clat, clon) < 6.0]
    if len(seed) >= 10:
        lat = st.mean(p[0] for p in seed)
        lon = st.mean(p[1] for p in seed)
    else:
        lat, lon = clat, clon
    for _ in range(6):
        core = [(p["lat"], p["lon"]) for p in trace
                if isinstance(p.get("alt_baro"), int) and p["alt_baro"] < 5000
                and km(p["lat"], p["lon"], lat, lon) < 2.5]
        if len(core) < 10:
            break
        nlat = st.mean(p[0] for p in core)
        nlon = st.mean(p[1] for p in core)
        if abs(nlat - lat) < 1e-6 and abs(nlon - lon) < 1e-6:
            break
        lat, lon = nlat, nlon
    return lat, lon


def orbit_altitude_profile(trace, clat, clon):
    """Altitude stats for points near the orbit center - level vs variable."""
    alts = []
    for p in trace:
        if "lat" not in p or not isinstance(p.get("alt_baro"), int):
            continue
        if km(p["lat"], p["lon"], clat, clon) < 4.0:
            alts.append(p["alt_baro"])
    if not alts:
        return (None, None, None)
    return (min(alts), max(alts), st.pstdev(alts) if len(alts) > 1 else 0)


def grid_cell_str(lat, lon, q):
    return f"{round(lat / q) * q:.3f},{round(lon / q) * q:.3f}"


def main(root):
    print("=" * 70)
    print(" O200 MANIFEST - reference solve")
    print("=" * 70)

    fleet = json.load(open(os.path.join(root, "fleet_week_20260914-20260920.json")))
    sites = list(csv.DictReader(open(os.path.join(root, "sites.csv"))))
    reg = json.load(open(os.path.join(root, "registry.json")))
    q = reg["grid_q"]

    ac = fleet["aircraft"]

    # ---------------------------------------------------------- STAGE 01
    print("\n[STAGE 01] Triage - group by hex, find circular tracks")
    orbiters = []
    for a in ac:
        circ, clat, clon, npts = path_curviness(a["trace"])
        if circ:
            orbiters.append((a, clat, clon, npts))
    check("more than one aircraft flies a circular pattern", len(orbiters) >= 2,
          f"{len(ac)} airframes, {len(orbiters)} circular")
    for a, clat, clon, npts in orbiters:
        print(f"    orbit: hex={a['hex']} r={a['r'].strip()} "
              f"center=({clat:.4f},{clon:.4f}) n={npts}")

    # ---------------------------------------------------------- STAGE 02
    print("\n[STAGE 02] Judgment - surveillance (low/variable) vs hold (level)")
    surveillance = []
    for a, clat, clon, npts in orbiters:
        lo, hi, sd = orbit_altitude_profile(a["trace"], clat, clon)
        level = (sd is not None and sd < 30)  # dead-level => holding pattern
        low = (lo is not None and lo < 5000)
        verdict = "SURVEILLANCE" if (low and not level) else "hold/other"
        print(f"    hex={a['hex']} alt[{lo}-{hi}] sd={sd:.0f} -> {verdict}")
        if low and not level:
            surveillance.append((a, clat, clon))
    check("exactly two aircraft show a surveillance profile", len(surveillance) == 2,
          f"{len(surveillance)} surveillance orbits")

    # ---------------------------------------------------------- STAGE 03
    print("\n[STAGE 03] Correlate - two tails, different days, same ground")
    if len(surveillance) != 2:
        return finish()
    (a1, la1, lo1), (a2, la2, lo2) = surveillance
    # refine each center to the tight orbit core (sheds transit-point bias)
    la1, lo1 = refine_centroid(a1["trace"], la1, lo1)
    la2, lo2 = refine_centroid(a2["trace"], la2, lo2)
    # days
    d1 = day_of(a1["trace"][0]["now"], fleet["window_start"])
    d2 = day_of(a2["trace"][0]["now"], fleet["window_start"])
    check("the two aircraft flew on different days", d1 != d2, f"day {d1} vs day {d2}")
    check("the two aircraft are different airframes (hex)", a1["hex"] != a2["hex"])
    sep = km(la1, lo1, la2, lo2)
    # The decisive test is not an arbitrary metre threshold (an eccentric
    # racetrack legitimately spreads the cloud) but whether BOTH orbits resolve
    # to the same registry grid cell - that is what makes them "the same place".
    cell1 = grid_cell_str(la1, lo1, q)
    cell2 = grid_cell_str(la2, lo2, q)
    check("both orbits resolve to the SAME grid cell (same watched ground)",
          cell1 == cell2, f"{cell1} vs {cell2} ({sep*1000:.0f} m apart)")

    # combined centroid
    clat = (la1 + la2) / 2
    clon = (lo1 + lo2) / 2
    print(f"    combined centroid: ({clat:.5f},{clon:.5f})")

    # the target is NOT in sites.csv
    nearest = min(sites, key=lambda s: km(clat, clon, float(s["lat"]), float(s["lon"])))
    ndist = km(clat, clon, float(nearest["lat"]), float(nearest["lon"]))
    check("the watched point is NOT a listed site (>1 km from nearest)", ndist > 1.0,
          f"nearest {nearest['site_code']} is {ndist:.2f} km away")

    # ---------------------------------------------------------- STAGE 04
    print("\n[STAGE 04] Derive - fragments + registry segment")

    # registry lookup by grid cell
    key = grid_cell_str(clat, clon, q)
    seg = reg["cells"].get(key, {}).get("segment", "<miss>")
    check("computed grid cell resolves to a live registry segment",
          seg not in ("<miss>", "0000"), f"cell {key} -> {seg}")

    # fragment A: squawk octal run on aircraft a1 or a2 (whichever has non-1200 squawks)
    fragA = recover_squawk_fragment(a1) or recover_squawk_fragment(a2)
    check("recovered fragment A from a squawk sequence", bool(fragA), repr(fragA))

    # fragment B: hex-decode the numeric callsign swap token
    fragB = recover_callsign_fragment(a1) or recover_callsign_fragment(a2)
    check("recovered fragment B from a callsign swap token", bool(fragB), repr(fragB))

    if fragA and fragB and seg not in ("<miss>", "0000"):
        flag = f"number{{{fragA}{fragB}_confirmed_{seg}}}"
        print(f"\n    ASSEMBLED FLAG: {flag}")
        check("assembled flag matches expected structure",
              flag == "number{overwatch_confirmed_5a3f}", flag)

    return finish()


def day_of(now_ms, window_start):
    return (now_ms - window_start) // 86_400_000


def recover_squawk_fragment(a):
    """Collect non-standard squawks in trace order, octal-decode digit stream."""
    squawks = []
    for p in a["trace"]:
        sq = p.get("squawk", "1200")
        if sq not in ("1200", "1201", "1202") and all(c in "01234567" for c in sq):
            squawks.append(sq)
    if not squawks:
        return None
    digits = "".join(squawks)
    # regroup by 3 octal digits -> ascii
    out = ""
    for i in range(0, len(digits) - 2, 3):
        try:
            v = int(digits[i:i + 3], 8)
            if 32 <= v < 127:
                out += chr(v)
        except ValueError:
            pass
    return out or None


def recover_callsign_fragment(a):
    """Find a bare-numeric callsign token in the trace; hex-decode it to ascii."""
    seen = set()
    for p in a["trace"]:
        cs = p.get("flight", "").strip()
        if cs and cs not in seen:
            seen.add(cs)
    for cs in seen:
        if len(cs) >= 6 and len(cs) % 2 == 0 and all(c in "0123456789ABCDEFabcdef" for c in cs):
            try:
                dec = bytes.fromhex(cs).decode()
                if dec.isprintable() and dec.isalpha():
                    return dec
            except (ValueError, UnicodeDecodeError):
                pass
    return None


def finish():
    print("\n" + "=" * 70)
    print(f" RESULT: {PASS}/{PASS+FAIL} checks passed")
    print("=" * 70)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(main(root))
