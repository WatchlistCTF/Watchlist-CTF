# O250: Manifest (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{overwatch_confirmed_5a3f}
```

## In short

A week of aircraft position data. Two different aircraft circled the same spot on two different days. Find both, work out the centre of each circle, and look that location up in the grid registry to get a four-character segment. The rest of the flag is hidden in the aircraft's own transponder data: one word in the squawk codes, one in a callsign.

## Walkthrough

### Find the two aircraft

1. Load `fleet_week_20260914-20260920.json`. It holds 16 aircraft and tens of thousands of position points, so it has to be scripted.
2. For each aircraft, look for stretches where the heading sweeps through a full circle, or several.
3. Circling alone is not enough. Aircraft waiting to land circle too. The difference is height and steadiness: a holding pattern sits level at 6,000 to 7,000 feet, while surveillance orbits are low (under 5,000 feet) and the height keeps changing.
4. Two aircraft pass both tests: `DCA418` (a Gulfstream, hex `a01d31`) on the Monday, and `DCA522` (a Citation, hex `a02e42`) on the Thursday. Two others circle but stay level: `SKW2841` at 6,000 to 7,000 feet and `FDX1508` at 18,000. Those are ordinary holds, so drop them.

### Find the ground they watched

5. For each of the two, average the low-altitude points of the orbit to get its centre.
6. Both centres land within metres of each other. The spot is not listed in `sites.csv`. That file holds only decoys.
7. Round the location to the registry's grid and look it up in `registry.json`. Cell `47.620,-122.350` holds the segment `5a3f`. Every other cell holds `0000`.

### Get the words

8. Look at the squawk codes the two aircraft transmitted. Some are not standard codes. Squawk digits are octal. Decode the odd ones to text and they spell `over`.
9. One callsign field holds a hex-looking token. Decode it as ASCII and it spells `watch`.
10. Assemble the flag: `overwatch`, then `confirmed`, then the segment.

## Watch out for

- `number{5a3f}` on its own is not the flag. The registry gives you the segment, and the aircraft give you the words.
- The timestamps in the file are from a different year than the file name suggests. Work in days relative to the start of the window and do not trust calendar dates.
- A sloppy centre, or one taken from a single orbit, can land in the neighbouring grid cell, which returns `0000`. The two orbits' centres land about 40 m apart, and the combined point sits 2.37 km from the nearest listed site, so a careful centroid is unambiguous.
- The number in this challenge's ID is a label. It was worth 350 points.

## Solver

[`solve_o250.py`](solve_o250.py) does the whole path: finds the circular tracks, separates surveillance from holds by altitude, recovers each orbit centre, keys the grid cell into the registry for the segment, and decodes the two word fragments. It runs 10 checks.

- Unpack the challenge tar from [`../files/`](../files/) first, then run the script from the unpacked folder (or pass that folder as an argument).
- It needs only the Python 3 standard library. No network access or live server is needed.
- It knows no answers in advance. The segment, the two words and the aircraft all come out of the data, and only the final flag is compared with a fixed pattern.
- We also rebuilt all three data files from the original generator and got byte-for-byte identical output, and the solver passes 10 of 10 on both.
