"""
O200 *Manifest* - planted truth.

Single source of truth for the whole challenge. The generator reads from here;
the solver NEVER imports this (it works from the artifact only).

Everything is deterministic under SEED so the artifact is byte-reproducible.

Verified mechanics (July 15):
  - two orbits (Mon + Thu) over an UNLISTED point recover a centroid to <40 m
  - the target grid cell is distinct from every decoy site's cell
  - nearest decoy site is 2.38 km away  (>> cell ~550 m >> recovery err ~40 m)
  - flag = frag_A('over') + frag_B('watch') + registry segment('5a3f')
"""

import math
import random

SEED = 20260915
RNG = random.Random(SEED)

# ---------------------------------------------------------------- geography
# THE TARGET - the unlisted point both aircraft orbit. NOT in sites.csv.
TARGET_LAT = 47.6205
TARGET_LON = -122.3493

# Grid quantization for the registry key. ~0.005 deg lat ~= 555 m.
# Must be >> recovery error (~40 m) and << nearest decoy (2.38 km).
GRID_Q = 0.005


def grid_cell(lat, lon, q=GRID_Q):
    """Deterministic grid-cell key. Dependency-free; the player can reproduce it."""
    return (round(lat / q) * q, round(lon / q) * q)


def cell_str(cell):
    return f"{cell[0]:.3f},{cell[1]:.3f}"


# 8 decoy facilities (the sites.csv haystack). NONE is the target.
# Each is >1 km from TARGET so no decoy cell collides with the target cell.
DECOY_SITES = {
    "GS-CASCADE":   (47.6480, -122.3200),
    "GS-DUWAMISH":  (47.5950, -122.3800),
    "GS-INTERBAY":  (47.6210, -122.4100),
    "GS-MAGNOLIA":  (47.6620, -122.3550),
    "GS-GEORGETOWN": (47.5880, -122.3300),
    "GS-EASTLAKE":  (47.6100, -122.3000),
    "GS-BALLARD":   (47.6350, -122.3900),
    "GS-SODO":      (47.6015, -122.3346),
}

# Herring C flies a *legitimate* holding pattern over this LISTED site.
HERRING_C_SITE = "GS-MAGNOLIA"

# ---------------------------------------------------------------- the flag
FRAG_A = "over"     # hidden in target A's squawk sequence (octal -> ascii)
FRAG_B = "watch"    # hidden in target B's callsign swap token
REGISTRY_SEGMENT = "5a3f"   # registry[target_cell]; decoy cells -> "0000"
FLAG = f"number{{{FRAG_A}{FRAG_B}_confirmed_{REGISTRY_SEGMENT}}}"

# ---------------------------------------------------------------- time frame
# Week of Mon 2026-09-14 .. Sun 2026-09-20 (epoch ms), UTC.
WEEK_START_MS = 1757808000000   # 2026-09-14 00:00:00 UTC
DAY_MS = 86_400_000
HOUR_MS = 3_600_000
MIN_MS = 60_000
SEC_MS = 1000

# ---------------------------------------------------------------- fleet spec
# hex must be stable per airframe (24-bit ICAO). callsign (flight) is mutable.

def _hex(n):
    return format(0xA00000 + n, "06x")


# The two TARGETS and the three signal-mimicking HERRINGS are explicit.
# The rest are routine transits generated procedurally.

TARGET_A = {
    "hex": _hex(0x1D31),
    "callsign_initial": "DCA418",   # departs as a Decima corporate flight
    "callsign_swap":    "N418DC",   # swaps mid-trace to a bare N-number
    "day_offset": 0,                # Monday
    "start_hour": 9,
    "role": "target_A",
    # fragment A "over" -> octal of each char, used as a squawk run
    "squawk_fragment": FRAG_A,
}

TARGET_B = {
    "hex": _hex(0x2E42),
    "callsign_initial": "DCA522",
    # The swap token is the hex encoding of fragment B ("watch" -> 7761746368),
    # styled as a bare numeric callsign. NOT the plaintext word. Player hex-decodes.
    "callsign_swap":    None,  # set by generator from callsign_fragment
    "day_offset": 3,                # Thursday
    "start_hour": 14,
    "role": "target_B",
    "callsign_fragment": FRAG_B,
}

HERRING_C = {           # legit holding pattern over a LISTED site
    "hex": _hex(0x3F11),
    "callsign_initial": "SKW2841",
    "callsign_swap": None,
    "day_offset": 1,
    "start_hour": 11,
    "role": "herring_orbit",
    "orbit_site": HERRING_C_SITE,
}

