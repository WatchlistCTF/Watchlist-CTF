# L200 build

- `generate_l200.py` builds `intercept.pcap`: ten hours of ordinary DNS with the implant's TXT-chunked config and the enrolment channel folded in, plus SPF/ACME decoy traffic. Seeded, but the exact bytes depend on the build host's timezone (the shipped capture was built in US Eastern).
- `l200_worker.js` is the C2 worker that answered `/telemetry/sync?sid=...` with the config, and a standby decoy for a wrong sid.

The shipped download is `intercept.pcap`, already in this challenge's `files/`.
