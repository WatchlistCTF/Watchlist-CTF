# T125 files

This challenge had no downloadable file. It ran against a live HTCPCP endpoint.

## To stand it up again

- A small HTTP service that speaks RFC 2324: it returns 418 to a browser or a wrong request, and pours the flag on a correct `BREW /pot-0` with `Content-Type: message/coffeepot` and body `start`.
- Build: `t125_htcpcp.py` is the server; `t125.service` runs it. It enforces a short per-IP cooldown.
- The server and unit file will live in this challenge's `build/` folder.
