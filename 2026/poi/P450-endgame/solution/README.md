# P450: Endgame (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{304771592}
```

## In short

Maya left an evidence cache that explains how to prove a nameless service account was really Pierce. Then an encrypted plan file opens with a key built from things you collected across all three challenges. The plan names Pierce and gives his designation number. That number is the flag.

## Walkthrough

### Tie the export to Pierce

1. Unzip the dossier. New items are `audit_export.log` (11 MB), `pierce_plan.enc` and an `evidence_cache` folder with `README.txt` and `note_meeting.txt`. The HR record, badge database and Exhibit A from the earlier challenges are included again.
2. Read the evidence cache. Maya explains that badge events and export requests are both signed with the same secret key, using HMAC-SHA256 cut to 16 characters. A badge signature covers the card id plus the timestamp. An export signature covers the account name plus the timestamp. She supplies the key and the timestamp that matters: `2026-03-13T19:40:33`.
3. Compute both signatures for that timestamp. Use Pierce's card id, `AR-304-77-1592`, for the badge and `svc_export_04` for the export.
4. The badge signature (`8bb15baca2401b57`) matches the session token on Pierce's 19:40 entry in the badge database. The export signature (`954698a53a1c93f9`) matches one line in the audit log.
5. Search the audit log for that signature. At the same second, `svc_export_04` ran a bulk export of the `northern_lights` dataset, 55,017 rows, to an outside relay. Same second, same key, his badge. The anonymous account was Pierce.

### Open the plan

6. `pierce_plan.enc` is AES-256-GCM. The first 12 bytes are the nonce and the rest is the ciphertext.
7. Build the key from three things joined with no separators: Maya's designation from P100 (`558247193`), the place (`SL2-MAIN`), and the SHA-256 of `exhibit_A.jpg` written as hex. Take the SHA-256 of that combined string. The result is the key.
8. Decrypt. The plan says Pierce intends to silence Maya at SL2-MAIN on 2026-03-20 at 21:00, the meeting from P100. It gives his designation: `304771592`.

## Watch out for

- Maya's number from P100 is not the answer here. It is an ingredient in the key. The brief says it plainly: not the number you started with, the right one.
- The three key ingredients are joined as plain text with nothing between them.
- The audit log is 11 MB. Search it. Do not read it.

## Solver

[`solve_p450.py`](solve_p450.py) runs the whole chain and checks 10 things: the exports isolated in the audit log, the device key from the evidence cache, the HMAC correlation that ties an export to Pierce's badge, the plan decrypted with the key built from the earlier challenges, and the anti-shortcut checks that the designation is nowhere in plain text.

- Unzip the dossier from [`../files/`](../files/) first, then pass the folder to the script.
- It needs the `cryptography` package and `pdftotext` (poppler) on the PATH. No network access or live server is needed.
- The correlation is done for real, not assumed. The README names one smoking-gun timestamp (2026-03-13T19:40:33); the script scans every export and stops at the first that co-signs with a restricted badge entry, and both routes recover the same card and the same designation.
