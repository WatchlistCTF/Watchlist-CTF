# F275: Dead Drop (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{eab3ef0976b5a44f}
```

## In short

The brief asks for the machine, the operator and the case. Windows shortcut (LNK) files on the drive leak the machine name, the user name and the machine's network card address. A small second partition holds the case number. The flag is a hash of those four values.

## Walkthrough

1. Check the partition table with `mmls`. There are two partitions: a 58 MB FAT32 one starting at sector 2048, and a tiny 2 MB one at sector 120832 that is easy to overlook.
2. Mount the first partition. A `TRANSFER` folder holds two shortcuts, `briefing_summary.lnk` and `schedule_q3.lnk`.
3. Parse them with an LNK parser (LnkParse3 works). Shortcuts remember where they were made:
   - the network path gives the machine name, `DECIMA-WS-07`,
   - the relative path goes through `Users\n.shaw`, which gives the operator, `n.shaw`,
   - the tracker block holds a volume id whose last 12 hex characters are the network card address, `00:1A:4F:C2:8E:3D`.
4. Carving the free space turns up a PDF and a contact list. They are background story and confirm the names, but they add nothing to the flag.
5. Scan the raw image for the LNK file signature. There are three hits, not two. The third, `device_check.lnk`, sits in unallocated space and is not in any folder. Carve it out and parse it. It confirms the same network card address, and its timestamp is real (2026), while the two visible shortcuts were backdated to 2019.
6. Mount the second partition. It holds `drop_archive.7z`, which wants a password.
7. The password is the machine and operator joined with a colon: `DECIMA-WS-07:n.shaw`. Inside, `case_ref.txt` gives the case number, `NL-2026-0447`.
8. Join all four values with colons: `DECIMA-WS-07:n.shaw:00:1A:4F:C2:8E:3D:NL-2026-0447`. Take the SHA-256 of that string, keep the first 16 hex characters, and wrap them in `number{}`.

## Watch out for

- The second partition is small and only shows up if you look at the partition table.
- The third shortcut is not in the directory listing. Only a raw signature scan finds it.
- The archive password is case sensitive and uses a colon.
- The backdated timestamps on the visible shortcuts are a deliberate tell that someone tampered with them.
