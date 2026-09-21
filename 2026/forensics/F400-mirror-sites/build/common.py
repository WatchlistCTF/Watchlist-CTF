"""
F400 *Mirror Sites* - shared core / the planted truth.

Single source of truth for the cast, the object, the MD5 join key, the relay
timeline and the flag fragments. Every per-cloud generator imports from here so
the three clouds cannot drift out of agreement.

Reference: f400-mirror-sites-challenge.md (design doc, June 7)
"""

import base64
import hashlib
import io
import random
import struct
from datetime import datetime, timedelta, timezone

import crc32c

# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------
SEED = 20260919  # event date; keeps builds reproducible
RNG = random.Random(SEED)

# --------------------------------------------------------------------------
# THE FLAG (locked - see design doc note 1)
# --------------------------------------------------------------------------
FLAG = "number{the_clouds_do_not_speak_to_each_other_but_we_do}"

# One base64 fragment per cloud, assembled in RELAY order GCP -> AWS -> Azure.
MFRAG_GCP = "dGhlX2Nsb3Vkc19kb19ub3Rf"        # the_clouds_do_not_
MFRAG_AWS = "c3BlYWtfdG9fZWFjaF9vdGhlcl8="    # speak_to_each_other_
MFRAG_AZURE = "YnV0X3dlX2Rv"                  # but_we_do

# --------------------------------------------------------------------------
# THE CAST - one insider, three cloud identities
# --------------------------------------------------------------------------
INSIDER_NAME = "Adrian Kessler"
GCP_USER = "adrian.kessler@decima-cloud.example"
GCP_SA = "svc-dataflow-relay@decima-prod-8841.iam.gserviceaccount.com"
GCP_PROJECT = "decima-prod-8841"
GCP_SRC_BUCKET = "decima-clients-prod"

AWS_ACCOUNT = "481516234297"
AWS_ROLE = "DecimaDataOps"
AWS_PRINCIPAL = f"arn:aws:sts::{AWS_ACCOUNT}:assumed-role/{AWS_ROLE}/akessler"
AWS_STAGING_BUCKET = "ak-personal-staging"
AWS_BUCKET_OWNER = "7f3d1c9a2b845e60fa11d7c3e8b492a5f60c17d84b3e29a5c710f8d6b24e93af"

AZURE_TENANT = "northernlights.example"
AZURE_USER = "akessler@northernlights.example"
AZURE_SUB = "b3d21f47-9c05-4ea8-8f16-2d7c4a91e0b5"
AZURE_ACCOUNT = "nlmirror01"
AZURE_CONTAINER = "archive"

# The insider's home IP - the thread that ties the three clouds to one person.
INSIDER_IP = "203.0.113.47"

# --------------------------------------------------------------------------
# THE OBJECT - renamed at every hop, which is WHY the MD5 join is load-bearing
# --------------------------------------------------------------------------
GCS_KEY = "exports/2026/q4/nl_client_roster_2026Q4.xlsx"
S3_KEY = "staging/tmp/ds_0917.bin"
AZURE_BLOB = "archive/backup_final.dat"

# The benign file used to overwrite the S3 object (the cover-up).
S3_BENIGN_NOTE = b"placeholder - scratch space reclaimed\n"

# --------------------------------------------------------------------------
# THE TIMELINE (UTC) - Tuesday night 2026-09-15 23:43 -> 2026-09-16 02:17
# Crosses midnight UTC on purpose; the Azure portal renders it as an afternoon.
# --------------------------------------------------------------------------
AZURE_PORTAL_TZ = timezone(timedelta(hours=-7))  # (UTC-07:00) Pacific Daylight Time
AZURE_PORTAL_TZ_LABEL = "(UTC-07:00) Pacific Daylight Time"


def _t(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


# The relay, in true UTC order. Stage 04 must reproduce exactly this ordering.
T_SA_KEY_CREATE = _t("2026-09-15T23:43:11Z")   # GCP  admin_activity  (setup)
T_GCS_GET = _t("2026-09-15T23:51:02Z")         # GCP  usage CSV       (THE READ)
T_AWS_ASSUMEROLE = _t("2026-09-16T00:14:37Z")  # AWS  cloudtrail      (setup)
T_S3_PUT = _t("2026-09-16T00:19:48Z")          # AWS  access log      (THE STAGE)
T_S3_GET = _t("2026-09-16T01:33:20Z")          # AWS  access log      (read back)
T_AZURE_PUT = _t("2026-09-16T01:58:04Z")       # Azure blob log       (THE MIRROR)
T_S3_OVERWRITE = _t("2026-09-16T02:11:00Z")    # AWS  access log      (cover-up)
T_AZURE_DELETE = _t("2026-09-16T02:15:30Z")    # Azure blob log       (cover-up)
T_GCS_LOGGING_OFF = _t("2026-09-16T02:17:00Z") # GCP  admin_activity  (cover-up)

WINDOW_START = T_SA_KEY_CREATE
WINDOW_END = T_GCS_LOGGING_OFF

# Decoy activity is smeared across this whole span to bury the window.
DECOY_SPAN_START = _t("2026-09-14T00:00:00Z")
DECOY_SPAN_END = _t("2026-09-17T23:59:59Z")


# --------------------------------------------------------------------------
# Hash dialects - the join key, rendered three ways
# --------------------------------------------------------------------------
def md5_hex(b):
    return hashlib.md5(b).hexdigest()


def md5_b64(b):
    return base64.b64encode(hashlib.md5(b).digest()).decode()


def hex_to_b64(h):
    return base64.b64encode(bytes.fromhex(h)).decode()


def crc32c_b64(b):
    """GCS crc32c - Castagnoli, big-endian, base64. GCP-only = red herring."""
    return base64.b64encode(struct.pack(">I", crc32c.crc32c(b))).decode()


# --------------------------------------------------------------------------
# Timestamp dialects - four renderings, one instant
# --------------------------------------------------------------------------
def ts_gcp(dt):
    """RFC3339 with micros, UTC:  2026-09-16T01:12:07.482194Z"""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond:06d}Z"


