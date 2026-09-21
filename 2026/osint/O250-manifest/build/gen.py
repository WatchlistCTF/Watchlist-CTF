#!/usr/bin/env python3
"""
O200 *Manifest* - generator.

Produces the three artifact files:
  fleet_week_20260914-20260920.json  - the haystack (~12 aircraft, 1 week)
  sites.csv                          - 8 decoy facilities (target is NOT here)
  registry.json                      - grid-cell -> segment (target cell live)

Deterministic under common.SEED => byte-reproducible.
"""

import argparse
import csv
import json
import math
import os
import random

import common as C


# ---------------------------------------------------------------- helpers
def _point(lat, lon, t_ms, callsign, hexid, alt, gs, track, squawk="1200",
           emergency="none", seen_pos=0.4):
    """One ADS-B position report, matching the airplanes.live / ADSBx v2 shape."""
    p = {
        "hex": hexid,
        "type": "adsb_icao",
        "flight": callsign.ljust(8),
        "alt_baro": alt,
        "alt_geom": alt + C.RNG.randint(50, 300) if isinstance(alt, int) else alt,
        "gs": round(gs, 1),
        "track": round(track % 360, 1),
        "baro_rate": C.RNG.choice([0, 0, 64, -64, 128, -128]),
        "squawk": squawk,
        "emergency": emergency,
        "category": "A2",
        "lat": lat,
        "lon": lon,
        "nic": 9,
        "rc": 75,
        "seen_pos": round(seen_pos, 3),
        "version": 2,
        "nac_p": 10,
        "nac_v": 2,
        "sil": 3,
        "sil_type": "perhour",
        "gva": 2,
        "sda": 3,
        "alert": 0,
        "spi": 0,
        "messages": C.RNG.randint(1000, 90000),
        "seen": round(C.RNG.uniform(0.1, 2.0), 1),
        "rssi": round(C.RNG.uniform(-20, -4), 1),
        "now": t_ms,
    }
    return p


def _leg(lat0, lon0, lat1, lon1, t0_ms, callsign, hexid, alt, cadence_s):
    """A straight transit leg between two points, sampled at cadence."""
    dist_km = C.km(lat0, lon0, lat1, lon1)
    gs = C.RNG.uniform(320, 460)  # knots
    dur_s = (dist_km / 1.852) / gs * 3600
    n = max(2, int(dur_s / cadence_s))
    track = math.degrees(math.atan2(lon1 - lon0, lat1 - lat0))
    pts = []
    for i in range(n + 1):
        f = i / n
        lat = lat0 + (lat1 - lat0) * f
        lon = lon0 + (lon1 - lon0) * f
        t = t0_ms + int(i * cadence_s * C.SEC_MS)
        pts.append(_point(round(lat, 6), round(lon, 6), t, callsign, hexid,
                          alt, gs, track))
    return pts, t0_ms + int(n * cadence_s * C.SEC_MS)


def _day_start_ms(day_offset, hour):
    return C.WEEK_START_MS + day_offset * C.DAY_MS + hour * C.HOUR_MS


# ---------------------------------------------------------------- fragment encoders
def squawk_sequence_for(fragment):
    """
    Encode a fragment as a run of squawk codes.
    Each char -> 3 octal digits (all 0-7, valid squawk digits); concatenate;
    repack into 4-digit squawk codes. Player reads squawks during the orbit,
    concatenates digits, regroups by 3, decodes octal -> ascii.
    """
    digits = "".join(format(ord(c), "03o") for c in fragment)
    # pad to a multiple of 4 with a sentinel '0' (decoder ignores trailing partial)
    while len(digits) % 4:
        digits += "0"
    return [digits[i:i + 4] for i in range(0, len(digits), 4)]


def swap_token_for(fragment):
    """Fragment B as a bare numeric callsign = hex of the word. Player hex-decodes."""
    return fragment.encode().hex().upper()


