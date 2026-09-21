# L300 build

- `generate.py` and `write_pcap.py` build `intercept.pcap`: 100 implants beaconing on a steady rhythm to one hub, buried in irregular noise from hundreds more.
- `server.py` is the live board (hardened): it validates submissions, rate-limits per IP, lights a country map over a TCP board port, and releases the flag at 100 of 100. `answer.json` (token to country) and `board.json` (grid order) are its data.

The shipped download is `intercept.pcap`, already in this challenge's `files/`. The event's runtime log is deliberately not included.
