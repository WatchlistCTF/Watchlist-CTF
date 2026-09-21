# T125 build

`t125_htcpcp.py` is the HTCPCP coffee-pot service: it returns 418 to a browser or a wrong request and pours the flag on a correct `BREW /pot-0` with `Content-Type: message/coffeepot` and body `start`. It rate-limits per IP. `t125.service` runs it under systemd; `test_brew.sh` exercises the correct and incorrect requests. The solver is in this challenge's `solution/`.
