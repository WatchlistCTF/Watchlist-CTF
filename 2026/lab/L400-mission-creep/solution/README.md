# L400: Mission Creep (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{a_foothold_is_never_just_a_foothold}
```

## In short

A full disk image of a compromised Linux server. You rebuild the attack in order: how they got in (an uploaded webshell), how they stayed (a fake cleanup timer), how they became root (a tampered `pkexec`), what they wiped, and what they forgot. Each stage points to the next. The flag is in a crash dump left behind in their loot folder.

## Walkthrough

### Set up

1. Extract the archive and decompress `relay-07.img.xz`. The raw image is about 25 GB, so keep at least 30 GB free.
2. The disk uses LVM. Mount it read-only with `guestmount`, which handles LVM for you. It takes up to a minute.

### Find when it happened

3. Build a filesystem timeline with The Sleuth Kit (`fls` to make a body file, then `mactime`).
4. Two bursts of activity show up. 9 April 2026 is random internet scanning and brute forcing. Ignore it. 14 April 2026, 02:15 to 02:38 UTC, is a tight 23-minute window. That is the intrusion.

### Stage 1: the way in

5. Read the nginx access log for that window. At 02:15:51 there is a successful POST to `/upload.php`.
6. Look in the web uploads folder. `sess_4f1c.php` is a one-line webshell that runs whatever command it is sent. Later log lines show it being used to fetch a second stage into `/dev/shm`, which is memory-only and gone after power-off. The log is the evidence that survived.

### Stage 2: how they stayed

7. List the systemd timers. Two are unusual: `cleanup.timer` and `nodebackup.timer`.
8. `nodebackup.timer` is a genuine daily backup. `cleanup.timer` is the fake: it fires every 15 minutes, it was last modified on the day of the intrusion, and it runs a hidden script, `/usr/local/sbin/.sysupd`.
9. Read `.sysupd`. It calls `pkexec` with an environment variable named `PKEXEC_AUTH`. That points to the next stage.

### Stage 3: how they became root

10. Check `pkexec` against the package database (`dpkg --verify` or `debsums`). The checksum does not match, so the binary was replaced.
11. Run `strings` over it. `PKEXEC_AUTH` and `/bin/bash` are both in there, which confirms a backdoor.
12. The trigger word is lightly hidden: each character is XORed with `0x42`. Undo that across the strings output and one readable word appears, `C0NT1NGENCY`. Running `pkexec` with `PKEXEC_AUTH` set to that word gives a root shell.

### Stage 4: the cover-up

13. Check the login records. `wtmp` and `lastlog` are empty, and root's bash history is empty, on a machine whose `auth.log` goes back weeks. Meanwhile the ordinary user `jhayes` still has a normal history. Missing records on a busy machine means someone wiped them.
14. Go back to the timeline. At 02:31 a folder named `/var/tmp/.x` was created.

### Stage 5: what they took

15. List `/var/tmp/.x/`. It holds `loot.tgz` and a `core` file. A program crashed during the theft and left a memory dump, and the cleanup missed the folder.
16. Run `strings` over the core file and search for `number{`. The flag is there.

## Watch out for

- Searching the whole disk for `number{` as plain text finds nothing useful. The flag only appears inside the core dump, so you have to follow the chain to know where to look.
- The 9 April activity is background noise. Starting there wastes time.
- Files on the mounted image belong to root, so most reads need `sudo`.

## Solver

[`l400_solve.sh`](l400_solve.sh) walks all five stages and checks each pivot, 17 checks in all. It is read-only and never writes to the target.

- Get the image from the `2026-files` release (`L400-mission-creep.7z`), extract and decompress it, mount it read-only, and point the script at the mount: `ROOT=/mnt/l400 bash l400_solve.sh`.
- The script needs only coreutils, `grep` and `strings`. Building the timeline in stage 0 needs the Sleuth Kit or plaso.
- No network access or live server is needed.
- We checked its logic without the 25 GB image by recreating the planted layout from the original build script: the webshell and its log line, the malicious and the decoy timer, the hidden payload, a stand-in `pkexec` carrying the backdoor strings but not the plaintext trigger, the wiped login records against an intact user history, and a core file holding the flag only in binary. The unchanged solver passed 17 of 17 against that layout.
