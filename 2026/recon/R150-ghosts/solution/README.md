# R150: Ghosts (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{ghosts_leave_certificates}
```

## In short

Every HTTPS certificate issued by a public authority is written into public Certificate Transparency logs. Those logs list host names that were never linked from anywhere. Search them for the organisation's certificates, visit each host you find, and one of them is the relay that should be dark.

## Walkthrough

1. Start at `northernlights.gg`, as the brief says. The main site does not list any subdomains.
2. Search the Certificate Transparency logs for certificates issued to the organisation's hosts. `crt.sh` and the Cert Spotter API both work.
3. Ten host names come back, with prefixes like `relay-`, `feed-arc-` and `proc-node-`.
4. Visit all ten. Every one answers with a page, so the status code tells you nothing. The content is what differs.
5. Nine are decoys. Their status panels have every field blank, and the page uses amber and red colours.
6. One is alive: `relay-843481`. Its panel is filled in (relay id, region, decommission date), its colours are green, and it shows the flag.

## Watch out for

- Subdomain tools such as `subfinder` and `dnsx` get you to the same list. That is fair recon and gives the same result.
- You cannot guess the host name. The number is random, and the ledger is the intended way to learn it.
