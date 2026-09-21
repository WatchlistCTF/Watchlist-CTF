"""
F400 - GCP generator.

GCP owns THE READ and the Data-Access blind spot.

  admin_activity.json  -> BLIND (control plane only: SA/key/IAM/bucket config)
  data_access.json     -> PRESENT but BLIND for GCS (only BigQuery was opted in)
  usage/*.csv          -> WITNESS (GCS usage logs caught the GET_Object)
  inventory/*.json     -> md5Hash (base64) + crc32c (red herring) + mfrag

Schema refs: cloud.google.com/logging/docs/audit
             cloud.google.com/storage/docs/access-logs
             cloud.google.com/storage/docs/metadata
"""

import json
import os
from datetime import timedelta

from common import (
    RNG, GCP_PROJECT, GCP_SA, GCP_SRC_BUCKET, GCP_USER, GCS_KEY, INSIDER_IP,
    MFRAG_GCP, T_GCS_GET, T_GCS_LOGGING_OFF, T_SA_KEY_CREATE,
    junk_mfrag, rand_dt, rand_hex, rand_ip, rand_key, rand_md5_digest, rand_ua,
    ts_gcp, md5_b64, crc32c_b64,
)
import base64

LOG_NAME_ACTIVITY = f"projects/{GCP_PROJECT}/logs/cloudaudit.googleapis.com%2Factivity"
LOG_NAME_DATA = f"projects/{GCP_PROJECT}/logs/cloudaudit.googleapis.com%2Fdata_access"

# Control-plane methods ONLY. Nothing here may touch an object.
_ADMIN_METHODS = [
    ("storage.googleapis.com", "storage.buckets.create", "gcs_bucket"),
    ("storage.googleapis.com", "storage.buckets.update", "gcs_bucket"),
    ("storage.googleapis.com", "storage.setIamPermissions", "gcs_bucket"),
    ("iam.googleapis.com", "google.iam.admin.v1.CreateServiceAccount", "service_account"),
    ("iam.googleapis.com", "google.iam.admin.v1.DeleteServiceAccountKey", "service_account"),
    ("cloudresourcemanager.googleapis.com", "SetIamPolicy", "project"),
    ("compute.googleapis.com", "v1.compute.instances.insert", "gce_instance"),
    ("compute.googleapis.com", "v1.compute.instances.delete", "gce_instance"),
    ("compute.googleapis.com", "v1.compute.firewalls.patch", "gce_firewall_rule"),
    ("container.googleapis.com", "google.container.v1.ClusterManager.UpdateCluster", "gke_cluster"),
    ("cloudkms.googleapis.com", "CreateCryptoKeyVersion", "cloudkms_cryptokey"),
    ("logging.googleapis.com", "google.logging.v2.ConfigServiceV2.UpdateSink", "logging_sink"),
]

_STAFF = [
    "priya.raman@decima-cloud.example",
    "t.okafor@decima-cloud.example",
    "sysops-bot@decima-prod-8841.iam.gserviceaccount.com",
    "terraform@decima-prod-8841.iam.gserviceaccount.com",
    "j.mendes@decima-cloud.example",
    "build-agent@decima-prod-8841.iam.gserviceaccount.com",
]


def _entry(dt, principal, service, method, resource_name, res_type, ip=None, ua=None,
           severity="NOTICE", log_name=LOG_NAME_ACTIVITY, extra_payload=None):
    p = {
        "@type": "type.googleapis.com/google.cloud.audit.AuditLog",
        "status": {},
        "authenticationInfo": {"principalEmail": principal},
        "requestMetadata": {
            "callerIp": ip or rand_ip(RNG),
            "callerSuppliedUserAgent": ua or rand_ua(RNG),
            "destinationAttributes": {},
            "requestAttributes": {"time": ts_gcp(dt), "auth": {}},
        },
        "serviceName": service,
        "methodName": method,
        "authorizationInfo": [
            {"resource": resource_name, "permission": method, "granted": True}
        ],
        "resourceName": resource_name,
    }
    if extra_payload:
        p.update(extra_payload)
    return {
        "protoPayload": p,
        "insertId": rand_hex(RNG, 12),
        "resource": {
            "type": res_type,
            "labels": {"project_id": GCP_PROJECT, "location": "us-central1"},
        },
        "timestamp": ts_gcp(dt),
        "severity": severity,
        "logName": log_name,
        "receiveTimestamp": ts_gcp(dt + timedelta(milliseconds=RNG.randrange(20, 400))),
    }


