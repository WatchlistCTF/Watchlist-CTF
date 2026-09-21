#!/usr/bin/env python3
"""
R300 Hop 2 - Script 1: Populate S3 bucket
Uploads all decoy objects to nl-relay-artifacts-7c2a

Usage:
    source venv/bin/activate
    export AWS_ACCESS_KEY_ID=...
    export AWS_SECRET_ACCESS_KEY=...
    export AWS_DEFAULT_REGION=us-east-2
    python3 01_populate_bucket.py
"""

import boto3, json, hashlib, random, io, struct
from botocore.config import Config

BUCKET = "nl-relay-artifacts-7c2a"
REGION = "us-east-2"

s3 = boto3.client("s3", region_name=REGION,
                  config=Config(retries={"max_attempts": 3}))

def upload(key, body, content_type="application/octet-stream"):
    if isinstance(body, str):
        body = body.encode()
    s3.put_object(Bucket=BUCKET, Key=key, Body=body, ContentType=content_type)
    sha = hashlib.sha256(body).hexdigest()[:12]
    print(f"  uploaded  {key:<55} ({len(body):>7,} bytes)  sha={sha}")

def minimal_jpeg(width=640, height=480, seed=0):
    random.seed(seed)
    buf = io.BytesIO()
    buf.write(b"\xff\xd8")
    buf.write(b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")
    buf.write(b"\xff\xc0" + struct.pack(">H", 17) +
              struct.pack(">BHH", 8, height, width) +
              b"\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01")
    buf.write(b"\xff\xc4\x00\x1f\x00"
              b"\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00"
              b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b")
    buf.write(b"\xff\xdb\x00\x43\x00" + bytes([8] * 64))
    buf.write(b"\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00")
    buf.write(bytes(random.randint(0, 254) for _ in range(random.randint(800, 1200))))
    buf.write(b"\xff\xd9")
    return buf.getvalue()

def log_content(node_id, month):
    actions = [
        f"relay/{node_id}: heartbeat ok",
        f"relay/{node_id}: artifact sync initiated",
        f"relay/{node_id}: camera capture scheduled",
        f"relay/{node_id}: s3 upload complete",
        f"relay/{node_id}: checksum validation passed",
    ]
    lines = [f"# NL relay log - {node_id} - {month}"]
    for i in range(40):
        h = 6 + (i * 24 // 40)
        m, s = random.randint(0, 59), random.randint(0, 59)
        lvl = random.choice(["INFO"] * 6 + ["DEBUG"] * 3 + ["WARN"])
        lines.append(f"{month}T{h:02d}:{m:02d}:{s:02d}Z [{lvl}] {random.choice(actions)}")
    return "\n".join(lines) + "\n"

def manifest_content(month, nodes):
    artifacts = []
    for node in nodes:
        for i in range(random.randint(2, 4)):
            fname = f"relay-cam-{random.randint(100,999):04d}.jpg"
            artifacts.append({
                "node_id": node, "key": f"media/{fname}",
                "size": random.randint(140000, 250000),
                "sha256": hashlib.sha256((fname + month).encode()).hexdigest(),
                "captured": f"{month}-{random.randint(1,28):02d}T{random.randint(6,18):02d}:00:00Z",
                "status": "archived",
            })
    return json.dumps({
        "manifest_id": hashlib.md5(month.encode()).hexdigest()[:8],
        "generated": f"{month}-28T23:59:00Z",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }, indent=2)

def populate():
    print(f"\nPopulating s3://{BUCKET}/\n")
    nodes = ["relay-4cf34e","relay-7f3a2c","relay-141786","relay-2b8e91","relay-a3f819"]

    print("-- media/ -------------------------------------------------------")
    cam_ids = ["0112","0203","0317","0521","0608","0714","0829","0905","1014","1127","1203"]
    for i, cam_id in enumerate(cam_ids):
        upload(f"media/relay-cam-{cam_id}.jpg", minimal_jpeg(640, 480, seed=i+100), "image/jpeg")
    # Placeholder for challenge image - will be replaced by 03_upload_challenge_image.py
    upload("media/relay-cam-0419.jpg", minimal_jpeg(640, 400, seed=419), "image/jpeg")
    print("  NOTE: relay-cam-0419.jpg is a placeholder - run 03_upload_challenge_image.py next\n")

    print("-- logs/ --------------------------------------------------------")
    for node, month in [
        ("relay-4cf34e","2024-01"),("relay-4cf34e","2024-02"),("relay-4cf34e","2024-03"),
        ("relay-7f3a2c","2023-10"),("relay-7f3a2c","2023-11"),("relay-141786","2023-12"),
        ("relay-141786","2024-01"),("relay-2b8e91","2023-05"),("relay-2b8e91","2023-06"),
        ("relay-a3f819","2022-12"),
    ]:
        upload(f"logs/{node}-{month}.log", log_content(node, month), "text/plain")

    print("\n-- manifests/ ---------------------------------------------------")
    for month in ["2023-11","2023-12","2024-01","2024-02","2024-03"]:
        upload(f"manifests/manifest-{month}.json",
               manifest_content(month, random.sample(nodes, 3)), "application/json")

    print("\n-- checksums/ ---------------------------------------------------")
    lines = [f"{hashlib.sha256(f'relay-cam-{c}'.encode()).hexdigest()}  media/relay-cam-{c}.jpg"
             for c in cam_ids]
    upload("checksums/media-sha256.txt", "\n".join(lines) + "\n", "text/plain")

    print("\n-- root/ --------------------------------------------------------")
    upload("relay-cam-notes.txt", """# relay camera capture notes
# last updated: 2024-03-31

relay-cam-0419.jpg  --  field capture from relay-843481 (US-EAST-1)
                        captured 2023-04-19T03:30:00Z prior to decommission
                        metadata intact
                        verify before archiving -- processing notes embedded
                        assigned to: archival review queue

relay-cam-1127.jpg  --  routine monthly capture relay-4cf34e
relay-cam-0905.jpg  --  capture relay-7f3a2c (pre-decom)
relay-cam-1203.jpg  --  capture relay-141786 Q4 archive
""", "text/plain")

    upload("README.txt", """# nl-relay-artifacts
Artifact store for Northern Lights relay node captures.
Structure:
  media/        relay camera still captures (JPEG)
  logs/         per-node monthly operation logs
  manifests/    artifact manifests with checksums
  checksums/    SHA-256 verification files
Access: public read, authenticated write.
""", "text/plain")

    response = s3.list_objects_v2(Bucket=BUCKET)
    print(f"\nBucket total: {response.get('KeyCount', 0)} objects")
    print("Run 02_verify_bucket.py to confirm all objects are accessible")
    print("Run 03_upload_challenge_image.py to upload the real EXIF image")

if __name__ == "__main__":
    populate()
