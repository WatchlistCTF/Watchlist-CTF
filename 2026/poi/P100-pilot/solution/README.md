# P100: Pilot (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{558247193}
```

## In short

Three items, one person. Work out who she is from a message export, a camera still and an HR record. The flag is her employee designation number. This is the first of three linked challenges, and what you learn here carries forward.

## Walkthrough

1. Unzip the dossier. It holds `messages_export.txt`, `feed_still.jpg` and `cole_notes.pdf`.
2. Read the messages. Someone named Maya confronts a man named Pierce about data exports and sounds threatening. A calendar entry mentions a meeting on 2026-03-20 at 21:00, at a place called SL2-MAIN.
3. Read the photo's metadata with `exiftool`. It was taken by a fixed Axis security camera, its GPS position is the Aletheia office, and it is dated 2026-03-11. It is a camera frame, not someone following anyone around.
4. Extract the text of the PDF. It is an HR record for Maya Cole, Data Analyst II at Northern Lights Data Services. Her manager is Daniel Pierce, and she filed an internal complaint against him over irregular access to a dataset.
5. The same record lists her employee designation: `558247193`. That is what the brief asks for.

## Watch out for

- On the surface the evidence makes Maya look dangerous. The brief warns you that the evidence may not be honest. Hold that thought for [P250](../../P250-witness/) and [P450](../../P450-endgame/).
- Keep the designation number. It is used again in P450.
- Note the meeting: 2026-03-20, 21:00, SL2-MAIN. It matters later.
