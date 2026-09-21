#!/usr/bin/env python3
"""
F400 *Mirror Sites* - build orchestrator.

  python3 build.py --scale smoke   # fast build for iteration (~4 MB)
  python3 build.py --scale full    # the shipped artifact (~180 MB uncompressed)

Deterministic: seeded RNG => identical bytes every run.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gen_aws
import gen_azure
import gen_gcp
from common import (
    AZURE_ACCOUNT, AZURE_CONTAINER, AZURE_PORTAL_TZ_LABEL, AZURE_TENANT,
    AWS_ACCOUNT, AWS_STAGING_BUCKET, FLAG, GCP_PROJECT, GCP_SRC_BUCKET,
    PlantedTruth,
)

SCALES = {
    "smoke": {
        "gcp_admin": 1000, "gcp_data_access": 100, "gcp_usage": 2500, "gcp_objects": 300,
        "aws_cloudtrail": 800, "aws_access": 2000, "aws_objects": 250,
        "azure_activity": 500, "azure_blob_logs": 1600, "azure_objects": 220,
    },
    # Tuned to land ~180 MB uncompressed (design doc: 150-200 MB), while keeping
    # the doc's stated floor of "50K+ GCP audit entries". Azure Activity entries
    # are enormous (~1.8 KB each), so that dial moves size the fastest.
    "full": {
        "gcp_admin": 50_000, "gcp_data_access": 2_000, "gcp_usage": 100_000,
        "gcp_objects": 6_000,
        "aws_cloudtrail": 30_000, "aws_access": 80_000, "aws_objects": 5_000,
        "azure_activity": 7_000, "azure_blob_logs": 48_000, "azure_objects": 4_500,
    },
}

README = f"""\
================================================================================
 NORTHERN LIGHTS // INCIDENT PACKAGE NL-2026-0916
 CLASSIFICATION: RELEVANT
================================================================================

A senior engineer at Decima Cloud Services moved a client dataset out of the
company and into a place it was never meant to go. One Tuesday night. Then they
went home.

They were careful. The data did not leave in one step. No single provider saw
the whole thing. Each one logged a fragment and assumed the fragment was
harmless.

Afterward, they cleaned up. The current state of every bucket looks innocent.

I have all three logs. They do not agree. They do not even use the same clock.
But the data carried the same fingerprint into every cloud it touched, and I do
not forget a fingerprint.

Reconstruct the night. Prove it was one person, one object, three clouds.
Tell me what they took.

  -- THE MACHINE

================================================================================
 COLLECTION NOTES
================================================================================

GCP
  project          : {GCP_PROJECT}
  bucket           : gs://{GCP_SRC_BUCKET}
  region           : us-central1
  audit/           : Cloud Audit Logs export (JSON array).
  usage/           : bucket usage & storage logs (CSV, one object per UTC day).
  inventory/       : Objects:list output, JSON.
  timestamps       : RFC3339, UTC.

AWS
  account          : {AWS_ACCOUNT}
  bucket           : s3://{AWS_STAGING_BUCKET}
  region           : us-east-1
  cloudtrail/      : CloudTrail delivery batches (gzip, {{"Records":[...]}}).
  s3_server_access/: S3 server access logs. Space-delimited; see AWS LogFormat.
  inventory/       : S3 Inventory (versions), CSV, enriched with HeadObject
                     user-metadata (x-amz-meta-*).
  timestamps       : CloudTrail = ISO8601 UTC.
                     Server access logs = [dd/Mon/yyyy:HH:MM:SS +0000].

AZURE
  tenant           : {AZURE_TENANT}
  storage account  : {AZURE_ACCOUNT}
  container        : {AZURE_CONTAINER}
  activity/        : Azure Activity Log export (JSON array).
  storage_logs/    : StorageBlobLogs, one object per UTC day.
  inventory/       : Blob inventory export, JSON.
  timestamps       : StorageBlobLogs = ISO8601 UTC.
                     Inventory export renders in the tenant's configured portal
                     timezone: {AZURE_PORTAL_TZ_LABEL}. Offsets are explicit.

--------------------------------------------------------------------------------
 Nothing was withheld from this package. Everything you need is inside it.
 Not everything inside it is true to the eye.
--------------------------------------------------------------------------------
"""


def human(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def dir_size(p):
    total = 0
    for root, _, files in os.walk(p):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", choices=list(SCALES), default="smoke")
    ap.add_argument("--out", default="../build")
    ap.add_argument("--tar", action="store_true", help="also produce the tarball")
    args = ap.parse_args()

    scale = SCALES[args.scale]
    root = os.path.abspath(args.out)
    stage = os.path.join(root, "nl-incident-2026")

    if os.path.exists(stage):
        shutil.rmtree(stage)
    os.makedirs(stage, exist_ok=True)

    t0 = time.time()
    print(f"[*] F400 Mirror Sites - build (scale={args.scale})")

    pt = PlantedTruth()
    pt.assert_sane()
    print(f"[*] planted object : {pt.size} B")
    print(f"[*]   md5 hex      : {pt.md5_hex}      (S3 ETag dialect)")
    print(f"[*]   md5 b64      : {pt.md5_b64}  (GCS md5Hash / Azure Content-MD5)")
    print(f"[*]   crc32c       : {pt.crc32c}                  (GCP-only red herring)")
    print(f"[*]   benign etag  : {pt.benign_md5_hex}      (S3 current version)")

    print("[*] generating GCP   ...", end="", flush=True)
    gen_gcp.generate(stage, pt, scale)
    print(" done")
    print("[*] generating AWS   ...", end="", flush=True)
    gen_aws.generate(stage, pt, scale)
    print(" done")
    print("[*] generating Azure ...", end="", flush=True)
    gen_azure.generate(stage, pt, scale)
    print(" done")

    with open(os.path.join(stage, "README.txt"), "w") as f:
        f.write(README)

    size = dir_size(stage)
    print(f"[*] staged: {human(size)} in {time.time()-t0:.1f}s -> {stage}")

    if args.tar:
        tarball = os.path.join(root, "nl-incident-2026.tar.gz")
        if os.path.exists(tarball):
            os.remove(tarball)
        print("[*] tarring ...", end="", flush=True)
        # Reproducible tarball: sorted member order, pinned mtimes/ownership, and
        # `gzip -n` so the gzip header carries no build timestamp or filename.
        with open(tarball, "wb") as out:
            tar = subprocess.Popen(
                ["tar", "--sort=name", "--mtime=2026-09-16 02:17:00 UTC",
                 "--owner=0", "--group=0", "--numeric-owner",
                 "-cf", "-", "-C", root, "nl-incident-2026"],
                stdout=subprocess.PIPE)
            gz = subprocess.Popen(["gzip", "-n", "-9"], stdin=tar.stdout, stdout=out)
            tar.stdout.close()
            gz.communicate()
            tar.wait()
        print(f" done -> {human(os.path.getsize(tarball))}")

    print(f"[*] flag: {FLAG}")


if __name__ == "__main__":
    main()