# ---------------------------------------------------------------- aircraft builders
def build_target_a(spec):
    """Monday: transit in, ORBIT (carrying squawk fragment), callsign swap, transit out."""
    hexid = spec["hex"]
    t = _day_start_ms(spec["day_offset"], spec["start_hour"])
    cs = spec["callsign_initial"]
    pts = []

    # transit into the area (from an origin airport, roughly)
    leg, t = _leg(47.90, -122.60, C.TARGET_LAT + 0.10, C.TARGET_LON - 0.08,
                  t, cs, hexid, 12000, C.TRANSIT_CADENCE_S)
    pts += leg

    # ORBIT over the target - low, variable altitude (surveillance profile).
    # Callsign swaps HERE (mid-trace); hex stays constant.
    swap_cs = spec.get("callsign_swap") or "N418DC"
    orbit = C.orbit_points(C.TARGET_LAT, C.TARGET_LON, seed=1)
    squawks = squawk_sequence_for(spec["squawk_fragment"])
    for i, (lat, lon) in enumerate(orbit):
        # altitude wanders 2200-3200 ft (low, non-level = watching the ground)
        alt = 2200 + int(400 * math.sin(i / 3.0)) + C.RNG.randint(-80, 80)
        track = (i / len(orbit)) * 360.0
        # lay the squawk fragment across the middle of the orbit
        sq = "1200"
        idx = i - 8
        if 0 <= idx < len(squawks):
            sq = squawks[idx]
        cs_here = cs if i < len(orbit) // 2 else swap_cs
        gs = C.RNG.uniform(140, 190)  # slow = orbiting
        t_pt = t + int(i * C.ORBIT_CADENCE_S * C.SEC_MS)
        pts.append(_point(lat, lon, t_pt, cs_here, hexid, alt, gs, track, squawk=sq))
    t += int(len(orbit) * C.ORBIT_CADENCE_S * C.SEC_MS)

    # transit out under the swapped callsign
    leg, t = _leg(C.TARGET_LAT + 0.02, C.TARGET_LON + 0.02, 47.20, -122.10,
                  t, swap_cs, hexid, 11000, C.TRANSIT_CADENCE_S)
    pts += leg
    return {"hex": hexid, "r": cs, "t": "GLF5", "trace": pts}


def build_target_b(spec):
    """Thursday: same target, different airframe/callsign; swap token = hex(fragB)."""
    hexid = spec["hex"]
    t = _day_start_ms(spec["day_offset"], spec["start_hour"])
    cs = spec["callsign_initial"]
    swap_cs = swap_token_for(spec["callsign_fragment"])   # "7761746368"
    pts = []

    leg, t = _leg(47.10, -122.05, C.TARGET_LAT - 0.09, C.TARGET_LON + 0.09,
                  t, cs, hexid, 13000, C.TRANSIT_CADENCE_S)
    pts += leg

    orbit = C.orbit_points(C.TARGET_LAT, C.TARGET_LON, seed=2)
    for i, (lat, lon) in enumerate(orbit):
        alt = 2400 + int(350 * math.sin(i / 3.5)) + C.RNG.randint(-80, 80)
        track = (i / len(orbit)) * 360.0
        cs_here = cs if i < len(orbit) // 2 else swap_cs
        gs = C.RNG.uniform(140, 190)
        t_pt = t + int(i * C.ORBIT_CADENCE_S * C.SEC_MS)
        pts.append(_point(lat, lon, t_pt, cs_here, hexid, alt, gs, track))
    t += int(len(orbit) * C.ORBIT_CADENCE_S * C.SEC_MS)

    leg, t = _leg(C.TARGET_LAT + 0.02, C.TARGET_LON - 0.02, 47.95, -122.55,
                  t, swap_cs, hexid, 12500, C.TRANSIT_CADENCE_S)
    pts += leg
    return {"hex": hexid, "r": cs, "t": "C560", "trace": pts}


