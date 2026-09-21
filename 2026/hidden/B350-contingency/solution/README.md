# B350: Contingency (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
contingency{you_were_never_a_threat}
```

## In short

An off-board bonus. The word "contingency" keeps turning up in other challenges, always attached to something that failed or could not be reached. Follow it to a hidden page on the CTF site. The page shows a scrambled table. Put it in order, read off a recovery key, and the page unlocks the flag.

## Walkthrough

1. Collect the breadcrumbs:
   - [L100](../../../lab/L100-reduced-footprint/): a dormant `contingency.timer` that mentions `contingency.decima.cloud`.
   - [L200](../../../lab/L200-signal/): a DNS record saying the failover endpoint `/contingency` is unreachable.
   - [L300](../../../lab/L300-legion/): a noise packet with the same warning.
   - [F200](../../../forensics/F200-shadow-box/): the hidden script in the PDF calls home to `contingency.decima.cloud`.
   - [L400](../../../lab/L400-mission-creep/): the backdoor trigger word is `C0NT1NGENCY`.
2. The brief says "a page that answers when found" and "look where things go wrong". Try `/contingency` on the CTF site.
3. The page shows a RECONSTRUCTION table with 12 rows and three columns: NODE, SEG and CHK. The rows are out of order.
4. Sort the rows by NODE id, from `0x00` to `0x0B`.
5. Read down the SEG column in that order: `4e 4f 54 5f 41 5f 54 48 52 45 41 54`.
6. Convert each hex byte to a character. It spells `NOT_A_THREAT`.
7. Enter that as the recovery key. The sealed payload on the page decrypts and shows the flag.

## Watch out for

- The flag format here is `contingency{...}`, not `number{...}`.
- The page shows the flag in capitals. The board accepted it in any case.
- The table is useless until sorted. Reading SEG in the order shown gives gibberish.
