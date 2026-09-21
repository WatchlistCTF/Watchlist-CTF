# F100: Carter's Note (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{her_witness_was_still_breathing}
```

## In short

The zip holds a FAT32 USB image. Carter deleted some files before she died, and deleted files on FAT32 are still recoverable. Two of them each hold half of the flag in base64.

## Walkthrough

1. Unzip the download. You get `usb-0412-a.img`, a 300 MB raw FAT32 image with no partition table.
2. Mount it read-only and look around. You see folders like `case_files`, `family` and `personal`. This is the public surface of her life, and the flag is not here.
3. List the deleted files with The Sleuth Kit (`fls` with the recursive and deleted-only options). Five deleted entries show up: `draft_resignation.docx`, `note_0847.txt`, `birthday_ideas.txt`, `password_hints.txt` and a hidden dotfile called `.cipher_note`.
4. Recover each one by its entry number with `icat`.
5. Read them. `note_0847.txt` is the real work. Carter writes that someone is using the system as a kill list, that "the number is in two pieces", that the first piece is "with the household reminders", and she gives the second piece as a base64 string.
6. The household reminders are in `.cipher_note`. It holds the first base64 string.
7. Decode both. The first gives `her_witness`, the second gives `_was_still_breathing`. Join them and wrap in `number{}`.

## Watch out for

- The brief says four deleted files, but there are five. The dotfile is the one people miss, and it holds half the flag.
- `draft_resignation.docx`, `birthday_ideas.txt` and `password_hints.txt` are cover. They look interesting and lead nowhere.
- You have to read every recovered file, because the two halves sit in two different files.