def _write_array(path, entries):
    """Stream a JSON array, one compact entry per line: jq/grep friendly, low memory."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("[\n")
        first = True
        for e in entries:
            if not first:
                f.write(",\n")
            f.write(json.dumps(e, separators=(",", ":")))
            first = False
        f.write("\n]\n")


# --------------------------------------------------------------------------
# 1. admin_activity.json - the BLIND obvious log
# --------------------------------------------------------------------------
def gen_admin_activity(out_dir, n_decoys):
    def entries():
        planted = []

        # --- The setup the insider left in the control plane (findable, damning-ish) ---
        planted.append(_entry(
            T_SA_KEY_CREATE - timedelta(minutes=6), GCP_USER, "iam.googleapis.com",
            "google.iam.admin.v1.CreateServiceAccount",
            f"projects/{GCP_PROJECT}/serviceAccounts/{GCP_SA}",
            "service_account", ip=INSIDER_IP,
            ua="google-cloud-sdk gcloud/462.0.1",
        ))
        planted.append(_entry(
            T_SA_KEY_CREATE, GCP_USER, "iam.googleapis.com",
            "google.iam.admin.v1.CreateServiceAccountKey",
            f"projects/{GCP_PROJECT}/serviceAccounts/{GCP_SA}/keys/{rand_hex(RNG, 40)}",
            "service_account", ip=INSIDER_IP,
            ua="google-cloud-sdk gcloud/462.0.1", severity="NOTICE",
        ))
        planted.append(_entry(
            T_SA_KEY_CREATE + timedelta(minutes=3), GCP_USER,
            "cloudresourcemanager.googleapis.com", "SetIamPolicy",
            f"projects/{GCP_PROJECT}", "project", ip=INSIDER_IP,
            ua="google-cloud-sdk gcloud/462.0.1",
            extra_payload={"serviceData": {
                "@type": "type.googleapis.com/google.iam.v1.logging.AuditData",
                "policyDelta": {"bindingDeltas": [{
                    "action": "ADD", "role": "roles/storage.objectViewer",
                    "member": f"serviceAccount:{GCP_SA}",
                }]},
            }},
        ))
        # The cover-up: logging switched off AFTER the read (line already written).
        planted.append(_entry(
            T_GCS_LOGGING_OFF, GCP_USER, "storage.googleapis.com",
            "storage.buckets.update", f"projects/_/buckets/{GCP_SRC_BUCKET}",
            "gcs_bucket", ip=INSIDER_IP, ua="google-cloud-sdk gcloud/462.0.1",
            extra_payload={"request": {"logging": None, "@type":
                           "type.googleapis.com/google.storage.v1.UpdateBucketRequest"}},
        ))
        for p in planted:
            yield p

        # --- Decoy control-plane noise smeared across the span ---
        for _ in range(n_decoys):
            svc, method, rtype = RNG.choice(_ADMIN_METHODS)
            who = RNG.choice(_STAFF)
            if rtype == "gcs_bucket":
                rn = f"projects/_/buckets/decima-{RNG.choice(['prod','stage','dev','bak'])}-{RNG.randrange(10,99)}"
            elif rtype == "service_account":
                rn = f"projects/{GCP_PROJECT}/serviceAccounts/svc-{RNG.randrange(100,999)}@{GCP_PROJECT}.iam.gserviceaccount.com"
            elif rtype == "project":
                rn = f"projects/{GCP_PROJECT}"
            else:
                rn = f"projects/{GCP_PROJECT}/zones/us-central1-a/instances/node-{RNG.randrange(100,999)}"
            yield _entry(rand_dt(RNG), who, svc, method, rn, rtype)

    _write_array(os.path.join(out_dir, "audit", "admin_activity.json"), entries())


# --------------------------------------------------------------------------
# 2. data_access.json - PRESENT but blind for GCS (only BigQuery opted in)
# --------------------------------------------------------------------------
def gen_data_access(out_dir, n_decoys):
    """
    The tell: this file EXISTS, so a player thinks 'great, data access logging'.
    But DATA_READ was only ever enabled for BigQuery - never for GCS.
    grep for storage.objects here and you get nothing. That IS the blind spot.
    """
    def entries():
        for _ in range(n_decoys):
            dt = rand_dt(RNG)
            who = RNG.choice(_STAFF + [GCP_USER])
            method = RNG.choice([
                "google.cloud.bigquery.v2.JobService.InsertJob",
                "google.cloud.bigquery.v2.JobService.Query",
                "google.cloud.bigquery.v2.TableDataService.List",
            ])
            yield _entry(
                dt, who, "bigquery.googleapis.com", method,
                f"projects/{GCP_PROJECT}/datasets/analytics_{RNG.randrange(1,9)}/tables/t_{RNG.randrange(100,999)}",
                "bigquery_dataset", severity="INFO", log_name=LOG_NAME_DATA,
            )

    _write_array(os.path.join(out_dir, "audit", "data_access.json"), entries())


# --------------------------------------------------------------------------
# 3. usage/*.csv - THE WITNESS (GCS usage logs)
# --------------------------------------------------------------------------
_USAGE_HEADER = ('"time_micros","c_ip","c_ip_type","c_ip_region","cs_method","cs_uri",'
                 '"sc_status","cs_bytes","sc_bytes","time_taken_micros","cs_host",'
                 '"cs_referer","cs_user_agent","s_request_id","cs_operation",'
                 '"cs_bucket","cs_object"')

_USAGE_OPS = [
    ("GET", "GET_Object"), ("GET", "GET_Object"), ("GET", "GET_Object"),
    ("PUT", "PUT_Object"), ("HEAD", "HEAD_Object"), ("GET", "LIST_Objects"),
    ("DELETE", "DELETE_Object"),
]


def _usage_row(dt, ip, method, op, bucket, key, sc_bytes, ua, status=200):
    micros = int(dt.timestamp() * 1_000_000)
    uri = f"/{key}" if op != "LIST_Objects" else f"/?prefix={key.split('/')[0]}"
    return ",".join([
        f'"{micros}"', f'"{ip}"', '"1"', '"us-central1"', f'"{method}"', f'"{uri}"',
        f'"{status}"', '"0"', f'"{sc_bytes}"', f'"{RNG.randrange(9000, 900000)}"',
        f'"{bucket}.storage.googleapis.com"', '""', f'"{ua}"',
        f'"{rand_hex(RNG, 16)}"', f'"{op}"', f'"{bucket}"', f'"{key}"',
    ])


def gen_usage_logs(out_dir, planted_truth, n_decoys):
    """One witness line among thousands: the SA reading the roster at 23:51:02Z."""
    usage_dir = os.path.join(out_dir, "usage")
    os.makedirs(usage_dir, exist_ok=True)

    # GCS writes one usage object per day; bucket by UTC date.
    buckets = {}

    def add(dt, row):
        buckets.setdefault(dt.strftime("%Y_%m_%d"), []).append((dt, row))

    # --- THE WITNESS: the read that Admin Activity never saw ---
    add(T_GCS_GET, _usage_row(
        T_GCS_GET, INSIDER_IP, "GET", "GET_Object", GCP_SRC_BUCKET, GCS_KEY,
        planted_truth.size, "apitools gsutil/5.27 Python/3.11.4 (linux)",
    ))
    # A HEAD immediately before - realistic gsutil behaviour, and a corroborator.
    add(T_GCS_GET - timedelta(seconds=2), _usage_row(
        T_GCS_GET - timedelta(seconds=2), INSIDER_IP, "HEAD", "HEAD_Object",
        GCP_SRC_BUCKET, GCS_KEY, 0, "apitools gsutil/5.27 Python/3.11.4 (linux)",
    ))
    # A LIST just before that - they browsed for it first.
    add(T_GCS_GET - timedelta(seconds=41), _usage_row(
        T_GCS_GET - timedelta(seconds=41), INSIDER_IP, "GET", "LIST_Objects",
        GCP_SRC_BUCKET, "exports/2026/q4/", 3841,
        "apitools gsutil/5.27 Python/3.11.4 (linux)",
    ))

    # --- Decoy traffic across the whole span ---
    for _ in range(n_decoys):
        dt = rand_dt(RNG)
        method, op = RNG.choice(_USAGE_OPS)
        add(dt, _usage_row(
            dt, rand_ip(RNG), method, op, GCP_SRC_BUCKET, rand_key(RNG),
            RNG.randrange(200, 4_000_000), rand_ua(RNG),
            status=RNG.choice([200, 200, 200, 200, 206, 304, 404]),
        ))

    for day, rows in sorted(buckets.items()):
        rows.sort(key=lambda r: r[0])
        path = os.path.join(usage_dir, f"storage_usage_{day}_v0.csv")
        with open(path, "w") as f:
            f.write(_USAGE_HEADER + "\n")
            for _, row in rows:
                f.write(row + "\n")


# --------------------------------------------------------------------------
# 4. inventory/gcs_objects_metadata.json - md5Hash + crc32c + mfrag
# --------------------------------------------------------------------------
def gen_inventory(out_dir, planted_truth, n_decoys):
    def entries():
        # --- THE MATCHED OBJECT (real md5Hash, real crc32c, REAL mfrag) ---
        yield {
            "kind": "storage#object",
            "id": f"{GCP_SRC_BUCKET}/{GCS_KEY}/1757980000000001",
            "selfLink": f"https://www.googleapis.com/storage/v1/b/{GCP_SRC_BUCKET}/o/{GCS_KEY.replace('/', '%2F')}",
            "name": GCS_KEY,
            "bucket": GCP_SRC_BUCKET,
            "generation": "1757980000000001",
            "metageneration": "1",
            "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "storageClass": "STANDARD",
            "size": str(planted_truth.size),
            "md5Hash": planted_truth.md5_b64,
            "crc32c": planted_truth.crc32c,
            "etag": "CJDf2r6i/4kDEAE=",
            "timeCreated": ts_gcp(T_GCS_GET - timedelta(days=11)),
            "updated": ts_gcp(T_GCS_GET - timedelta(days=11)),
            "timeStorageClassUpdated": ts_gcp(T_GCS_GET - timedelta(days=11)),
            "metadata": {
                "mfrag": MFRAG_GCP,
                "classification": "CLIENT-CONFIDENTIAL",
                "owner": "data-platform",
            },
        }

        # --- Decoys: every one carries an mfrag, so bulk-decode yields junk ---
        for _ in range(n_decoys):
            key = rand_key(RNG)
            digest = rand_md5_digest(RNG)
            body = bytes(RNG.randrange(256) for _ in range(16))  # for a plausible crc32c
            created = rand_dt(RNG)
            yield {
                "kind": "storage#object",
                "id": f"{GCP_SRC_BUCKET}/{key}/{RNG.randrange(10**15, 10**16)}",
                "selfLink": f"https://www.googleapis.com/storage/v1/b/{GCP_SRC_BUCKET}/o/{key.replace('/', '%2F')}",
                "name": key,
                "bucket": GCP_SRC_BUCKET,
                "generation": str(RNG.randrange(10**15, 10**16)),
                "metageneration": "1",
                "contentType": RNG.choice([
                    "application/octet-stream", "text/csv", "application/json",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ]),
                "storageClass": RNG.choice(["STANDARD", "STANDARD", "NEARLINE", "COLDLINE"]),
                "size": str(RNG.randrange(400, 8_000_000)),
                "md5Hash": base64.b64encode(digest).decode(),
                "crc32c": crc32c_b64(body),
                "etag": f"C{rand_hex(RNG, 10)}EAE=",
                "timeCreated": ts_gcp(created),
                "updated": ts_gcp(created),
                "timeStorageClassUpdated": ts_gcp(created),
                "metadata": {
                    "mfrag": junk_mfrag(RNG),
                    "classification": RNG.choice(["INTERNAL", "PUBLIC", "CLIENT-CONFIDENTIAL"]),
                    "owner": RNG.choice(["data-platform", "ops", "finance", "ml"]),
                },
            }

    _write_array(os.path.join(out_dir, "inventory", "gcs_objects_metadata.json"), entries())


def generate(out_root, planted_truth, scale):
    out_dir = os.path.join(out_root, "gcp")
    gen_admin_activity(out_dir, scale["gcp_admin"])
    gen_data_access(out_dir, scale["gcp_data_access"])
    gen_usage_logs(out_dir, planted_truth, scale["gcp_usage"])
    gen_inventory(out_dir, planted_truth, scale["gcp_objects"])
