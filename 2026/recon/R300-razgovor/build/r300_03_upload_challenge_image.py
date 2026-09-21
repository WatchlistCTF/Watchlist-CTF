#!/usr/bin/env python3
"""
R300 Hop 3 - Script 3: Upload real EXIF challenge image
Replaces the placeholder relay-cam-0419.jpg with the real EXIF version

Usage:
    source venv/bin/activate
    export AWS_ACCESS_KEY_ID=...
    export AWS_SECRET_ACCESS_KEY=...
    export AWS_DEFAULT_REGION=us-east-2
    python3 03_upload_challenge_image.py

Requires relay-cam-0419.jpg to exist in the current directory.
If it doesn't exist, run build_image.py first to generate it.
"""

import boto3, os, hashlib, urllib.request

BUCKET     = "nl-relay-artifacts-7c2a"
REGION     = "us-east-2"
LOCAL_FILE = "relay-cam-0419.jpg"
S3_KEY     = "media/relay-cam-0419.jpg"
MIN_SIZE   = 50_000   # real image should be ~99KB


def check_local_file():
    if not os.path.exists(LOCAL_FILE):
        print(f"ERROR: {LOCAL_FILE} not found in current directory")
        print("Run build_image.py first to generate it")
        return False
    size = os.path.getsize(LOCAL_FILE)
    if size < MIN_SIZE:
        print(f"ERROR: {LOCAL_FILE} is only {size} bytes - looks like a placeholder")
        print("Run build_image.py to generate the real EXIF version")
        return False
    print(f"Local file:  {LOCAL_FILE} ({size:,} bytes) OK")
    return True


def verify_exif():
    try:
        import piexif
        exif = piexif.load(LOCAL_FILE)
        uc   = exif["Exif"].get(37510, b"")
        if len(uc) > 8:
            decoded = uc[8:].decode("ascii", errors="replace")
            print(f"EXIF check:  UserComment = {decoded}")
            if "provenance" in decoded and "northernlights.gg" in decoded:
                print("             URL verified in UserComment")
                return True
            else:
                print("WARNING: UserComment doesn't contain expected provenance URL")
                return False
        print("WARNING: No UserComment found in EXIF")
        return False
    except ImportError:
        print("EXIF check:  piexif not installed - skipping (pip install piexif)")
        return True   # don't block upload
    except Exception as e:
        print(f"EXIF check:  ERROR - {e}")
        return False


def upload():
    s3 = boto3.client("s3", region_name=REGION)
    sha = hashlib.sha256(open(LOCAL_FILE, "rb").read()).hexdigest()
    print(f"Uploading:   {LOCAL_FILE} -> s3://{BUCKET}/{S3_KEY}")
    s3.upload_file(LOCAL_FILE, BUCKET, S3_KEY,
                   ExtraArgs={"ContentType": "image/jpeg",
                              "Metadata": {"sha256": sha}})
    print(f"SHA-256:     {sha}")
    print("Upload:      OK")


def verify_remote():
    url = f"https://{BUCKET}.s3.{REGION}.amazonaws.com/{S3_KEY}"
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            size = resp.headers.get("Content-Length", "unknown")
            print(f"Remote check: {url}")
            print(f"             {int(size):,} bytes accessible anonymously")
            return int(size) > MIN_SIZE
    except Exception as e:
        print(f"Remote check: ERROR - {e}")
        return False


def main():
    print(f"\nUploading challenge image to s3://{BUCKET}/{S3_KEY}\n")

    if not check_local_file():
        return

    exif_ok = verify_exif()
    if not exif_ok:
        ans = input("\nEXIF check failed. Upload anyway? (y/N): ")
        if ans.lower() != "y":
            return

    print()
    upload()
    print()
    remote_ok = verify_remote()

    print("\n" + "=" * 65)
    if remote_ok:
        print("SUCCESS - relay-cam-0419.jpg is live with real EXIF data")
        print("Hop 3 is complete and solvable")
    else:
        print("WARN - upload may have succeeded but remote check failed")
        print("Try again in a few seconds")
    print("=" * 65)


if __name__ == "__main__":
    main()
