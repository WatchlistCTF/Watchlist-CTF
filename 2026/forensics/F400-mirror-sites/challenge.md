# F400: Mirror Sites

**Category:** Forensics · **Points:** 400

```text
[ FILE REF: DECIMA CLOUD SERVICES // CLIENT DATA FLOW - NORTHERN LIGHTS ]

A senior engineer at Decima Cloud Services moved a client dataset
out of the company and into a place it was never meant to go.
One Tuesday night. 23:43 to 02:17. Then they went home.

They were careful. The data did not leave in one step. It was
read in one cloud, staged in a second, mirrored into a third -
a personal tenant. No single provider saw the whole thing. Each
one logged a fragment and assumed the fragment was harmless.

Afterward, they cleaned up. They overwrote what they could and
deleted the rest. The current state of every bucket looks innocent.

I have all three logs. They do not agree. They do not even use
the same clock. But the data carried the same fingerprint into
every cloud it touched, and I do not forget a fingerprint.

Reconstruct the night. Prove it was one person, one object,
three clouds. Tell me what they took.

  - THE MACHINE

  Download: nl-incident-2026.tar.gz  (~180 MB)
```

## Files

Download: [`a093033e707206da.tar.gz`](files/a093033e707206da.tar.gz) (23.31 MB). Details in [`files/`](files/README.md).

Stuck? The walkthrough is in [`solution/`](solution/README.md). It contains the flag.