HERRING_D = {           # legit callsign change at a stopover
    "hex": _hex(0x4A73),
    "callsign_initial": "FDX1190",
    "callsign_swap": "FDX2205",
    "day_offset": 2,
    "start_hour": 7,
    "role": "herring_callsign",
}

HERRING_E = {           # coverage gap over water
    "hex": _hex(0x5B90),
    "callsign_initial": "ASA615",
    "callsign_swap": None,
    "day_offset": 4,
    "start_hour": 16,
    "role": "herring_gap",
}

NAMED = [TARGET_A, TARGET_B, HERRING_C, HERRING_D, HERRING_E]

# ~10 routine transits to fill the haystack, each flying multiple legs across the week.
N_ROUTINE = 11
ROUTINE_CALLSIGNS = ["QXE201", "QXE338", "ASA412", "UAL1567", "SWA2290",
                     "DAL889", "N772TP", "N145RC", "JBU621", "AAL1203",
                     "FDX1508", "UPS2841"]

# ---------------------------------------------------------------- orbit model
ORBIT_RADIUS_KM = 1.4
ORBIT_POINTS = 40
ORBIT_ECC = 1.6         # racetrack, not a perfect circle
ADSB_JITTER_DEG = 0.0007  # ~ 60-70 m GPS/quantization noise
ORBIT_CADENCE_S = 15    # position cadence during the orbit
TRANSIT_CADENCE_S = 5   # real ADS-B ~ 1/sec; 5s keeps files sane but dense


def orbit_points(center_lat, center_lon, seed, n=ORBIT_POINTS,
                 r_km=ORBIT_RADIUS_KM, ecc=ORBIT_ECC, jitter=ADSB_JITTER_DEG):
    """A noisy racetrack orbit around a center. Deterministic per seed."""
    rng = random.Random(seed)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        dlat = (r_km / 111.0) * math.cos(a)
        dlon = (r_km / (111.0 * math.cos(math.radians(center_lat)))) * ecc * math.sin(a)
        pts.append((
            round(center_lat + dlat + rng.gauss(0, jitter), 6),
            round(center_lon + dlon + rng.gauss(0, jitter), 6),
        ))
    return pts


def km(a, b, c, d):
    return math.hypot((a - c) * 111.0, (b - d) * 111.0 * math.cos(math.radians(a)))


# ---------------------------------------------------------------- invariants
def assert_sane():
    """Fail the build loudly if any load-bearing property is violated."""
    # 1. target is NOT a decoy, and is >1 km from every decoy
    for name, (la, lo) in DECOY_SITES.items():
        d = km(TARGET_LAT, TARGET_LON, la, lo)
        assert d > 1.0, f"decoy {name} only {d:.2f} km from target (need >1 km)"

    # 2. target cell distinct from every decoy cell
    tcell = grid_cell(TARGET_LAT, TARGET_LON)
    for name, (la, lo) in DECOY_SITES.items():
        assert grid_cell(la, lo) != tcell, f"decoy {name} shares target cell"

    # 3. both orbits recover the target cell (fairness: single-orbit is enough)
    import statistics as st
    for seed in (1, 2):
        pts = orbit_points(TARGET_LAT, TARGET_LON, seed)
        c = (st.mean(p[0] for p in pts), st.mean(p[1] for p in pts))
        err = km(c[0], c[1], TARGET_LAT, TARGET_LON) * 1000
        assert err < 100, f"orbit seed {seed} centroid err {err:.0f} m too high"
        assert grid_cell(*c) == tcell, f"orbit seed {seed} misses target cell"

    # 4. herring C site is a real listed decoy
    assert HERRING_C_SITE in DECOY_SITES

    # 5. flag well-formed and its pieces are the planted ones
    assert FLAG == f"number{{{FRAG_A}{FRAG_B}_confirmed_{REGISTRY_SEGMENT}}}"

    # 6. neither fragment nor the flag word appears as a decoy site name
    for name in DECOY_SITES:
        assert FRAG_A not in name.lower() and FRAG_B not in name.lower()

    return True


if __name__ == "__main__":
    assert_sane()
    print("planted truth OK")
    print("  flag        :", FLAG)
    print("  target      :", (TARGET_LAT, TARGET_LON), "(UNLISTED)")
    print("  target cell :", cell_str(grid_cell(TARGET_LAT, TARGET_LON)))
    print("  fragments   :", FRAG_A, "/", FRAG_B, "/", REGISTRY_SEGMENT)