def build_herring_c(spec):
    """Legit HOLDING pattern over a LISTED site: level, standard-rate, published fix."""
    hexid = spec["hex"]
    t = _day_start_ms(spec["day_offset"], spec["start_hour"])
    cs = spec["callsign_initial"]
    site_lat, site_lon = C.DECOY_SITES[spec["orbit_site"]]
    pts = []

    leg, t = _leg(48.10, -122.30, site_lat + 0.12, site_lon, t, cs, hexid,
                  8000, C.TRANSIT_CADENCE_S)
    pts += leg

    # holding pattern: LEVEL altitude (7000 exactly), steady - the tell that it's
    # air-traffic sequencing, NOT surveillance.
    hold = C.orbit_points(site_lat, site_lon, seed=3, r_km=2.2, ecc=2.4)
    for i, (lat, lon) in enumerate(hold):
        alt = 7000  # dead level
        track = (i / len(hold)) * 360.0
        gs = C.RNG.uniform(210, 230)  # holding speed, faster than a watch orbit
        t_pt = t + int(i * C.ORBIT_CADENCE_S * C.SEC_MS)
        pts.append(_point(lat, lon, t_pt, cs, hexid, alt, gs, track))
    t += int(len(hold) * C.ORBIT_CADENCE_S * C.SEC_MS)

    leg, t = _leg(site_lat, site_lon, 47.45, -122.30, t, cs, hexid, 6000,
                  C.TRANSIT_CADENCE_S)
    pts += leg
    return {"hex": hexid, "r": cs, "t": "E75L", "trace": pts}


def build_herring_d(spec):
    """Legit callsign change at a stopover - mimics the identity-swap tell only."""
    hexid = spec["hex"]
    t = _day_start_ms(spec["day_offset"], spec["start_hour"])
    cs1 = spec["callsign_initial"]
    cs2 = spec["callsign_swap"]
    pts = []
    leg, t = _leg(47.90, -122.60, 47.55, -122.30, t, cs1, hexid, 10000,
                  C.TRANSIT_CADENCE_S)
    pts += leg
    # ground stop (callsign changes here - new flight number, same airframe)
    t += 40 * C.MIN_MS
    leg, t = _leg(47.55, -122.30, 47.20, -121.90, t, cs2, hexid, 11000,
                  C.TRANSIT_CADENCE_S)
    pts += leg
    return {"hex": hexid, "r": cs1, "t": "B738", "trace": pts}


def build_herring_e(spec):
    """Coverage gap over water - mimics the transponder-gap tell only."""
    hexid = spec["hex"]
    t = _day_start_ms(spec["day_offset"], spec["start_hour"])
    cs = spec["callsign_initial"]
    pts = []
    leg, t = _leg(47.95, -122.55, 47.70, -122.90, t, cs, hexid, 9000,
                  C.TRANSIT_CADENCE_S)
    pts += leg
    # GAP: 22 minutes of no reports (over water, below coverage), then reappear
    t += 22 * C.MIN_MS
    leg, t = _leg(47.40, -123.20, 47.10, -123.40, t, cs, hexid, 9500,
                  C.TRANSIT_CADENCE_S)
    # bump seen_pos on reappearance to make the gap visible in-record
    leg[0]["seen_pos"] = 1320.0
    pts += leg
    return {"hex": hexid, "r": cs, "t": "A320", "trace": pts}


def build_routine(i, callsign):
    """A boring point-to-point transit somewhere in the metro that week."""
    hexid = C._hex(0x9000 + i)
    day = C.RNG.randint(0, 6)
    hour = C.RNG.randint(6, 20)
    t = _day_start_ms(day, hour)
    # random-ish endpoints around the metro
    lat0 = round(C.RNG.uniform(47.1, 48.1), 4)
    lon0 = round(C.RNG.uniform(-122.9, -122.0), 4)
    lat1 = round(C.RNG.uniform(47.1, 48.1), 4)
    lon1 = round(C.RNG.uniform(-122.9, -122.0), 4)
    alt = C.RNG.choice([9000, 10000, 12000, 15000, 18000, 21000])
    trace, _ = _leg(lat0, lon0, lat1, lon1, t, callsign, hexid, alt,
                    C.TRANSIT_CADENCE_S)
    # routine flights fly many legs across the week (real airframes are busy)
    n_extra = C.RNG.randint(20, 32)
    last = trace[-1]
    tt = last["now"] + C.RNG.randint(2, 12) * C.HOUR_MS
    for _ in range(n_extra):
        nlat = round(C.RNG.uniform(47.1, 48.1), 4)
        nlon = round(C.RNG.uniform(-122.9, -122.0), 4)
        more, tt = _leg(last["lat"], last["lon"], nlat, nlon, tt, callsign,
                        hexid, alt, C.TRANSIT_CADENCE_S)
        trace += more
        last = more[-1]
        tt = last["now"] + C.RNG.randint(3, 30) * C.HOUR_MS
    return {"hex": hexid, "r": callsign, "t": C.RNG.choice(["B738", "A320", "E75L", "C208"]),
            "trace": trace}


