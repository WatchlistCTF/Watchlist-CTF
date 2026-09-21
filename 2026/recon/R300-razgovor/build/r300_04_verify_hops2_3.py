#!/usr/bin/env python3
"""
R300 Hops 2+3 - Script 4: Full verification
Tests the complete solve path for Hops 2 and 3

Usage:
    python3 04_verify_hops2_3.py
    (no AWS credentials needed - uses anonymous HTTP)

What it checks:
    1. Bucket is publicly listable
    2. All 30 expected objects present
    3. relay-cam-0419.jpg is the real EXIF image (not placeholder)
    4. relay-cam-notes.txt contains the nudge text
    5. EXIF UserComment contains the provenance URL
    6. Thumbnail is embedded (uncropped version)
    7. The full Hop 2->3 solve path works end to end
"""

import urllib.request, os, sys, tempfile
from xml.etree import ElementTree as ET

BUCKET    = "nl-relay-artifacts-7c2a"
REGION    = "us-east-2"
BASE      = f"https://{BUCKET}.s3.{REGION}.amazonaws.com"
EXPECTED_URL = "provenance: https://provenance.northernlights.gg/relay-export/"

results = []

def check(label, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((status, label, detail))
    icon = "[+]" if passed else "[!]"
    print(f"  {icon} {label}")
    if detail:
        print(f"      {detail}")
    return passed


def test_bucket_listing():
    print("\n-- Hop 2: S3 Bucket ------------------------------------------")
    try:
        url = f"{BASE}/?list-type=2"
        with urllib.request.urlopen(url, timeout=15) as resp:
            xml = ET.parse(resp)
        ns      = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
        objects = {obj.find("s3:Key", ns).text: int(obj.find("s3:Size", ns).text)
                   for obj in xml.findall(".//s3:Contents", ns)}

        check("Bucket publicly listable", True, f"{len(objects)} objects found")
        check("30 objects present", len(objects) == 30, f"found {len(objects)}/30")
        check("relay-cam-notes.txt present", "relay-cam-notes.txt" in objects)
        check("media/ folder has 12 files",
              sum(1 for k in objects if k.startswith("media/")) == 12)
        check("logs/ folder has 10 files",
              sum(1 for k in objects if k.startswith("logs/")) == 10)
        check("manifests/ folder present",
              sum(1 for k in objects if k.startswith("manifests/")) > 0)

        img_size = objects.get("media/relay-cam-0419.jpg", 0)
        check("relay-cam-0419.jpg is real image (not placeholder)",
              img_size > 50_000,
              f"{img_size:,} bytes {'OK' if img_size > 50_000 else '- run 03_upload_challenge_image.py'}")
        return objects
    except Exception as e:
        check("Bucket publicly listable", False, str(e))
        return {}


def test_notes_file():
    try:
        url = f"{BASE}/relay-cam-notes.txt"
        with urllib.request.urlopen(url, timeout=10) as resp:
            content = resp.read().decode()
        has_image = "relay-cam-0419.jpg" in content
        has_nudge = "metadata intact" in content
        has_embedded = "processing notes embedded" in content
        check("relay-cam-notes.txt references challenge image", has_image)
        check("relay-cam-notes.txt contains nudge ('metadata intact')", has_nudge)
        check("relay-cam-notes.txt mentions embedded notes", has_embedded)
    except Exception as e:
        check("relay-cam-notes.txt accessible", False, str(e))


def test_exif_image():
    print("\n-- Hop 3: EXIF Image -----------------------------------------")
    try:
        url = f"{BASE}/media/relay-cam-0419.jpg"
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
            with urllib.request.urlopen(url, timeout=30) as resp:
                tmp.write(resp.read())

        size = os.path.getsize(tmp_path)
        check("Image downloadable anonymously", True, f"{size:,} bytes")

        try:
            import piexif
            exif = piexif.load(tmp_path)

            # UserComment
            uc = exif["Exif"].get(37510, b"")
            if len(uc) > 8:
                decoded = uc[8:].decode("ascii", errors="replace")
                has_url = "northernlights.gg" in decoded and "relay-export" in decoded
                check("EXIF UserComment present", True, decoded[:80])
                check("UserComment contains provenance URL", has_url)
            else:
                check("EXIF UserComment present", False, "not found")

            # Camera metadata
            make  = exif["0th"].get(271, b"").decode("ascii", errors="replace")
            model = exif["0th"].get(272, b"").decode("ascii", errors="replace")
            check("Camera make/model in EXIF", bool(make), f"{make} / {model}")

            # Thumbnail
            thumb = exif.get("thumbnail")
            thumb_len = exif["1st"].get(514, 0) if "1st" in exif else 0
            check("Thumbnail embedded in EXIF", bool(thumb) or thumb_len > 0,
                  f"{thumb_len} bytes" if thumb_len else "present" if thumb else "missing")

            # DateTime
            dt = exif["0th"].get(306, b"").decode("ascii", errors="replace")
            check("DateTime in EXIF", bool(dt), dt)

        except ImportError:
            check("EXIF verification", False, "piexif not installed - pip install piexif")
        except Exception as e:
            check("EXIF parsing", False, str(e))

        os.unlink(tmp_path)

    except Exception as e:
        check("Image downloadable", False, str(e))


def test_solve_path():
    print("\n-- Solve path simulation ------------------------------------")
    print("  Simulating player discovering Hop 3 URL from image...\n")

    try:
        import piexif, tempfile, os
        url = f"{BASE}/media/relay-cam-0419.jpg"
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
            with urllib.request.urlopen(url, timeout=30) as resp:
                tmp.write(resp.read())

        exif = piexif.load(tmp_path)
        uc   = exif["Exif"].get(37510, b"")
        if len(uc) > 8:
            url_found = uc[8:].decode("ascii", errors="replace")
            correct   = EXPECTED_URL in url_found
            check("Player runs: exiftool relay-cam-0419.jpg | grep -i usercomment",
                  correct, f"Found: {url_found[:80]}")
            if correct:
                print(f"\n  Next hop URL: https://provenance.northernlights.gg/relay-export/")
                print("  Player now visits Hop 4 web app\n")
        os.unlink(tmp_path)
    except ImportError:
        print("  (piexif not installed - skipping solve path simulation)")
    except Exception as e:
        check("Solve path simulation", False, str(e))


def summary():
    print("\n" + "=" * 65)
    passed = sum(1 for s, _, _ in results if s == "PASS")
    failed = sum(1 for s, _, _ in results if s == "FAIL")
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        print("\nFailed checks:")
        for status, label, detail in results:
            if status == "FAIL":
                print(f"  [!] {label}")
                if detail:
                    print(f"      {detail}")
    else:
        print("ALL CHECKS PASSED - Hops 2 and 3 are fully operational")
    print("=" * 65)


if __name__ == "__main__":
    print("R300 Razgovor - Hop 2+3 Verification")
    print("=" * 65)
    objects = test_bucket_listing()
    if objects:
        test_notes_file()
        test_exif_image()
        test_solve_path()
    summary()
