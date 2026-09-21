# L100 build

`build_l100.sh` installs Cowrie on a fresh Ubuntu host and injects the Node 0447 challenge filesystem: the login `investigator`, the decoys (a certbot cron, a login-banner script), and the real implant under a hidden systemd service whose script carries the base64 flag. Run as root.

The solver/checker (`l100_check.sh`) is in this challenge's `solution/` folder.