# ---------------------------------------------------------------- orchestration
def generate(out_dir):
    C.assert_sane()
    os.makedirs(out_dir, exist_ok=True)

    aircraft = [
        build_target_a(C.TARGET_A),
        build_target_b(C.TARGET_B),
        build_herring_c(C.HERRING_C),
        build_herring_d(C.HERRING_D),
        build_herring_e(C.HERRING_E),
    ]
    for i in range(C.N_ROUTINE):
        aircraft.append(build_routine(i, C.ROUTINE_CALLSIGNS[i]))

    # shuffle so target aircraft aren't first (deterministic under SEED)
    C.RNG.shuffle(aircraft)

    fleet = {
        "source": "adsb-metro-archive",
        "window_start": C.WEEK_START_MS,
        "window_end": C.WEEK_START_MS + 7 * C.DAY_MS,
        "aircraft_count": len(aircraft),
        "aircraft": aircraft,
    }
    fleet_path = os.path.join(out_dir, "fleet_week_20260914-20260920.json")
    with open(fleet_path, "w") as f:
        json.dump(fleet, f, separators=(",", ":"))

    # sites.csv - decoys only
    sites_path = os.path.join(out_dir, "sites.csv")
    with open(sites_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["site_code", "lat", "lon", "class"])
        for name, (la, lo) in sorted(C.DECOY_SITES.items()):
            w.writerow([name, la, lo, "ground-facility"])

    # registry.json - grid-cell -> segment. Target cell live; decoys -> 0000.
    tcell = C.grid_cell(C.TARGET_LAT, C.TARGET_LON)
    registry = {C.cell_str(tcell): {"segment": C.REGISTRY_SEGMENT}}
    # add decoy cells (each decoy site's own cell) all mapping to 0000
    for name, (la, lo) in C.DECOY_SITES.items():
        registry.setdefault(C.cell_str(C.grid_cell(la, lo)), {"segment": "0000"})
    # a handful of extra null cells around the metro so the target doesn't stand out
    for _ in range(30):
        la = round(C.RNG.uniform(47.1, 48.1), 4)
        lo = round(C.RNG.uniform(-122.9, -122.0), 4)
        registry.setdefault(C.cell_str(C.grid_cell(la, lo)), {"segment": "0000"})
    reg_path = os.path.join(out_dir, "registry.json")
    with open(reg_path, "w") as f:
        json.dump({"grid_q": C.GRID_Q, "note": "key = (round(lat/q)*q, round(lon/q)*q) as 'lat,lon' 3dp",
                   "cells": registry}, f, indent=2)

    return fleet_path, sites_path, reg_path, fleet


def _human(n):
    for u in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../build")
    args = ap.parse_args()
    fp, sp, rp, fleet = generate(args.out)
    npts = sum(len(a["trace"]) for a in fleet["aircraft"])
    print("[*] O200 Manifest generated")
    print(f"    aircraft : {fleet['aircraft_count']}")
    print(f"    points   : {npts:,}")
    print(f"    fleet    : {_human(os.path.getsize(fp))}  {fp}")
    print(f"    sites    : {os.path.getsize(sp)} B  {sp}")
    print(f"    registry : {os.path.getsize(rp)} B  {rp}")
    print(f"    flag     : {C.FLAG}")
