# F100 build

Regenerates the USB image players download.

- `build-f100.sh` builds a 300 MB FAT32 image with a detective's realistic backup (cases, family photos, school papers), then deletes five files: two carry the split flag, three are decoys. Run on Linux with root (it uses a loopback mount).
- `test-f100.sh` checks the built image: the deleted files are recoverable, the decoys are present, and the two halves decode and combine to the flag.

The shipped download is this image, gzipped. The flag lives in the built files, not in the script's output.
