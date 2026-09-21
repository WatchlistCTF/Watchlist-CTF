"""
F400 - AWS generator.

AWS owns THE STAGING hop, the CloudTrail Data-Events blind spot, and the
versioning cover-up.

  cloudtrail/management_*.json.gz  -> BLIND (S3 object ops need Data Events; off)
  s3_server_access/access_*.log    -> WITNESS (REST.PUT.OBJECT / REST.GET.OBJECT)
  inventory/s3_inventory_versions.csv -> ETag (hex) + VersionId + IsLatest + mfrag

The cover-up: the real object is the NONCURRENT version (IsLatest=false) and
carries the real mfrag. The current version is benign with a junk mfrag.

Schema refs: docs.aws.amazon.com/AmazonS3/latest/userguide/LogFormat.html
             docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html
"""

import gzip
import json
import os
from datetime import datetime, timedelta
from datetime import timezone as tz

from common import (
    RNG, AWS_ACCOUNT, AWS_BUCKET_OWNER, AWS_PRINCIPAL, AWS_ROLE, AWS_STAGING_BUCKET,
    INSIDER_IP, MFRAG_AWS, S3_KEY,
    T_AWS_ASSUMEROLE, T_S3_GET, T_S3_OVERWRITE, T_S3_PUT,
    junk_mfrag, rand_dt, rand_hex, rand_ip, rand_key, rand_md5_digest, rand_ua,
    ts_clf, ts_iso,
)

# Management events ONLY. No object-level operations may appear here.
_MGMT_EVENTS = [
    ("sts.amazonaws.com", "AssumeRole"),
    ("s3.amazonaws.com", "CreateBucket"),
    ("s3.amazonaws.com", "PutBucketPolicy"),
    ("s3.amazonaws.com", "PutBucketVersioning"),
    ("s3.amazonaws.com", "PutBucketAcl"),
    ("s3.amazonaws.com", "ListBuckets"),
    ("s3.amazonaws.com", "GetBucketLocation"),
    ("iam.amazonaws.com", "CreateAccessKey"),
    ("iam.amazonaws.com", "AttachRolePolicy"),
    ("ec2.amazonaws.com", "RunInstances"),
    ("ec2.amazonaws.com", "DescribeInstances"),
    ("kms.amazonaws.com", "CreateKey"),
    ("logs.amazonaws.com", "CreateLogGroup"),
    ("cloudformation.amazonaws.com", "UpdateStack"),
]

_AWS_STAFF = [
    ("arn:aws:iam::481516234297:user/p.raman", "AIDA2QK4EXAMPLE01", "p.raman"),
    ("arn:aws:iam::481516234297:user/t.okafor", "AIDA2QK4EXAMPLE02", "t.okafor"),
    ("arn:aws:sts::481516234297:assumed-role/BuildAgent/ci", "AROA2QK4EXAMPLE03", "ci"),
    ("arn:aws:sts::481516234297:assumed-role/TerraformExec/tf", "AROA2QK4EXAMPLE04", "tf"),
    ("arn:aws:iam::481516234297:user/j.mendes", "AIDA2QK4EXAMPLE05", "j.mendes"),
]


def _ct_record(dt, arn, user_name, source, event_name, ip, ua, params=None, extra=None):
    rec = {
        "eventVersion": "1.09",
        "userIdentity": {
            "type": "AssumedRole" if ":assumed-role/" in arn else "IAMUser",
            "principalId": rand_hex(RNG, 21).upper(),
            "arn": arn,
            "accountId": AWS_ACCOUNT,
            "userName": user_name,
        },
        "eventTime": ts_iso(dt),
        "eventSource": source,
        "eventName": event_name,
        "awsRegion": "us-east-1",
        "sourceIPAddress": ip,
        "userAgent": ua,
        "requestParameters": params or {},
        "responseElements": None,
        "requestID": rand_hex(RNG, 16).upper(),
        "eventID": f"{rand_hex(RNG,8)}-{rand_hex(RNG,4)}-{rand_hex(RNG,4)}-{rand_hex(RNG,4)}-{rand_hex(RNG,12)}",
        "readOnly": event_name.startswith(("List", "Describe", "Get")),
        "eventType": "AwsApiCall",
        "managementEvent": True,
        "recipientAccountId": AWS_ACCOUNT,
        "eventCategory": "Management",
    }
    if extra:
        rec.update(extra)
    return rec


