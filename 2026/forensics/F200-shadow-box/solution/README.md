# F200: Shadow Box (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{greer_targeted_contingency}
```

## In short

The PDF was saved three times, and each save covered the one before without erasing it. The flag is never written anywhere in the file. You build it from three findings, one from each hidden layer: a name, a word and a domain.

## Walkthrough

### Piece 1: who really wrote it (`greer`)

1. Count the `%%EOF` markers in the file. There are three, which means the PDF was saved incrementally three times. Every older version is still inside.
2. Cut the file at the first `%%EOF` and open that as its own PDF. This is the original memo, before it was falsified. It says the program is ACTIVE, the subjects are PENDING ACTION, and it is signed by S. Greer.
3. Check the metadata across the revisions with `pdf-parser.py`. The author field reads "S. Greer" first and "James Harrison" later. The earliest author is the true one. First piece: `greer`.

### Piece 2: the image they removed (`targeted`)

4. Run `pdfimages` on the file. It finds one image, the cover graphic, and nothing else. That is the trap: it only looks at images still attached to a page.
5. Search the raw objects for images with `pdf-parser.py`. Two JPEG objects turn up: the cover graphic you already saw, and a smaller one that is orphaned, meaning it was removed from the page but left in the file.
6. Dump that object to a JPEG and open it. It is a thumbnail of the memo with tracked changes showing. Under "Project status", the word TARGETED is struck through in red and replaced with CLEARED. Under "Disposition", PENDING ACTION is struck through and replaced with WOUND DOWN. The project status line is the one that matters. Second piece: `targeted`.

### Piece 3: the hidden script (`contingency`)

7. Run `pdfid.py`. It reports JavaScript and an action that runs when the file opens.
8. Pull the script out with `pdf-parser.py`. It calls home to `contingency.decima.cloud`. Third piece: the subdomain, `contingency`.

### Put it together

9. Join the three pieces with underscores inside `number{}`.

## Watch out for

- Searching the file for `number{` finds nothing. The flag has to be assembled.
- `pdfimages` showing only the cover graphic does not mean that is the only image in the file.
- The thumbnail has two struck-through phrases. The flag uses the first one, the project status.
- The `contingency` domain is also a breadcrumb toward the hidden challenge [B350](../../../hidden/B350-contingency/).

## Solver

[`f200_solve.py`](f200_solve.py) walks the same three layers against the file in [`../files/`](../files/) and prints the hand command for each step. It finds every object by reading the raw bytes, with no object numbers written into it.

- Run it with no arguments from this folder.
- Layers 1 and 3 need only Python 3.
- Layer 2 reads a word out of a picture. With `pillow`, `numpy`, `pytesseract` and the `tesseract` program installed, it reads the word itself. Without them it saves the picture as `f200_orphan.jpg` and stops. Open the picture, read the word, and run it again with `--word` followed by that word.
- No network access or live server is needed.
