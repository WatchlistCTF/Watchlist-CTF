# F300 "Tmpfs" - capture & package runbook (asset VM)

Everything here runs on the **asset VM** (Ubuntu Server 22.04.5, kernel
6.8.0-124-generic), which the spike already proved out. The ISF is already
generated and cached at `~/f300-isf-6.8.0-124-generic.json`.

## 0. Prep: a settled system
The spike showed captures taken right after heavy apt/compile activity are
unparseable. So capture on a **fresh boot, lightly loaded** box.

```
sudo reboot
# log back in, do nothing else heavy
```

## 1. Stage the scenario
```
sudo bash stage_operative.sh
```
Confirm it ends with `state  OK .vault.enc deleted-but-open in pid <N>`.
Leave it running.

## 2. Capture RAM with LiME
```
mkdir -p $HOME/f300-work
sudo rmmod lime 2>/dev/null
sudo insmod ~/junk/LiME/src/lime-$(uname -r).ko \
     "path=$HOME/f300-work/reyes.lime format=lime"
ls -lh $HOME/f300-work/reyes.lime          # ~2 GB
sudo chown marcus: $HOME/f300-work/reyes.lime
```

## 3. Verify the capture parses (do NOT skip)
```
vol -f $HOME/f300-work/reyes.lime linux.pslist | grep -Ei 'python3|tcpdump|gpg-agent|nc'
```
You should see the four processes. If pslist is empty, the capture caught the
memory map mid-churn, just `rmmod lime` and re-`insmod` to recapture.

## 4. Validate the full solve path
```
bash f300_solve.sh $HOME/f300-work/reyes.lime
```
Expect it to end with `SOLVED -> number{volatile_storage_has_a_half_life}`.

## 5. Package the player artifact
```
cd $HOME/f300-work
xz -9e -T0 -k reyes.lime                            # -> reyes.lime.xz (~500-700 MB)
cp ~/f300-isf-6.8.0-124-generic.json ubuntu-6.8.0-124-generic.json
xz -9 ubuntu-6.8.0-124-generic.json                 # ship the symbol file gzipped/xz'd
sha256sum reyes.lime.xz ubuntu-6.8.0-124-generic.json.xz
```
Player download bundle = `reyes.lime.xz` + `ubuntu-6.8.0-124-generic.json.xz`
+ `README_player.md`.

## Notes
- The symbol file is shipped so players never need dbgsym/dwarf2json. They drop
  it into `volatility3/symbols/linux/` (decompressed or as `.json.gz`).
- `reyes.lime` and `~/f300-isf-*.json` are build secrets only in the sense that
  the dump *is* the challenge; the ISF is fine to ship (it's just kernel symbols).
- Do not ship `vault.json`, `f300_solve.sh`, or `stage_operative.sh`.