def ts_iso(dt):
    """ISO8601 seconds, UTC:  2026-09-16T01:12:07Z"""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def ts_iso_ms(dt):
    """ISO8601 millis, UTC (Azure log analytics style)."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}0000Z"


def ts_clf(dt):
    """Apache/CLF, as S3 server access logs render it:  [16/Sep/2026:01:12:07 +0000]"""
    return dt.strftime("[%d/%b/%Y:%H:%M:%S +0000]")


def ts_azure_portal_local(dt):
    """Portal-local rendering with explicit offset - the eyeball trap."""
    return dt.astimezone(AZURE_PORTAL_TZ).strftime("%Y-%m-%dT%H:%M:%S%z")[:-2] + ":00"


def rand_dt(rng, start=DECOY_SPAN_START, end=DECOY_SPAN_END):
    span = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randrange(span), microseconds=rng.randrange(1000000))


# --------------------------------------------------------------------------
# Decoy machinery
# --------------------------------------------------------------------------
# Every decoy object carries an mfrag too, so bulk-decoding all metadata yields
# thousands of junk fragments (design doc, anti-shortcut row 2).
_JUNK_WORDS = [
    "relay", "sector", "archive", "north", "delta", "ingest", "shard", "vector",
    "tertiary", "cache", "mirror", "pivot", "trace", "beacon", "cluster", "quota",
    "staging", "handoff", "parcel", "segment", "epoch", "cursor", "bundle", "rollup",
    "checkpoint", "warm", "cold", "tier", "batch", "spool", "digest", "manifest",
]


def junk_mfrag(rng):
    """base64 of plausible word-salad - indistinguishable in shape from the real ones."""
    n = rng.randint(2, 4)
    s = "_".join(rng.choice(_JUNK_WORDS) for _ in range(n)) + "_"
    return base64.b64encode(s.encode()).decode()


_PREFIXES = [
    "exports/2026/q1", "exports/2026/q2", "exports/2026/q3", "exports/2026/q4",
    "logs/ingest", "logs/rollup", "backup/daily", "backup/weekly", "staging/tmp",
    "reports/finance", "reports/ops", "archive/2025", "archive/2026", "tmp/scratch",
    "datasets/raw", "datasets/curated", "media/render", "index/shards",
]
_STEMS = [
    "roster", "ledger", "manifest", "snapshot", "extract", "rollup", "audit",
    "inventory", "telemetry", "billing", "headcount", "payroll", "contacts",
    "sessions", "assets", "routes", "nodes", "segments",
]
_EXTS = ["csv", "json", "xlsx", "parquet", "bin", "dat", "gz", "log"]


def rand_key(rng):
    return (f"{rng.choice(_PREFIXES)}/{rng.choice(_STEMS)}_"
            f"{rng.randrange(1000, 9999)}.{rng.choice(_EXTS)}")


def rand_md5_digest(rng):
    return bytes(rng.randrange(256) for _ in range(16))


def rand_ip(rng):
    # RFC5737 / documentation ranges, plus plausible cloud egress
    pool = ["198.51.100.", "203.0.113.", "192.0.2.", "35.199.", "52.94.", "20.150."]
    p = rng.choice(pool)
    if p.count(".") == 3:
        return p + str(rng.randrange(1, 254))
    return p + f"{rng.randrange(1, 254)}.{rng.randrange(1, 254)}"


_UA = [
    "apitools gsutil/5.27 Python/3.11.4 (linux)",
    "google-cloud-sdk gcloud/462.0.1",
    "aws-cli/2.15.30 Python/3.11.8 Linux/6.5.0 exe/x86_64",
    "Boto3/1.34.51 md/Botocore#1.34.51 ua/2.0 os/linux#6.5.0 lang/python#3.11.8",
    "azure-storage-blob/12.19.0 Python/3.11.8 (Linux-6.5.0)",
    "Azure-Storage/12.19.0 (Python; Linux)",
    "python-requests/2.31.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
]


def rand_ua(rng):
    return rng.choice(_UA)


def rand_hex(rng, n):
    return "".join(rng.choice("0123456789abcdef") for _ in range(n))


# --------------------------------------------------------------------------
# The exfiltrated object's bytes - built once, hashed once, used everywhere.
# --------------------------------------------------------------------------
def build_client_roster_xlsx():
    """
    The real client dataset. A genuine xlsx so the MD5 is the MD5 of a real file.
    Deterministic: fixed rows + pinned zip timestamps => stable digest.
    """
    from openpyxl import Workbook

    wb = Workbook()

    # openpyxl stamps docProps/core.xml with datetime.now() by default, which makes
    # the bytes -- and therefore the MD5 join key -- different on every build.
    # Pin every property so the digest is reproducible across machines and runs.
    props = wb.properties
    props.creator = "Decima Cloud Services / data-platform"
    props.lastModifiedBy = "Decima Cloud Services / data-platform"
    props.created = datetime(2026, 9, 4, 11, 20, 0)
    props.modified = datetime(2026, 9, 4, 11, 20, 0)
    props.title = "Client Roster Q4 2026"
    props.revision = None

    ws = wb.active
    ws.title = "Q4_ROSTER"
    ws.append(["client_id", "designation", "surname", "given", "region", "tier", "status"])

    rng = random.Random(0xC0FFEE)
    surnames = ["Whistler", "Carrow", "Danforth", "Okonkwo", "Reyes-Lund", "Halloway",
                "Bertram", "Sung", "Ivanova", "Marchetti", "Farrow", "Delacroix",
                "Nakamura", "Oyelaran", "Petrov", "Sandoval", "Thackeray", "Vance"]
    givens = ["Marcus", "Elena", "Jonah", "Priya", "Tobias", "Ines", "Rafael", "Wen",
              "Astrid", "Curtis", "Naomi", "Emeka", "Sofia", "Dmitri", "Claire", "Owen"]
    regions = ["NA-EAST", "NA-WEST", "EMEA", "APAC", "LATAM"]

    for i in range(1, 641):
        ws.append([
            f"DC-{40000 + i}",
            f"{rng.randrange(100, 999)}-{rng.randrange(10, 99)}-{rng.randrange(1000, 9999)}",
            rng.choice(surnames),
            rng.choice(givens),
            rng.choice(regions),
            rng.choice(["GOLD", "SILVER", "BRONZE"]),
            rng.choice(["ACTIVE", "ACTIVE", "ACTIVE", "DORMANT"]),
        ])

    buf = io.BytesIO()
    wb.save(buf)
    raw = buf.getvalue()

    # Rewrite the zip with pinned timestamps so the digest is build-stable.
    #
    # openpyxl stamps docProps/core.xml with utcnow() inside save(), overriding
    # whatever we set on wb.properties. Normalising the XML here (rather than
    # relying on openpyxl internals) keeps the digest deterministic across
    # openpyxl versions. The MD5 IS the challenge's join key -- if it drifts,
    # every generated cloud disagrees and the challenge is unsolvable.
    import re
    import zipfile

    PINNED = "2026-09-04T11:20:00Z"

    src = zipfile.ZipFile(io.BytesIO(raw))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(src.namelist()):
            data = src.read(name)
            if name == "docProps/core.xml":
                text = data.decode()
                text = re.sub(
                    r"(<dcterms:(created|modified)[^>]*>)[^<]*(</dcterms:\2>)",
                    lambda m: m.group(1) + PINNED + m.group(3),
                    text,
                )
                data = text.encode()
            zi = zipfile.ZipInfo(name, date_time=(2026, 9, 15, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o600 << 16
            z.writestr(zi, data)
    return out.getvalue()


class PlantedTruth:
    """The one object, its digest, and the three dialects that must agree."""

    def __init__(self):
        self.obj_bytes = build_client_roster_xlsx()
        self.size = len(self.obj_bytes)

        self.md5_hex = md5_hex(self.obj_bytes)      # S3 ETag dialect
        self.md5_b64 = md5_b64(self.obj_bytes)      # GCS md5Hash / Azure Content-MD5
        self.crc32c = crc32c_b64(self.obj_bytes)    # GCP-only red herring

        # The benign overwrite (S3 current version) - different bytes, different ETag.
        self.benign_bytes = S3_BENIGN_NOTE
        self.benign_size = len(self.benign_bytes)
        self.benign_md5_hex = md5_hex(self.benign_bytes)

        # Version ids for the S3 cover-up
        self.s3_version_real = "3sL4kqtJlcpXroDTDmJ" + rand_hex(RNG, 13)
        self.s3_version_benign = "9vQ2mHfNbxWzYuKaPrT" + rand_hex(RNG, 13)

    def assert_sane(self):
        assert hex_to_b64(self.md5_hex) == self.md5_b64, "MD5 dialects disagree"
        assert self.md5_hex != self.benign_md5_hex, "cover-up ETag collides with real"
        frag = (base64.b64decode(MFRAG_GCP) + base64.b64decode(MFRAG_AWS)
                + base64.b64decode(MFRAG_AZURE)).decode()
        assert FLAG == "number{" + frag + "}", "fragments do not assemble to the flag"
        return True
