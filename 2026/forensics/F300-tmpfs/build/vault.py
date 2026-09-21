#!/usr/bin/env python3
# Decima operative vault loader.
# Keeps the encrypted vault resident in memory. The full key is SPLIT so neither
# half alone is usable:
#     head -> process ENVIRONMENT  (VAULT_KEY_HEAD)
#     tail -> process COMMAND LINE (--keytail)
# The loader never combines them or decrypts; unlocking happens at the relay.
import os, time, argparse

ap = argparse.ArgumentParser(add_help=False)
ap.add_argument("--keytail", default="")
args, _ = ap.parse_known_args()

loc = os.environ.get("VAULT_LOC", "/tmp/.cache/.vault.enc")
key_head = os.environ.get("VAULT_KEY_HEAD", "")   # head half (env)
key_tail = args.keytail                            # tail half (argv)

# Load the encrypted vault into memory and KEEP THE DESCRIPTOR OPEN, so the
# bytes survive in RAM even after the file is unlinked from disk.
_fd = open(loc, "rb")
_blob = _fd.read()        # encrypted bytes resident in anonymous memory

# Vault stays loaded but locked.
while True:
    time.sleep(3600)
