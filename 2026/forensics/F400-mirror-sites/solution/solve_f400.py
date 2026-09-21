#!/usr/bin/env python3
"""
F400 *Mirror Sites* - reference solver / answer key.

Walks the INTENDED 6-stage path against the shipped artifact and nothing else.
It deliberately does NOT import common.py -- it knows no planted value in
advance. If this recovers the flag, a player can too.

Usage:
  tar xzf ../files/a093033e707206da.tar.gz
  python3 solve_f400.py nl-incident-2026

Needs only the Python 3 standard library. No network access.

Stages:
  01 triage the obvious logs      -> confirm they are blind to data movement
  02 pivot to the witness logs    -> find the data ops
  03 fingerprint-match MD5        -> isolate the one object crossing 3 clouds
  04 stitch the timeline          -> relay order under skew / TZ
  05 recover the originals        -> S3 noncurrent + Azure soft-deleted
  06 assemble                     -> decode mfrags in relay order
"""

import base64
import csv
import glob
import gzip
import json
import os
import re
import sys
from datetime import datetime, timezone

PASS = 0
FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {label}" + (f": {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f": {detail}" if detail else ""))
    return cond


def b64_to_hex(s):
    try:
        raw = base64.b64decode(s, validate=True)
        return raw.hex() if len(raw) == 16 else None
    except Exception:
        return None


def load_json(path):
    with open(path) as f:
        return json.load(f)


