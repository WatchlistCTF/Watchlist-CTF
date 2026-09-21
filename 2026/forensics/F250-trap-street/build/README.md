# F250 build

Rebuilds the honeypot package and the flag oracle.

- `cowrie-install.md` sets up Cowrie on a host and injects the challenge filesystem.
- `cowrie_decima_fs.py` builds the fake filesystem (the operative's home, the personnel file).
- `decima_subject_register.xlsx` is the register shown in-scene.
- `build_canary.py` builds the canary spreadsheet, with the check-in URL hidden white-on-white.
- `worker.js` is the Cloudflare Worker that answers the canary check-in and returns the flag for the right id.
- `reset-cowrie-logs.sh` clears logs between runs.

The shipped download is the honeypot log/tty/downloads tree, not these scripts. Do not publish real capture logs that contain player data.
