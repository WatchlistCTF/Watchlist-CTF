# F275 build

`build_lnk.py` writes the three Windows shortcut (.lnk) files, two visible with stomped timestamps and one hidden, each carrying the machine name, user and MAC in its tracker block. `drop_archive_inner.7z` is the archive placed on the hidden second partition (password is hostname:username).

To assemble the full 64 MB image: create an MBR disk with two FAT32 partitions, put the visible shortcuts and lore files on partition 1 (and the hidden shortcut into unallocated space), and `drop_archive_inner.7z` on partition 2. The flag is the SHA-256 of the four recovered values joined by colons.
