"""
F400 - Azure generator.

Azure owns THE MIRROR (destination), the Activity-Log blind spot, and the
soft-delete cover-up.

  activity/activity_log.json        -> BLIND (control plane only, never blob data ops)
  storage_logs/StorageBlobLogs_*.json -> WITNESS (PutBlob / GetBlob / DeleteBlob)
  inventory/blob_inventory.json     -> Content-MD5 (b64) + mfrag + Deleted=true

Two traps live here:
  1. the mirrored blob is SOFT-DELETED - absent from a normal listing
  2. the inventory renders times in the tenant's portal TZ (UTC-07:00), so the
     cross-midnight-UTC window reads as a tidy Sept-15 afternoon

Schema refs: learn.microsoft.com/azure/storage/blobs/monitor-blob-storage
             learn.microsoft.com/azure/storage/blobs/soft-delete-blob-overview
"""

import json
import os
from datetime import timedelta

from common import (
    RNG, AZURE_ACCOUNT, AZURE_BLOB, AZURE_CONTAINER, AZURE_SUB, AZURE_TENANT,
    AZURE_USER, INSIDER_IP, MFRAG_AZURE,
    T_AZURE_DELETE, T_AZURE_PUT,
    junk_mfrag, rand_dt, rand_hex, rand_ip, rand_key, rand_md5_digest, rand_ua,
    ts_azure_portal_local, ts_iso, ts_iso_ms,
)
import base64

RG = "nl-rg-01"
_RESOURCE_ID = (f"/subscriptions/{AZURE_SUB}/resourceGroups/{RG}"
                f"/providers/Microsoft.Storage/storageAccounts/{AZURE_ACCOUNT}")

# Control-plane operations ONLY. No blob data ops may appear here.
_ACTIVITY_OPS = [
    ("Microsoft.Storage/storageAccounts/write", "Create/Update Storage Account"),
    ("Microsoft.Storage/storageAccounts/listKeys/action", "List Storage Account Keys"),
    ("Microsoft.Authorization/roleAssignments/write", "Create role assignment"),
    ("Microsoft.Resources/deployments/write", "Create Deployment"),
    ("Microsoft.Network/networkSecurityGroups/write", "Create/Update NSG"),
    ("Microsoft.Compute/virtualMachines/write", "Create/Update Virtual Machine"),
    ("Microsoft.KeyVault/vaults/write", "Update Key Vault"),
    ("Microsoft.Storage/storageAccounts/blobServices/write", "Update Blob Service Properties"),
]

_AZ_STAFF = [
    "p.raman@northernlights.example",
    "svc-deploy@northernlights.example",
    "t.okafor@northernlights.example",
    "automation@northernlights.example",
]


def _activity_entry(dt, caller, op_value, op_localized, ip, status="Succeeded"):
    return {
        "authorization": {
            "action": op_value,
            "scope": _RESOURCE_ID,
        },
        "caller": caller,
        "channels": "Operation",
        "claims": {
            "aud": "https://management.core.windows.net/",
            "iss": f"https://sts.windows.net/{AZURE_SUB}/",
            "name": caller,
            "ipaddr": ip,
        },
        "correlationId": f"{rand_hex(RNG,8)}-{rand_hex(RNG,4)}-{rand_hex(RNG,4)}-{rand_hex(RNG,4)}-{rand_hex(RNG,12)}",
        "eventDataId": f"{rand_hex(RNG,8)}-{rand_hex(RNG,4)}-{rand_hex(RNG,4)}-{rand_hex(RNG,4)}-{rand_hex(RNG,12)}",
        "eventName": {"value": "EndRequest", "localizedValue": "End request"},
        "category": {"value": "Administrative", "localizedValue": "Administrative"},
        "eventTimestamp": ts_iso_ms(dt),
        "id": f"{_RESOURCE_ID}/events/{rand_hex(RNG,8)}/ticks/{RNG.randrange(10**18, 10**19)}",
        "level": "Informational",
        "operationId": f"{rand_hex(RNG,8)}-{rand_hex(RNG,4)}-{rand_hex(RNG,4)}-{rand_hex(RNG,4)}-{rand_hex(RNG,12)}",
        "operationName": {"value": op_value, "localizedValue": op_localized},
        "resourceGroupName": RG,
        "resourceProviderName": {"value": op_value.split("/")[0],
                                 "localizedValue": op_value.split("/")[0]},
        "resourceType": {"value": "/".join(op_value.split("/")[:2]),
                         "localizedValue": "/".join(op_value.split("/")[:2])},
        "resourceId": _RESOURCE_ID,
        "status": {"value": status, "localizedValue": status},
        "subStatus": {"value": "OK", "localizedValue": "OK (HTTP Status Code: 200)"},
        "submissionTimestamp": ts_iso_ms(dt + timedelta(milliseconds=RNG.randrange(50, 900))),
        "subscriptionId": AZURE_SUB,
        "tenantId": AZURE_SUB,
    }


