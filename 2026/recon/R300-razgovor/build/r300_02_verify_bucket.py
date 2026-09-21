#!/usr/bin/env python3
"""
R300 Hop 2 - Script 2: Verify bucket contents
Checks all objects are publicly accessible without credentials

Usage:
    python3 02_verify_bucket.py
    (no AWS credentials needed - uses anonymous HTTP)
"""

import urllib.request
from xml.etree import ElementTree as ET

BUCKET  = "nl-relay-artifacts-7c2a"
REGION  = "us-east-2"
BASE    = f"https://{BUCKET}.s3.{REGION}.amazonaws.com"

EXPECTED_FILES = [
    "README.txt",
    "relay-cam-notes.txt",
    "checksums/media-sha256.txt",
    "media/relay-cam-0112.jpg",
    "media/relay-cam-0203.jpg",
    "media/relay-cam-0317.jpg",
    "media/relay-cam-0419.jpg",   # challenge image - should be ~99KB
    "media/relay-cam-0521.jpg",
    "media/relay-cam-0608.jpg",
    "media/relay-cam-0714.jpg",
    "media/relay-cam-0829.jpg",
    "media/relay-cam-0905.jpg",
    "media/relay-cam-1014.jpg",
    "media/relay-cam-1127.jpg",
    "media/relay-cam-1203.jpg",
    "logs/relay-4cf34e-2024-01.log",
    "logs/relay-4cf34e-2024-02.log",
    "logs/relay-4cf34e-2024-03.log",
    "logs/relay-7f3a2c-2023-10.log",
    "logs/relay-7f3a2c-2023-11.log",
    "logs/relay-141786-2023-12.log",
    "logs/relay-141786-2024-01.log",
    "logs/relay-2b8e91-2023-05.log",
    "logs/relay-2b8e91-2023-06.log",
    "logs/relay-a3f819-2022-12.log",
    "manifests/manifest-2023-11.json",
    "manifests/manifest-2023-12.json",
    "manifests/manifest-2024-01.json",
    "manifests/manifest-2024-02.json",
    "manifests/manifest-2024-03.json",
]

CHALLENGE_IMAGE_MIN_SIZE = 50_000  # real EXIF image should be ~99KB


def list_bucket():
    url = f"{BASE}/?list-type=2"
    with urllib.request.urlopen(url, timeout=15) as resp:
        xml = ET.parse(resp)
    ns  = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    objects = {}
    for obj in xml.findall(".//s3:Contents", ns):
        key  = obj.find("s3:Key", ns).text
        size = int(obj.find("s3:Size", ns).text)
        objects[key] = size
    return objects


def verify_challenge_image(objects):
    key  = "media/relay-cam-0419.jpg"
    size = objects.get(key, 0)
    if size < CHALLENGE_IMAGE_MIN_SIZE:
        print(f"  WARNING  {key} is only {size} bytes - still the placeholder!")
        print(f"           Run 03_upload_challenge_image.py to fix this.")
        return False
    print(f"  OK       {key} = {size:,} bytes (real EXIF image)")
    return True


def verify_notes_file():
    url = f"{BASE}/relay-cam-notes.txt"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            content = resp.read().decode()
        if "metadata intact" in content and "relay-cam-0419.jpg" in content:
            print("  OK       relay-cam-notes.txt - nudge file present and correct")
            return True
        print("  WARN     relay-cam-notes.txt - missing expected content")
        return False
    except Exception as e:
        print(f"  FAIL     relay-cam-notes.txt - {e}")
        return False


def main():
    print(f"\nVerifying s3://{BUCKET}/ (anonymous access)\n")

    try:
        objects = list_bucket()
    except Exception as e:
        print(f"FAIL: Could not list bucket - {e}")
        return

    print(f"Bucket contains {len(objects)} objects\n")

    all_ok   = True
    missing  = []
    present  = []

    for key in EXPECTED_FILES:
        if key in objects:
            present.append((key, objects[key]))
        else:
            missing.append(key)
            all_ok = False

    # Print all present files
    print("-- Object listing -----------------------------------------------")
    for key, size in sorted(present, key=lambda x: x[0]):
        flag = " <-- CHALLENGE IMAGE" if key == "media/relay-cam-0419.jpg" else ""
        print(f"  {size:>8,}  {key}{flag}")

    # Check missing
    if missing:
        print(f"\nMISSING ({len(missing)}):")
        for k in missing:
            print(f"  !! {k}")
        all_ok = False

    print()
    # Check challenge image size
    img_ok = verify_challenge_image(objects)
    if not img_ok:
        all_ok = False

    # Check nudge file content
    notes_ok = verify_notes_file()
    if not notes_ok:
        all_ok = False

    # Extra objects (unexpected)
    expected_set = set(EXPECTED_FILES)
    extra = [k for k in objects if k not in expected_set]
    if extra:
        print(f"\nExtra objects (not in expected list):")
        for k in extra:
            print(f"  +  {k}")

    print("\n" + "=" * 65)
    if all_ok:
        print("ALL CHECKS PASSED - Hop 2 bucket is ready")
    else:
        print("ISSUES FOUND - see above")
    print("=" * 65)


if __name__ == "__main__":
    main()
