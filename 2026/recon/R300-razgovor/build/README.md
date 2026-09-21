# R300 build

Rebuilds the four-hop chain.

- `nl-relay-tools.zip` is the seed repo. Its git history must carry a "scrubbed" commit that still names the S3 bucket (sanitized at HEAD).
- `r300_01_populate_bucket.py` / `r300_02_verify_bucket.py` fill and check the S3 bucket; `s3-enable.sh` makes it publicly listable.
- `r300_03_upload_challenge_image.py` uploads `relay-cam-0419.jpg`, whose EXIF User Comment points to the provenance endpoint.
- `flag_endpoint.py` is that endpoint; it returns the flag for the right node. `r300_04_verify_hops2_3.py` checks the chain end to end.

Fill in your own bucket, account and host; no live values are shipped.
