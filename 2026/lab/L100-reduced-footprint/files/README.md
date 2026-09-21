# L100 files

This challenge had no downloadable file. It ran against a live SSH target.

## To stand it up again

A Cowrie SSH honeypot on a fresh Ubuntu host, presenting a fake filesystem for "node0447". Players log in as `investigator` on port 2222 and read the planted files.

- Build: the one-shot `build_l100.sh` installs Cowrie and injects the challenge filesystem (login `investigator`, hostname `node0447`).
- The planted files, the decoys and the encoded flag are all created by that script.
- The build script will live in this challenge's `build/` folder.