def _write_array(path, entries):
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


def gen_activity_log(out_dir, n_decoys):
    """The insider's tenant setup is here. The mirror itself is not."""
    def entries():
        # --- The personal tenant being stood up, minutes before the mirror ---
        yield _activity_entry(
            T_AZURE_PUT - timedelta(minutes=22), AZURE_USER,
            "Microsoft.Storage/storageAccounts/write", "Create/Update Storage Account",
            INSIDER_IP,
        )
        yield _activity_entry(
            T_AZURE_PUT - timedelta(minutes=20), AZURE_USER,
            "Microsoft.Storage/storageAccounts/blobServices/write",
            "Update Blob Service Properties", INSIDER_IP,
        )
        yield _activity_entry(
            T_AZURE_PUT - timedelta(minutes=18), AZURE_USER,
            "Microsoft.Authorization/roleAssignments/write", "Create role assignment",
            INSIDER_IP,
        )
        yield _activity_entry(
            T_AZURE_PUT - timedelta(minutes=15), AZURE_USER,
            "Microsoft.Storage/storageAccounts/listKeys/action",
            "List Storage Account Keys", INSIDER_IP,
        )

        for _ in range(n_decoys):
            op_value, op_local = RNG.choice(_ACTIVITY_OPS)
            yield _activity_entry(
                rand_dt(RNG), RNG.choice(_AZ_STAFF), op_value, op_local, rand_ip(RNG),
                status=RNG.choice(["Succeeded"] * 9 + ["Failed"]),
            )

    _write_array(os.path.join(out_dir, "activity", "activity_log.json"), entries())


# --------------------------------------------------------------------------
# StorageBlobLogs - THE WITNESS
# --------------------------------------------------------------------------
def _blob_log(dt, op, blob, status, md5, size, ip, ua, identity, duration=None):
    uri = f"https://{AZURE_ACCOUNT}.blob.core.windows.net/{blob}"
    return {
        "TimeGenerated": ts_iso_ms(dt),
        "ResourceId": _RESOURCE_ID + "/blobServices/default",
        "Category": "StorageWrite" if op in ("PutBlob", "DeleteBlob") else "StorageRead",
        "OperationName": op,
        "CallerIpAddress": ip,
        "CorrelationId": f"{rand_hex(RNG,8)}-{rand_hex(RNG,4)}-{rand_hex(RNG,4)}-{rand_hex(RNG,4)}-{rand_hex(RNG,12)}",
        "Protocol": "HTTPS",
        "AuthenticationType": "OAuth",
        "RequesterObjectId": identity,
        "StatusCode": status,
        "StatusText": "Success" if status in (200, 201, 202) else "Failure",
        "DurationMs": duration or RNG.randrange(9, 800),
        "ServerLatencyMs": RNG.randrange(5, 300),
        "Uri": uri,
        "AccountName": AZURE_ACCOUNT,
        "ContentMD5": md5,
        "RequestBodySize": size if op == "PutBlob" else 0,
        "ResponseBodySize": size if op == "GetBlob" else 0,
        "UserAgentHeader": ua,
        "ObjectKey": f"/{AZURE_ACCOUNT}/{blob}",
    }


_BLOB_OPS = ["GetBlob", "GetBlob", "PutBlob", "GetBlobProperties", "ListBlobs", "DeleteBlob"]


