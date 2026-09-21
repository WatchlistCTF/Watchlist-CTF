# O100: Cadence (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{the_author_is_not_the_byline}
```

## In short

A Word document is a zip file full of XML. It records who created it, who saved it last, the template it was built from, when it was written, and, with tracked changes on, every word that was deleted. Two of those name fields are decoys. The real author is named in the template path, confirmed twice more, and the flag is in a paragraph they wrote and then deleted.

## Walkthrough

1. Treat the `.docx` as a zip archive and extract it (or read it with Python's `zipfile`).
2. Open `docProps/core.xml`. The creator is M. Reyes, the compliance officer on the byline. The last person to save it is `svc-docgen`, an automated service account. Both are dead ends: one is the costume the brief warns about, the other is a robot. Note also that the document was created at 03:14, an odd hour that gives the challenge its name.
3. Open `docProps/app.xml`. The template path is `C:\Users\akessler\AppData\...`. That username, `akessler`, matches neither name field. That is the person at the keyboard.
4. Open `word/document.xml` and look for tracked deletions, stored in `<w:del>` blocks with the removed words inside `<w:delText>`. The deletion's author attribute is also `akessler`, which confirms it.
5. Read the deleted paragraph. It is signed "AK" (akessler's initials, the third confirmation): they are leaving their name off, the Q3 audit numbers do not reconcile, and Reyes will not sign the real version. The flag is at the end of that deleted line.

## Watch out for

- Opening the file in Word and accepting all changes hides exactly what you are looking for. Read the XML, or use the Review view with all markup shown.
- The visible memo text is filler. Everything that matters is in the metadata and the deletions.
- `svc-docgen` is the trap. It is a real "last saved by" value, so it looks like the answer, but a service account is not a person. Three independent signals point at `akessler` instead: the template path, the deletion's author attribute, and the "AK" signature.

## Solver

[`solve_o100.py`](solve_o100.py) works from the document alone and runs 9 checks: it reads the two decoy name fields, finds `akessler` in the template path, matches it to the deletion's author and the "AK" signature, and pulls the flag from the deleted text.

- Run it with no arguments from this folder. It reads the file in [`../files/`](../files/).
- It needs only the Python 3 standard library. No network access or live server is needed.
