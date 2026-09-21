# F400 build

`build.py` orchestrates the three per-cloud generators (`gen_aws.py`, `gen_azure.py`, `gen_gcp.py`) with shared config in `common.py`. It is seeded, so it reproduces the shipped tarball byte-for-byte.

```
python3 build.py --scale full     # the shipped ~180 MB dataset
python3 build.py --scale smoke     # a fast ~5 MB build for iteration
```

Needs `crc32c` and `openpyxl`. One object is planted across all three clouds with a matching MD5; the flag is three base64 fragments in its metadata.
