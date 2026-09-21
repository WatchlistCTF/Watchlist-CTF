# L100: Reduced Footprint (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{the_footprint_was_never_reduced}
```

## In short

You get a read-only SSH seat on a "decommissioned" node. Something still runs on a schedule. Of three scheduled items that look normal, one is the intruder's. It points to a script in a hidden folder, and the script carries the flag in base64.

## Walkthrough

1. Log in over SSH with the account given in the challenge (`investigator`).
2. Read `notes.txt` in the home folder. It repeats the brief: three things look like they belong, and two do.
3. Look around for things that run by themselves. Three look like they belong:
   - a certbot cron job in `/etc/cron.d/`,
   - a login banner script, `/etc/profile.d/00-welcome.sh`, which decodes a base64 string,
   - a `sysupdate` service and timer in `/etc/systemd/system/`.
4. Check the first two. The certbot job renews certificates, which is ordinary. The banner's base64 string decodes to "AUTHORIZED PERSONNEL ONLY :: NODE 0447 :: ACTIVITY IS LOGGED". It looks suspicious and is harmless. That leaves `sysupdate`.
5. Read `sysupdate.service`. It runs `/usr/local/lib/.sysupdate/run.sh`.
6. List `/usr/local/lib/`. A plain `ls` shows nothing odd, because the folder name starts with a dot. List it again with hidden files shown (`ls -a`) and `.sysupdate/` appears.
7. Read `run.sh`. It calls itself a "sysupdate helper" and carries a "maintenance token" in base64.
8. Decode it. That is the flag.

## Watch out for

- `contingency.timer` also looks out of place. It is a breadcrumb toward the hidden challenge [B350](../../../hidden/B350-contingency/).
- The banner script is the better decoy. It holds a base64 string just like the real implant does, so decoding it and finding no flag is part of the path.
- The operator's account, `relay`, still has a shell history and a `cleanup.sh`. Both mention `sysupdate` and a helper directory they meant to remove, and neither names the hidden folder. The notes hint at this: "the history is not the only thing that remembers".
- The script ends with the comment `# signed: bad code`. The brief tells you to remember that signature. It leads to the hidden challenge [B200](../../../hidden/B200-bad-code/).

## Solver

[`l100_check.sh`](l100_check.sh) logs in over SSH, runs the same commands a player would, and confirms 19 things: the decoys are harmless, plain `ls` hides the folder, `ls -a` shows it, the implant decodes to the flag, and the flag appears nowhere in plain text.

- It needs only `bash`, `ssh` and `base64`.
- It needs a live node. The event node was taken offline after the CTF, so the script is here for anyone who rebuilds the node.
- We checked it without the live node. The original build script's file injector was run to recreate every planted file, and the unchanged check script passed 19 of 19 against that copy.
