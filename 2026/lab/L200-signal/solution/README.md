# L200: Signal (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{the_config_was_the_payload}
```

## In short

A full day of DNS traffic hides an implant. Its instructions came down as TXT records in five chunks. Those instructions name a server and say it needs a session id. The session id was sent separately, one character at a time, inside DNS names. Ask the server the same question the implant did, and it answers with the flag.

## Walkthrough

1. Open `intercept.pcap` in Wireshark or tshark. It holds about 16,000 packets, nearly all of them ordinary lookups.
2. Filter for TXT queries, which are rare in normal browsing. Most of what comes back is ordinary: mail sender records (SPF) and certificate checks (ACME). One name is neither, and it has about ten hits: `sync.relay-7f3a.rl7f3a.net`.
3. Look at the TXT answers. There are five, tagged `v1;1/5` through `v1;5/5`. Put them in order, join them and base64-decode the result.
4. You get a small Perl script: the implant's config. It names the command server (`https://l200-c2.xonnie.ai/telemetry/sync`) and says the request needs a `sid` value that comes from the "enrolment channel".
5. Find the enrolment channel. Filter for `enroll.rl7f3a.net`. Six lookups appear, each with a label made of one character and a sequence number: `a.00`, `7.01`, `f.02`, `3.03`, `c.04`, `1.05`.
6. Sort by the sequence number and read the characters in order. The session id is `a7f3c1`.
7. Request the server address with `?sid=a7f3c1`. It replies with JSON containing an `auth_token`.
8. Base64-decode the token. That is the flag.

## Watch out for

- The flag is not in the capture. Searching the file for `number{` or for the flag words finds nothing.
- A wrong session id gets a decoy reply with no flag.
- The malicious traffic is a handful of packets out of 16,000. Filtering by record type is what makes it visible.
- The SPF and ACME TXT records are a planted distraction. They are real-looking and carry nothing.
- The capture also holds nine small easter eggs for fans of the show. None of them is part of the solve.
- One of the records mentions a failover endpoint called `/contingency`. That is a breadcrumb toward the hidden challenge [B350](../../../hidden/B350-contingency/).

## Solver

[`solve_l200.py`](solve_l200.py) does all three parts: rebuilds the script from the TXT chunks, reads the session id from the enrolment lookups, and asks the C2 worker for the config. It runs 12 checks.

- Run it with no arguments from this folder. It reads the capture in [`../files/`](../files/).
- It needs `scapy` (`pip install scapy`).
- It takes the worker's address from the capture, the way a player does. The last step needs that worker to be live.
- If the worker is ever taken down, the script says so in capital letters and only shows what the worker would have returned. It does not pretend to have fetched a flag. Set `L200_ENDPOINT` to point it at a worker you deployed yourself.
