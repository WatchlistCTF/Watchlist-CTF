# T125: RFC 2324 (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{the_machine_takes_it_black}
```

## In short

RFC 2324 is the Hyper Text Coffee Pot Control Protocol, an April Fools' standard from 1998. The coffee machine on the network really does follow it. Send it a proper request to brew and it pours the flag.

## Walkthrough

1. Visit the brew station address from the challenge in a browser. You get a landing page whose message mentions RFC 2324.
2. Read RFC 2324. To start a pot, you send a request with the method `BREW` (not GET or POST), the header `Content-Type: message/coffeepot`, and a body that says `start`.
3. A browser cannot send that, so use `curl`. Set the method to BREW, add the content type header, send `start` as the body, and address it to the pot, `/pot-0`.
4. The machine replies with the flag.

## Watch out for

- The wrong content type gets a 415 error with a hint.
- A body of `stop` in place of `start` gets a 400 error with a hint.
- Requests sent too quickly get a 429. Wait about three seconds between attempts.

## Solver

[`t125_solve.py`](t125_solve.py) does the three requests in order: the greeting, a wrong request that returns 418, and the proper `BREW /pot-0` that pours the flag.

- Point it at the endpoint: `python3 t125_solve.py https://t125.northernlights.gg`. With no argument it uses `http://127.0.0.1:8421`.
- Standard library only. The station enforces a 3-second per-IP cooldown, so the script waits between its requests.
- The event server is offline now. We tested the solver by running the original coffee-pot service (`t125_htcpcp.py`) locally: it walked 200, 418, then 200 and recovered the flag, and the wrong content type and wrong body returned 415 and 400 as RFC 2324 expects.
