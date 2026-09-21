# F300: Tmpfs (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{volatile_storage_has_a_half_life}
```

## In short

The operative deleted his encrypted vault from disk, but the program that had read it was still running when the memory was captured. The vault is still in that process's memory. The key was split across two places in the same process: half in an environment variable, half on the command line.

## Walkthrough

1. Extract the archive. You get a LiME memory image (`reyes.lime.xz`, about 2 GB once decompressed), a Volatility 3 symbol file for the exact kernel, a player readme and checksums.
2. Install Volatility 3 and copy the symbol file into its `symbols/linux` folder. Leave the symbol file compressed. Volatility reads the `.xz` directly.
3. List processes with their arguments (`linux.psaux`). Among about a hundred, a few stand out: the operator's `bash`, a `python3` running `/tmp/.cache/vault.py --keytail 0e8a7c5d2f1b3e6a`, a `nc` listener on port 4444, a `tcpdump` and a `gpg-agent`. Only the python process was holding something.
4. Optional, but it tells the story: recover the shell's command history from memory (`linux.bash`). The history file was deleted, but the shell still remembers. It shows the panic: he inspected `.vault.enc`, checked for the vault process, then deleted the vault files and the history.
5. The `--keytail` value is the second half of a key. For the first half, dump that python process's environment variables (`linux.envars`). You find `VAULT_KEY_HEAD=8b3f7e2a1c4d6f9b`, and `VAULT_LOC` pointing at `/tmp/.cache/.vault.enc`.
6. Put head and tail together for the full AES-128 key: `8b3f7e2a1c4d6f9b0e8a7c5d2f1b3e6a`.
7. The vault file no longer exists on disk, so take it from memory. Dump the python process's memory regions (`linux.proc.Maps` with the dump option).
8. Search the dumped regions for the vault's 4-byte marker, `VLT1`. It turns up in the large heap region. Carve 292 bytes from there: 4 bytes of marker plus 288 bytes of ciphertext.
9. Drop the 4-byte marker and decrypt the rest with AES-128-CBC, using the key above and an all-zero IV. A plain `openssl enc -d` does it.
10. The output is a small JSON record naming the operative (Marcus Reyes), his handler (Greer) and the program. The `auth_phrase` field is the flag text.

## Watch out for

- `nc`, `tcpdump` and `gpg-agent` are there to distract. None of them is needed for the flag.
- Neither half of the key works alone, and a plain string search of the image will not hand you the key in one piece.
- In Volatility's environment listing the name and the value are in separate columns. If you search for `VAULT_KEY_HEAD=` with an equals sign you will find nothing.
- The vault sits in a large anonymous memory region (about 3 MB), not in the regions that belong to the python program itself.

## Solver

[`f300_solve.sh`](f300_solve.sh) runs the same path: process list, environment, memory dump, carve, decrypt.

- It needs the memory image from the `2026-files` release (`F300-tmpfs.7z`), Volatility 3 on your PATH with the supplied symbol file installed, `openssl` and `python3`. The top of the script lists the setup steps.
- No network access or live server is needed.
- We checked its method by rebuilding the scene with the original creator scripts: the real vault loader was started with the split key, the vault file was deleted, and the script's carve and decrypt steps recovered the flag from the live process's memory.
