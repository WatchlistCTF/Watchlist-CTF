# P250: Witness (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{AR-ETH-884213}
```

## In short

Pierce gives a confident statement with exact times. Check those times against the door badge records and Maya's email. The records put her at home and put him inside the building. The flag is the case reference on the ethics complaint she filed at the very minute he says he saw her.

## Walkthrough

1. Unzip the case file. It holds `pierce_statement.txt`, `access_control.sqlite`, `maya_mail.mbox` and `exhibit_A.jpg`.
2. Read the statement and write down anything you can check. Pierce says that on 13 March, at about 21:00, he saw Maya outside the facility, and that she sent a threat at 21:15.
3. Open the badge database and list Maya's events for that day. She badges out at 18:30 and never comes back. She could not have been there at 21:00.
4. List Pierce's events for the same day. He enters SL2-MAIN at 19:40 and leaves at 21:18. He was inside the whole time, during exactly the kind of access Maya had complained about.
5. Read Maya's mailbox. At 19:12 she emails her mother. At 20:03 a streaming service reports a sign-in from her home network. At 21:08 an ethics hotline confirms a complaint she filed at 21:07.
6. Look at the headers of that confirmation email. The `X-Case-Ref` header reads `AR-ETH-884213`. That whole value, not just the digits, is the flag.
7. For completeness, check Exhibit A with `exiftool`. Its modify date is 2026-03-14 01:22, which is after Pierce gave his statement. His proof was made afterwards.

## Watch out for

- The badge database holds tens of thousands of events. Filter by person and date.
- The flag is the exact header value, with its capital letters and dashes.
- Note what Pierce was doing between 19:40 and 21:18. [P450](../../P450-endgame/) picks it up.

## Solver

[`solve_p250.py`](solve_p250.py) walks the four steps and runs 11 checks: the falsifiable 21:00 claim, Maya's badge-out with no return, Pierce inside the restricted room, the case reference in the mail header, and the doctored exhibit.

- Unzip the case file from [`../files/`](../files/) first, then pass the folder to the script.
- Step 4 needs `exiftool` on the PATH. The rest is standard library. No network access or live server is needed.
- It reads the flag out of the `X-Case-Ref` header rather than assuming it, and checks the recovered value against the expected one.