def main(root):
    print("=" * 74)
    print(" F400 MIRROR SITES - reference solve")
    print("=" * 74)

    # ---------------------------------------------------------------- STAGE 01
    print("\n[STAGE 01] Triage the obvious logs (and hit the wall)")

    admin = load_json(os.path.join(root, "gcp/audit/admin_activity.json"))
    gcp_obj_ops = [e for e in admin
                   if ".objects." in e["protoPayload"]["methodName"]]
    check("GCP Admin Activity is blind to object ops", len(gcp_obj_ops) == 0,
          f"{len(admin)} entries, {len(gcp_obj_ops)} object ops")

    data_access = load_json(os.path.join(root, "gcp/audit/data_access.json"))
    gcs_reads = [e for e in data_access
                 if "storage" in e["protoPayload"]["serviceName"]]
    check("GCP Data Access exists but never covered GCS", len(gcs_reads) == 0,
          f"{len(data_access)} entries, {len(gcs_reads)} GCS")

    ct_events, ct_obj_ops = 0, 0
    for p in glob.glob(os.path.join(root, "aws/cloudtrail/*.json.gz")):
        with gzip.open(p, "rt") as f:
            for r in json.load(f)["Records"]:
                ct_events += 1
                if r["eventName"] in ("GetObject", "PutObject", "DeleteObject"):
                    ct_obj_ops += 1
    check("AWS CloudTrail is blind to S3 object ops", ct_obj_ops == 0,
          f"{ct_events} mgmt events, {ct_obj_ops} object ops")

    activity = load_json(os.path.join(root, "azure/activity/activity_log.json"))
    az_blob_ops = [e for e in activity
                   if re.search(r"blobServices/containers/blobs",
                                e["operationName"]["value"])]
    check("Azure Activity Log is blind to blob data ops", len(az_blob_ops) == 0,
          f"{len(activity)} entries, {len(az_blob_ops)} blob ops")

    # ---------------------------------------------------------------- STAGE 02
    print("\n[STAGE 02] Pivot to the witness logs")

    # GCS usage CSV - the read
    gcs_gets = []
    for p in sorted(glob.glob(os.path.join(root, "gcp/usage/storage_usage_*.csv"))):
        with open(p) as f:
            for row in csv.DictReader(f):
                if row["cs_operation"] == "GET_Object":
                    gcs_gets.append(row)
    check("GCS usage log contains object GETs", len(gcs_gets) > 0,
          f"{len(gcs_gets)} GET_Object rows")

    # S3 server access logs - the stage-in / read-back
    s3_ops = []
    for p in sorted(glob.glob(os.path.join(root, "aws/s3_server_access/access_*.log"))):
        with open(p) as f:
            for line in f:
                parts = line.split()
                if len(parts) > 8 and parts[7] in ("REST.PUT.OBJECT", "REST.GET.OBJECT"):
                    s3_ops.append(parts)
    check("S3 server access log contains object PUT/GET", len(s3_ops) > 0,
          f"{len(s3_ops)} object ops")

    # Azure StorageBlobLogs - the mirror
    az_ops = []
    for p in sorted(glob.glob(os.path.join(root, "azure/storage_logs/StorageBlobLogs_*.json"))):
        for e in load_json(p):
            if e["OperationName"] in ("PutBlob", "GetBlob"):
                az_ops.append(e)
    check("Azure StorageBlobLogs contains blob data ops", len(az_ops) > 0,
          f"{len(az_ops)} blob ops")

    # ---------------------------------------------------------------- STAGE 03
    print("\n[STAGE 03] Fingerprint-match MD5 across three dialects")

    gcs_inv = load_json(os.path.join(root, "gcp/inventory/gcs_objects_metadata.json"))
    gcs_by_hex = {}
    for o in gcs_inv:
        h = b64_to_hex(o.get("md5Hash", ""))
        if h:
            gcs_by_hex.setdefault(h, []).append(o)

    s3_rows = []
    with open(os.path.join(root, "aws/inventory/s3_inventory_versions.csv")) as f:
        for row in csv.DictReader(f):
            s3_rows.append(row)
    s3_by_hex = {}
    for r in s3_rows:
        h = r["ETag"].strip('"').lower()
        if re.fullmatch(r"[0-9a-f]{32}", h):
            s3_by_hex.setdefault(h, []).append(r)

    az_inv = load_json(os.path.join(root, "azure/inventory/blob_inventory.json"))
    az_by_hex = {}
    for b in az_inv:
        h = b64_to_hex(b.get("Content-MD5", ""))
        if h:
            az_by_hex.setdefault(h, []).append(b)

    common_hex = set(gcs_by_hex) & set(s3_by_hex) & set(az_by_hex)
    check("exactly ONE object matches across all three clouds", len(common_hex) == 1,
          f"GCS={len(gcs_by_hex)} S3={len(s3_by_hex)} AZ={len(az_by_hex)} "
          f"-> intersection={len(common_hex)}")
    if len(common_hex) != 1:
        print("\n  cannot continue: the join is not unique")
        return finish()

    digest = common_hex.pop()
    g_obj = gcs_by_hex[digest][0]
    s3_vers = s3_by_hex[digest]
    az_blob = az_by_hex[digest][0]
    print(f"    digest      : {digest}")
    print(f"    GCS  name   : {g_obj['name']}")
    print(f"    S3   key    : {s3_vers[0]['Key']}")
    print(f"    Azure name  : {az_blob['Name']}")
    check("the object was renamed at every hop (names cannot join it)",
          len({os.path.basename(g_obj['name']),
               os.path.basename(s3_vers[0]['Key']),
               os.path.basename(az_blob['Name'])}) == 3)

    # crc32c red herring
    crc_in_others = any("crc32c" in json.dumps(x).lower()
                        for x in (s3_rows[:50] + az_inv[:50]))
    check("crc32c is GCP-only (unusable as a join)",
          "crc32c" in g_obj and not crc_in_others)

    # ---------------------------------------------------------------- STAGE 04
    print("\n[STAGE 04] Stitch the timeline under skew / TZ")

    md5_b64 = g_obj["md5Hash"]
    events = []

    # GCS usage: time_micros (epoch micros, UTC)
    for row in gcs_gets:
        if row["cs_object"] == g_obj["name"]:
            events.append(("GCP", "GCS GET_Object",
                           datetime.fromtimestamp(int(row["time_micros"]) / 1e6,
                                                  tz=timezone.utc)))
    # S3 access: CLF [16/Sep/2026:00:19:48 +0000]
    s3_key = s3_vers[0]["Key"]
    for parts in s3_ops:
        if parts[8] == s3_key:
            clf = (parts[2] + " " + parts[3]).strip("[]")
            dt = datetime.strptime(clf, "%d/%b/%Y:%H:%M:%S %z")
            events.append(("AWS", f"S3 {parts[7]}", dt))
    # Azure: ISO8601 UTC
    for e in az_ops:
        if e.get("ContentMD5") == md5_b64:
            dt = datetime.strptime(e["TimeGenerated"][:19], "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=timezone.utc)
            events.append(("Azure", f"Azure {e['OperationName']}", dt))

    events.sort(key=lambda x: x[2])
    print("    normalized to UTC:")
    for cloud, what, dt in events:
        print(f"      {dt.isoformat()}  {cloud:6} {what}")

    relay = []
    for cloud, _, _ in events:
        if cloud not in relay:
            relay.append(cloud)
    check("relay order derived from the timeline is GCP -> AWS -> Azure",
          relay == ["GCP", "AWS", "Azure"], " -> ".join(relay))
    check("the operation crosses midnight UTC",
          events[0][2].date() != events[-1][2].date(),
          f"{events[0][2].date()} -> {events[-1][2].date()}")

    # The portal-TZ trap: inventory renders local, and it hides the midnight crossing
    az_local = az_blob["Creation-Time"]
    check("Azure inventory renders portal-local time (the eyeball trap)",
          bool(re.search(r"[+-]\d{2}:\d{2}$", az_local)), az_local)

    # ---------------------------------------------------------------- STAGE 05
    print("\n[STAGE 05] Recover the originals (defeat the cover-up)")

    latest = [r for r in s3_rows if r["Key"] == s3_key and r["IsLatest"] == "true"]
    noncurrent = [r for r in s3_vers if r["IsLatest"] == "false"]
    check("S3 current version is the benign overwrite", len(latest) == 1
          and latest[0]["ETag"].strip('"').lower() != digest,
          f"current ETag={latest[0]['ETag'].strip(chr(34))}")
    check("S3 real object is the NONCURRENT version", len(noncurrent) == 1,
          f"VersionId={noncurrent[0]['VersionId']}")
    check("Azure blob is soft-deleted", az_blob.get("Deleted") is True)

    # ---------------------------------------------------------------- STAGE 06
    print("\n[STAGE 06] Assemble the fragments in relay order")

    frags = {
        "GCP": g_obj["metadata"]["mfrag"],
        "AWS": noncurrent[0]["x-amz-meta-mfrag"],
        "Azure": az_blob["Metadata"]["mfrag"],
    }
    junk = latest[0]["x-amz-meta-mfrag"]
    check("the S3 CURRENT version carries a junk mfrag (wrong path fails)",
          junk != frags["AWS"],
          f"current={junk!r} vs noncurrent={frags['AWS']!r}")

    out = ""
    for cloud in relay:
        dec = base64.b64decode(frags[cloud]).decode()
        print(f"    {cloud:6} {frags[cloud]:30} -> {dec!r}")
        out += dec

    flag = "number{" + out + "}"
    print(f"\n    FLAG: {flag}")
    check("assembled flag matches the locked value",
          flag == "number{the_clouds_do_not_speak_to_each_other_but_we_do}")

    return finish()


def finish():
    print("\n" + "=" * 74)
    print(f" RESULT: {PASS}/{PASS+FAIL} checks passed")
    print("=" * 74)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "nl-incident-2026"
    sys.exit(main(root))
