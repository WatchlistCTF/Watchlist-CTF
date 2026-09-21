# F300 build

Recreates the memory-capture scenario.

- `f300_build.py` builds the encrypted vault (AES-128-CBC, split key) and proves the openssl decrypt path.
- `vault.py` is the loader that holds the vault open in memory after it is deleted from disk.
- `stage_operative.sh` stages the live scene (the loader, the decoy processes, the panic deletion) on a throwaway VM.
- `capture_runbook.md` is the LiME memory-acquisition procedure.

The shipped download is the resulting memory image plus the Volatility symbol file. Run the staging only on a disposable VM.