def gen_storage_blob_logs(out_dir, planted_truth, n_decoys):
    log_dir = os.path.join(out_dir, "storage_logs")
    os.makedirs(log_dir, exist_ok=True)

    insider_oid = "c41f8a92-7b6e-4d13-9a05-8e2f1c60b7d4"
    rows = []

    # --- THE WITNESS: the mirror lands. Content-MD5 == the join key. ---
    rows.append((T_AZURE_PUT, _blob_log(
        T_AZURE_PUT, "PutBlob", AZURE_BLOB, 201, planted_truth.md5_b64,
        planted_truth.size, INSIDER_IP,
        "azure-storage-blob/12.19.0 Python/3.11.8 (Linux-6.5.0)", insider_oid,
        duration=2841,
    )))
    # --- The cover-up: soft delete ---
    rows.append((T_AZURE_DELETE, _blob_log(
        T_AZURE_DELETE, "DeleteBlob", AZURE_BLOB, 202, "", 0, INSIDER_IP,
        "azure-storage-blob/12.19.0 Python/3.11.8 (Linux-6.5.0)", insider_oid,
    )))

    # --- Decoy blob traffic ---
    for _ in range(n_decoys):
        dt = rand_dt(RNG)
        op = RNG.choice(_BLOB_OPS)
        blob = f"{AZURE_CONTAINER}/{rand_key(RNG)}"
        size = RNG.randrange(200, 5_000_000)
        rows.append((dt, _blob_log(
            dt, op, blob, RNG.choice([200, 200, 200, 201, 206, 404, 403]),
            base64.b64encode(rand_md5_digest(RNG)).decode() if op in ("PutBlob", "GetBlob") else "",
            size, rand_ip(RNG), rand_ua(RNG),
            f"{rand_hex(RNG,8)}-{rand_hex(RNG,4)}-{rand_hex(RNG,4)}-{rand_hex(RNG,4)}-{rand_hex(RNG,12)}",
        )))

    rows.sort(key=lambda r: r[0])

    files = {}
    for dt, row in rows:
        files.setdefault(dt.strftime("%Y%m%d"), []).append(row)
    for day, entries in sorted(files.items()):
        _write_array(os.path.join(log_dir, f"StorageBlobLogs_{day}.json"), entries)


# --------------------------------------------------------------------------
# blob_inventory.json - soft-delete cover-up + the portal-TZ trap
# --------------------------------------------------------------------------
def gen_blob_inventory(out_dir, planted_truth, n_decoys):
    """
    NOTE: times here render in the tenant's PORTAL timezone (UTC-07:00), which is
    how a portal-driven inventory export presents them. The offset is explicit -
    but an analyst who string-sorts or eyeballs will misread the window entirely.
    """
    def entries():
        # --- THE MIRRORED BLOB: soft-deleted, real Content-MD5, REAL mfrag ---
        yield {
            "Name": AZURE_BLOB,
            "Container": AZURE_CONTAINER,
            "AccountName": AZURE_ACCOUNT,
            "Blob-Type": "BlockBlob",
            "Content-Length": planted_truth.size,
            "Content-MD5": planted_truth.md5_b64,
            "Content-Type": "application/octet-stream",
            "Creation-Time": ts_azure_portal_local(T_AZURE_PUT),
            "Last-Modified": ts_azure_portal_local(T_AZURE_PUT),
            "Access-Tier": "Hot",
            "Deleted": True,
            "DeletionId": str(RNG.randrange(10**17, 10**18)),
            "Deleted-Time": ts_azure_portal_local(T_AZURE_DELETE),
            "Remaining-Retention-Days": 7,
            "Snapshot": "",
            "VersionId": "",
            "Metadata": {
                "mfrag": MFRAG_AZURE,
                "src": "staged",
            },
        }

        # --- Decoys: a few also soft-deleted, so Deleted=true isn't a giveaway ---
        for _ in range(n_decoys):
            deleted = RNG.random() < 0.06
            created = rand_dt(RNG)
            e = {
                "Name": f"{AZURE_CONTAINER}/{rand_key(RNG)}",
                "Container": AZURE_CONTAINER,
                "AccountName": AZURE_ACCOUNT,
                "Blob-Type": RNG.choice(["BlockBlob"] * 9 + ["AppendBlob"]),
                "Content-Length": RNG.randrange(200, 5_000_000),
                "Content-MD5": base64.b64encode(rand_md5_digest(RNG)).decode(),
                "Content-Type": RNG.choice([
                    "application/octet-stream", "text/csv", "application/json"]),
                "Creation-Time": ts_azure_portal_local(created),
                "Last-Modified": ts_azure_portal_local(created),
                "Access-Tier": RNG.choice(["Hot", "Hot", "Cool", "Archive"]),
                "Deleted": deleted,
                "Snapshot": "",
                "VersionId": "",
                "Metadata": {
                    "mfrag": junk_mfrag(RNG),
                    "src": RNG.choice(["ingest", "backup", "sync", "staged"]),
                },
            }
            if deleted:
                d = created + timedelta(hours=RNG.randrange(1, 60))
                e["DeletionId"] = str(RNG.randrange(10**17, 10**18))
                e["Deleted-Time"] = ts_azure_portal_local(d)
                e["Remaining-Retention-Days"] = RNG.randrange(1, 7)
            yield e

    _write_array(os.path.join(out_dir, "inventory", "blob_inventory.json"), entries())


def generate(out_root, planted_truth, scale):
    out_dir = os.path.join(out_root, "azure")
    gen_activity_log(out_dir, scale["azure_activity"])
    gen_storage_blob_logs(out_dir, planted_truth, scale["azure_blob_logs"])
    gen_blob_inventory(out_dir, planted_truth, scale["azure_objects"])
