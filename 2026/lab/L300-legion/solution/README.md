# L300: Legion (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{a_hundred_faces_one_machine}
```

## In short

One capture, hundreds of machines talking to one hub. A hundred of them are implants that check in on a steady rhythm, and the rest is noise. Separate them by how regular their timing is, decode the token each implant sends, and submit all hundred to the board. The flag is released when the last one lights up.

## Walkthrough

1. Get a feel for the capture (`capinfos`). It holds about 34,000 packets from many sources.
2. Count packets per destination address. One address receives traffic from 366 different sources. That is the Samaritan hub. Most of those sources send only a handful of packets, too few to judge, so set them aside. About 145 send enough to measure.
3. Now split implants from noise. Real implants check in roughly every 30 seconds with a little jitter. Noise (time sync, DNS, keepalives) arrives at irregular intervals.
4. For each source, take the gaps between its packets and work out how much they vary compared to their average (the coefficient of variation: standard deviation divided by mean). The sources fall into two clear groups. 100 of them score between 0.05 and 0.12, a steady beat. The other 45 score between 0.43 and 0.64. Draw the line anywhere from 0.2 to 0.4 and exactly 100 sources pass.
5. Look at the payload those 100 send. It is unreadable until you XOR every byte with `0x5A`. After that, the first two bytes are a node number and the next sixteen are a token in the form country code plus hash, for example `DE-d91928d0`.
6. Write a short script that POSTs each token to the `/submit` endpoint given in the challenge. Doing this by hand is not realistic.
7. Keep the board open in a second terminal with `nc` and watch the countries light up one at a time.
8. At 100 out of 100 the board releases the flag.

## Watch out for

- This challenge needs a script. A hundred nodes across 34,000 packets is built to be out of reach by hand.
- Packet count alone does not separate implants from noise. Timing regularity does.
- Do not set the cut-off too loosely. At 0.5, four noise sources slip through. Their payloads decode to rubbish and the board rejects them as unknown tokens, so you lose nothing but time.
- The board checks what you send: a team name of up to 32 letters, digits, hyphens or underscores, and tokens shaped like `XX-xxxxxxxx`. It also limits each address to 120 requests every 10 seconds, so a script that fires everything at once should back off and retry when it gets a 429.
- One noise packet carries the text "failover endpoint /contingency unreachable". That is a breadcrumb toward the hidden challenge [B350](../../../hidden/B350-contingency/).

## Solver

[`solve_l300.py`](solve_l300.py) finds the hub, keeps the sources with a steady beat, decodes the 100 tokens and submits them.

- Run it with no arguments from this folder to decode the tokens from the capture in [`../files/`](../files/). That part works offline.
- To submit, give it the capture, the board's address and a team name. It backs off and retries if the board rate-limits it.
- It needs `scapy` and `numpy`.
- The event's board server was taken offline after the CTF. We tested the full run by starting the original server program on a local machine: the unchanged solver decoded 100 tokens from the released capture, the server accepted 100 of 100 and released the flag, and the text board showed the full map.
- It knows no answers in advance. It picks the hub and the beacons from the traffic, and only the final flag is compared with a fixed value.