def gen_cloudtrail(out_dir, n_decoys, n_files=4):
    """Management-plane only. The staging setup is here; the data movement is not."""
    ct_dir = os.path.join(out_dir, "cloudtrail")
    os.makedirs(ct_dir, exist_ok=True)

    records = []

    # --- The insider's staging setup (visible, but no data ops) ---
    records.append(_ct_record(
        T_AWS_ASSUMEROLE, AWS_PRINCIPAL, "akessler", "sts.amazonaws.com", "AssumeRole",
        INSIDER_IP, "aws-cli/2.15.30 Python/3.11.8 Linux/6.5.0 exe/x86_64",
        params={"roleArn": f"arn:aws:iam::{AWS_ACCOUNT}:role/{AWS_ROLE}",
                "roleSessionName": "akessler"},
        extra={"responseElements": {"credentials": {
            "accessKeyId": "ASIA" + rand_hex(RNG, 16).upper(),
            "expiration": ts_iso(T_AWS_ASSUMEROLE + timedelta(hours=12))}}},
    ))
    records.append(_ct_record(
        T_AWS_ASSUMEROLE + timedelta(minutes=1), AWS_PRINCIPAL, "akessler",
        "s3.amazonaws.com", "CreateBucket", INSIDER_IP,
        "aws-cli/2.15.30 Python/3.11.8 Linux/6.5.0 exe/x86_64",
        params={"bucketName": AWS_STAGING_BUCKET,
                "Host": f"{AWS_STAGING_BUCKET}.s3.amazonaws.com"},
    ))
    records.append(_ct_record(
        T_AWS_ASSUMEROLE + timedelta(minutes=2), AWS_PRINCIPAL, "akessler",
        "s3.amazonaws.com", "PutBucketVersioning", INSIDER_IP,
        "aws-cli/2.15.30 Python/3.11.8 Linux/6.5.0 exe/x86_64",
        params={"bucketName": AWS_STAGING_BUCKET,
                "VersioningConfiguration": {"Status": "Enabled"}},
    ))
    records.append(_ct_record(
        T_AWS_ASSUMEROLE + timedelta(minutes=3), AWS_PRINCIPAL, "akessler",
        "s3.amazonaws.com", "PutBucketPolicy", INSIDER_IP,
        "aws-cli/2.15.30 Python/3.11.8 Linux/6.5.0 exe/x86_64",
        params={"bucketName": AWS_STAGING_BUCKET,
                "bucketPolicy": {"Version": "2012-10-17", "Statement": [
                    {"Effect": "Allow", "Principal": {"AWS": AWS_PRINCIPAL},
                     "Action": "s3:*", "Resource": f"arn:aws:s3:::{AWS_STAGING_BUCKET}/*"}]}},
    ))

    # --- Decoy management noise ---
    for _ in range(n_decoys):
        source, event = RNG.choice(_MGMT_EVENTS)
        arn, _pid, uname = RNG.choice(_AWS_STAFF)
        records.append(_ct_record(
            rand_dt(RNG), arn, uname, source, event, rand_ip(RNG), rand_ua(RNG),
            params={"bucketName": f"decima-{RNG.choice(['prod','stage','dev'])}-{RNG.randrange(10,99)}"}
            if source == "s3.amazonaws.com" else {},
        ))

    records.sort(key=lambda r: r["eventTime"])

    # CloudTrail delivers batches of gzipped {"Records":[...]} files.
    per = (len(records) + n_files - 1) // n_files
    for i in range(n_files):
        chunk = records[i * per:(i + 1) * per]
        if not chunk:
            continue
        name = (f"management_{AWS_ACCOUNT}_CloudTrail_us-east-1_"
                f"2026091{i}T0000Z_{rand_hex(RNG, 16)}.json.gz")
        payload = json.dumps({"Records": chunk}, separators=(",", ":")).encode()

        # gzip.open() stamps the CURRENT time into the gzip header, which makes the
        # artifact non-reproducible. Derive the mtime from the batch's own last
        # event instead: deterministic AND realistic (CloudTrail delivers shortly
        # after the events it contains).
        delivered = int(datetime.strptime(
            chunk[-1]["eventTime"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=tz.utc).timestamp()) + 300

        with open(os.path.join(ct_dir, name), "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw,
                               mtime=delivered) as gz:
                gz.write(payload)


# --------------------------------------------------------------------------
# S3 server access logs - THE WITNESS
# --------------------------------------------------------------------------
def _access_line(dt, bucket, requester, operation, key, uri, status, bytes_sent,
                 object_size, ip, ua, version_id="-"):
    return " ".join([
        AWS_BUCKET_OWNER,
        bucket,
        ts_clf(dt),
        ip,
        requester,
        rand_hex(RNG, 16).upper(),
        operation,
        key,
        f'"{uri}"',
        str(status),
        "-",
        str(bytes_sent),
        str(object_size),
        str(RNG.randrange(12, 900)),
        str(RNG.randrange(5, 120)),
        '"-"',
        f'"{ua}"',
        version_id,
        rand_hex(RNG, 40) + "=",
        "SigV4",
        "ECDHE-RSA-AES128-GCM-SHA256",
        "AuthHeader",
        f"{bucket}.s3.us-east-1.amazonaws.com",
        "TLSv1.3",
        "-",
        "-",
    ])


_ACCESS_OPS = [
    ("REST.GET.OBJECT", "GET"), ("REST.PUT.OBJECT", "PUT"),
    ("REST.HEAD.OBJECT", "HEAD"), ("REST.GET.BUCKET", "GET"),
    ("REST.DELETE.OBJECT", "DELETE"),
]


def gen_s3_access_logs(out_dir, planted_truth, n_decoys):
    acc_dir = os.path.join(out_dir, "s3_server_access")
    os.makedirs(acc_dir, exist_ok=True)

    rows = []

    # --- THE WITNESS: the stage-in (PUT), the read-back (GET), the overwrite ---
    rows.append((T_S3_PUT, _access_line(
        T_S3_PUT, AWS_STAGING_BUCKET, AWS_PRINCIPAL, "REST.PUT.OBJECT", S3_KEY,
        f"PUT /{S3_KEY} HTTP/1.1", 200, 0, planted_truth.size, INSIDER_IP,
        "aws-cli/2.15.30 Python/3.11.8 Linux/6.5.0 exe/x86_64",
        version_id=planted_truth.s3_version_real,
    )))
    rows.append((T_S3_GET, _access_line(
        T_S3_GET, AWS_STAGING_BUCKET, AWS_PRINCIPAL, "REST.GET.OBJECT", S3_KEY,
        f"GET /{S3_KEY} HTTP/1.1", 200, planted_truth.size, planted_truth.size,
        INSIDER_IP, "Boto3/1.34.51 md/Botocore#1.34.51 ua/2.0 os/linux#6.5.0 lang/python#3.11.8",
        version_id=planted_truth.s3_version_real,
    )))
    # The cover-up: overwrite with a benign file (creates the noncurrent version).
    rows.append((T_S3_OVERWRITE, _access_line(
        T_S3_OVERWRITE, AWS_STAGING_BUCKET, AWS_PRINCIPAL, "REST.PUT.OBJECT", S3_KEY,
        f"PUT /{S3_KEY} HTTP/1.1", 200, 0, planted_truth.benign_size, INSIDER_IP,
        "aws-cli/2.15.30 Python/3.11.8 Linux/6.5.0 exe/x86_64",
        version_id=planted_truth.s3_version_benign,
    )))

    # --- Decoy traffic ---
    for _ in range(n_decoys):
        dt = rand_dt(RNG)
        op, verb = RNG.choice(_ACCESS_OPS)
        key = rand_key(RNG)
        size = RNG.randrange(300, 6_000_000)
        arn, _pid, _u = RNG.choice(_AWS_STAFF)
        rows.append((dt, _access_line(
            dt, AWS_STAGING_BUCKET, arn, op, key, f"{verb} /{key} HTTP/1.1",
            RNG.choice([200, 200, 200, 200, 206, 304, 403, 404]),
            size if verb == "GET" else 0, size, rand_ip(RNG), rand_ua(RNG),
        )))

    rows.sort(key=lambda r: r[0])

    # S3 delivers access logs in many small time-stamped files; group per hour.
    files = {}
    for dt, line in rows:
        files.setdefault(dt.strftime("%Y-%m-%d-%H"), []).append(line)
    for stamp, lines in sorted(files.items()):
        path = os.path.join(acc_dir, f"access_{stamp}-00-00-{rand_hex(RNG, 16).upper()}.log")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")


# --------------------------------------------------------------------------
# S3 inventory with versions - the cover-up lives or dies here
# --------------------------------------------------------------------------
_INV_HEADER = ("Bucket,Key,VersionId,IsLatest,IsDeleteMarker,Size,LastModifiedDate,"
               "ETag,StorageClass,IsMultipartUploaded,ReplicationStatus,"
               "EncryptionStatus,ChecksumAlgorithm,x-amz-meta-mfrag")


def _inv_row(bucket, key, vid, is_latest, size, dt, etag, mfrag,
             storage_class="STANDARD", is_delete_marker="false"):
    return ",".join([
        bucket, f'"{key}"', vid, str(is_latest).lower(), is_delete_marker, str(size),
        f'"{ts_iso(dt)}"', f'"{etag}"', storage_class, "false", "", "SSE-S3", "CRC32",
        mfrag,
    ])


def gen_s3_inventory(out_dir, planted_truth, n_decoys):
    inv_dir = os.path.join(out_dir, "inventory")
    os.makedirs(inv_dir, exist_ok=True)
    rows = []

    # --- THE COVER-UP ---
    # Current version: benign, junk mfrag. Match this and you get the wrong fragment.
    rows.append(_inv_row(
        AWS_STAGING_BUCKET, S3_KEY, planted_truth.s3_version_benign, True,
        planted_truth.benign_size, T_S3_OVERWRITE, planted_truth.benign_md5_hex,
        junk_mfrag(RNG),
    ))
    # Noncurrent version: the REAL object. Matching ETag, REAL mfrag.
    rows.append(_inv_row(
        AWS_STAGING_BUCKET, S3_KEY, planted_truth.s3_version_real, False,
        planted_truth.size, T_S3_PUT, planted_truth.md5_hex, MFRAG_AWS,
    ))

    # --- Decoys, some with multiple versions so version-noise is normal ---
    for _ in range(n_decoys):
        key = rand_key(RNG)
        n_ver = RNG.choices([1, 1, 1, 2, 3], k=1)[0]
        for v in range(n_ver):
            rows.append(_inv_row(
                AWS_STAGING_BUCKET, key,
                "3sL4kqtJlcpXroDTDmJ" + rand_hex(RNG, 13), v == 0,
                RNG.randrange(300, 6_000_000), rand_dt(RNG),
                rand_md5_digest(RNG).hex(), junk_mfrag(RNG),
                storage_class=RNG.choice(["STANDARD", "STANDARD", "STANDARD_IA", "GLACIER_IR"]),
            ))

    RNG.shuffle(rows)
    with open(os.path.join(inv_dir, "s3_inventory_versions.csv"), "w") as f:
        f.write(_INV_HEADER + "\n")
        f.write("\n".join(rows) + "\n")


def generate(out_root, planted_truth, scale):
    out_dir = os.path.join(out_root, "aws")
    gen_cloudtrail(out_dir, scale["aws_cloudtrail"])
    gen_s3_access_logs(out_dir, planted_truth, scale["aws_access"])
    gen_s3_inventory(out_dir, planted_truth, scale["aws_objects"])
