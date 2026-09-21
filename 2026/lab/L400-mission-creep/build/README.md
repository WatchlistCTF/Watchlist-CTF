# L400 build

`build_l400.sh` builds the compromised-relay disk image: a webshell in the web logs, a malicious systemd timer beside a legitimate one, a trojaned `pkexec` with an XOR-hidden trigger, wiped login records, and a core dump in the exfil staging that holds the flag. `l400_cleanup.sh` tears the scenario down.

WARNING: the builder installs a live backdoor and forces a core dump on the machine it runs on. Run it only as root on a disposable, throwaway VM.

The shipped download (`L400-mission-creep.7z`) is on the `2026-files` release. The solver (`l400_solve.sh`) is in this challenge's `solution/`.
