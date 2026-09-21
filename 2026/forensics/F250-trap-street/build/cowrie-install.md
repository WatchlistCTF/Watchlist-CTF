# Cowrie "Decima Staging Relay" Honeypot - Install Guide

End-to-end build of an internet-facing SSH honeypot on AWS, presenting as a fake
Decima Technologies staging relay (`dcm-stg-fra-04`) with a planted canary spreadsheet.
Written from the actual build; follow top to bottom on a fresh host.

---

## What you end up with

```
                      ┌─────────────────── AWS EC2 (Ubuntu 24.04) ───────────────────┐
  attacker ──:22──►   │  AWS Security Group (22 open) ─► iptables nat REDIRECT ─►:2222 │
                      │                                          Cowrie (dcm-stg-fra-04)│
  admin ────:60022─►  │  real sshd (moved off 22 in Phase 1)                           │
                      └───────────────────────────────────────────────────────────────┘
```

- Port **22** is bait - every connection lands in Cowrie and is logged.
- Real admin SSH lives on **60022** so it never collides with the honeypot.
- Cowrie listens on **2222**; an iptables redirect sends inbound 22 → 2222.

---

## Key facts for this deployment

| Item | Value |
|------|-------|
| Platform | AWS EC2, Ubuntu 24.04 LTS |
| Public IP | `100.27.201.47` |
| Admin SSH | port `60022`, user `ubuntu`, key `~/.ssh/forensics.pem` |
| Honeypot front port | `22` (redirected to 2222) |
| Cowrie listen port | `2222` |
| Service user | `cowrie` (dedicated, `--disabled-password`, no sudo) |
| Cowrie state dir | `/home/cowrie/cowrie` |
| venv | `/home/cowrie/cowrie/cowrie-env` |
| Config | `/home/cowrie/cowrie/etc/cowrie.cfg` |
| Filesystem pickle | `/home/cowrie/cowrie/var/lib/cowrie/fs.pickle` |
| honeyfs override | `/home/cowrie/cowrie/honeyfs` |
| Logs | `/home/cowrie/cowrie/var/log/cowrie/` |
| Honeypot identity | `dcm-stg-fra-04` - Decima Technologies / Northern Lights, FRA region |
| Canary file | `decima_subject_register.xlsx` |
| Injector script | `cowrie_decima_fs.py` |

---

## Prerequisites

- A fresh Ubuntu 24.04 host with sudo access (here: AWS EC2, user `ubuntu`).
- The two staging files available locally: `cowrie_decima_fs.py` and `decima_subject_register.xlsx`.
- **Out-of-band console access** (cloud provider web console) as a lockout safety net before Phase 1.

---

## Phase 1 - Move admin SSH to an alternate port

Frees port 22 for the honeypot and protects your real access. Pick a high port that is
**not 22** (bait) and **not 2222** (Cowrie). Here: `60022`.

> Keep your current SSH session open the whole time. Test the new port from a second
> terminal before closing anything.

```bash
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak

# check drop-ins for any Port override
sudo grep -ri '^Port' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/

# set the new port
sudo sed -i 's/^#\?Port .*/Port 60022/' /etc/ssh/sshd_config
```

**Ubuntu 24.04 gotcha - socket activation.** When `ssh.socket` is active it ignores the
`Port` line in `sshd_config`. Disable it so the traditional service honors the port:

```bash
sudo systemctl disable --now ssh.socket
sudo systemctl enable ssh.service
sudo sshd -t                      # validate config (no output = OK)
```

Open the new port (host firewall + cloud Security Group), then apply:

```bash
sudo ufw allow 60022/tcp comment 'admin ssh'   # if ufw is in use
sudo systemctl restart ssh.service
sudo ss -tlnp | grep ssh                        # confirm listening on :60022
```

Also open **60022** inbound in the AWS Security Group (ideally restricted to your IP).
Test from a **new** terminal before closing the old one:

```bash
ssh -p 60022 ubuntu@100.27.201.47
```

After this, nothing listens on 22 (expected - it stays dark until Phase 5).

---

## Phase 2 - Install Cowrie

Cowrie 3.0+ uses a pip-install operator workflow (state directory + venv). It refuses to
run as root, so it runs under a dedicated `cowrie` user.

### System dependencies (as `ubuntu`)

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv libssl-dev libffi-dev \
    build-essential libpython3-dev python3-minimal authbind git
```

### Create the dedicated user

```bash
sudo adduser --disabled-password cowrie
sudo su - cowrie
```

### Install (as `cowrie`)

```bash
mkdir ~/cowrie && cd ~/cowrie
python3 -m venv cowrie-env
source cowrie-env/bin/activate
python -m pip install --upgrade pip
python -m pip install cowrie
cowrie init
```

### Smoke test

```bash
cowrie start
ssh -p 2222 root@localhost      # any password; should drop into a fake shell
# look around, then: exit
cowrie stop
```

(`CryptographyDeprecationWarning: Blowfish/TripleDES` is harmless - ignore it.)

---

## Phase 3 - Configure Cowrie and materialize the filesystem

Run as `cowrie`, from `~/cowrie`, venv active.

### Edit `etc/cowrie.cfg`

Three settings (two are commented out by default - uncomment them):

| Section | Key | Value |
|---------|-----|-------|
| `[honeypot]` | `hostname` | `dcm-stg-fra-04` |
| `[honeypot]` | `contents_path` | `honeyfs` |
| `[shell]` | `filesystem` | `var/lib/cowrie/fs.pickle` |

```bash
sed -i 's|^hostname = svr04|hostname = dcm-stg-fra-04|' etc/cowrie.cfg
sed -i 's|^# contents_path = /opt/cowrie/honeyfs|contents_path = honeyfs|' etc/cowrie.cfg
sed -i 's|^# filesystem = /path/to/custom-fs.pickle|filesystem = var/lib/cowrie/fs.pickle|' etc/cowrie.cfg
```

### Materialize a writable copy of the bundled pickle

The bundled `fs.pickle` lives read-only inside the package. Copy it out to the path the
config now points at, so the injector can patch it:

```bash
mkdir -p honeyfs var/lib/cowrie
python -c "from cowrie.core.resources import read_data_bytes; open('var/lib/cowrie/fs.pickle','wb').write(read_data_bytes('fs.pickle'))"
```

Verify:

```bash
grep -nE '^(hostname|contents_path|filesystem) =' etc/cowrie.cfg
ls -l var/lib/cowrie/fs.pickle          # ~1.2 MB
```

### SSH banner - leave it Debian

The bundled filesystem is Debian-based (`/etc/issue` → `Debian GNU/Linux 12`), so the stock
banner (`[ssh] version = SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u3`) is internally consistent.
**Do not** switch it to Ubuntu - that would mismatch the emulated OS.

---

## Phase 4 - Inject the Decima filesystem and verify locally

Stage the two files into the `cowrie` user's home (as `ubuntu`, since `/tmp` sticky bit and
the cowrie account's lack of sudo block doing it as `cowrie`):

```bash
sudo cp /tmp/cowrie_decima_fs.py /tmp/decima_subject_register.xlsx /home/cowrie/
sudo chown cowrie:cowrie /home/cowrie/cowrie_decima_fs.py /home/cowrie/decima_subject_register.xlsx
```

Run the injector as `cowrie` from `~/cowrie` (Cowrie stopped), pointing `COWRIE_PICKLE` at the
working pickle:

```bash
COWRIE_PICKLE=/home/cowrie/cowrie/var/lib/cowrie/fs.pickle \
  python3 /home/cowrie/cowrie_decima_fs.py ~/cowrie /home/cowrie/decima_subject_register.xlsx
```

It backs up the pickle (`fs.pickle.bak-*`), writes the honeyfs content, and patches the pickle.

Verify in the fake shell:

```bash
cowrie start
ssh -p 2222 root@localhost
#   hostname                                  -> dcm-stg-fra-04
#   cat /etc/motd                             -> Decima banner
#   ls -l /opt/decima/staging/outbound/       -> archive + canary
#   cat /opt/decima/staging/outbound/.transfer.log
#   cat /home/jvoss/notes.txt
#   exit
```

> **Cowrie `ls` quirk:** Cowrie's `ls` ignores `-t`/`-S`/`-r` and always sorts alphabetically
> by filename. The injector's "newest mtime surfaces first" logic and its
> `CANARY SURFACES FIRST: True` self-check do **not** reflect real behavior - the canary
> shows second under `ls -lt`. This is fine: the canary is baited via `.transfer.log` and
> jvoss's `.bash_history` (which references `sha256sum decima_subject_register.xlsx`), which
> is a stronger lure than list order. Renaming the canary to force first position would be a
> bigger tell, so it's left as-is.

---

## Phase 5 - Go live (redirect port 22 → Cowrie)

Traffic path: `public IP:22` → AWS Security Group → instance → iptables redirect → Cowrie 2222.

1. **AWS Security Group:** open inbound TCP **22** from `0.0.0.0/0`. (Keep 60022 restricted.)
2. **Check the host firewall:** `sudo ufw status`.

### If ufw is INACTIVE (this build) - plain iptables

```bash
sudo ss -tlnp | grep ':2222'          # confirm Cowrie is listening first
sudo iptables -t nat -A PREROUTING -p tcp --dport 22 -j REDIRECT --to-port 2222
sudo iptables -t nat -S PREROUTING    # confirm the rule
# persist across reboots:
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
```

### If ufw is ACTIVE - use ufw's nat section instead

```bash
sudo ufw allow 2222/tcp               # redirect rewrites dport to 2222 before the filter
# add to the TOP of /etc/ufw/before.rules, above the *filter line:
#   *nat
#   :PREROUTING ACCEPT [0:0]
#   -A PREROUTING -p tcp --dport 22 -j REDIRECT --to-port 2222
#   COMMIT
sudo ufw reload
```

### Verify from an external machine

The redirect doesn't apply to loopback - test from your laptop, not the host:

```bash
ssh root@100.27.201.47          # default port 22 -> Decima shell
```

Admin access remains: `ssh -p 60022 ubuntu@100.27.201.47`.

---

## Phase 6 - Make it durable (systemd) + hardening

### systemd auto-start (so a reboot can't silently kill the honeypot)

Stop the manually-started instance first, then install the unit (as `ubuntu`):

```bash
sudo su - cowrie -c 'cd ~/cowrie && cowrie-env/bin/cowrie stop'

sudo tee /etc/systemd/system/cowrie.service > /dev/null <<'EOF'
[Unit]
Description=Cowrie SSH/Telnet Honeypot
After=network.target

[Service]
Type=simple
User=cowrie
Group=cowrie
WorkingDirectory=/home/cowrie/cowrie
ExecStart=/home/cowrie/cowrie/cowrie-env/bin/cowrie start -n
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now cowrie.service
sudo systemctl status cowrie.service --no-pager
```

From now on manage Cowrie with `sudo systemctl {start,stop,restart,status} cowrie`.
**Do not** mix the `cowrie` CLI with systemd - that causes stale-PID conflicts. If start ever
fails on a stale PID: `sudo rm /home/cowrie/cowrie/var/run/cowrie.pid` then restart.

We did **not** use Cowrie's socket-activated unit - it's unnecessary here since Cowrie listens
on 2222 directly and the iptables redirect handles 22.

### Remaining hardening checklist (recommended)

- [ ] Populate `/etc/os-release` to Debian 12 (stock honeyfs leaves it empty - a small tell).
      Do it via the pickle-load method (`fsctl`) so it reliably overrides.
- [ ] (Optional) Add a `jvoss` login to `etc/userdb.txt` so the planted username works.
- [ ] Harden admin SSH on 60022: key-only auth, `PasswordAuthentication no`, install fail2ban.
- [ ] Confirm structured logging in `var/log/cowrie/cowrie.json`; consider an output plugin
      (ELK / Splunk / etc.) for off-box retention.

---

## Operations

### Manage the service

```bash
sudo systemctl status cowrie
sudo systemctl restart cowrie
journalctl -u cowrie --no-pager        # service start/stop noise only
```

### Where captured data lives (all under /home/cowrie/cowrie)

| Path | Contents |
|------|----------|
| `var/log/cowrie/cowrie.log*` | text log: connections, IPs, commands |
| `var/log/cowrie/cowrie.json*` | structured event log |
| `var/lib/cowrie/tty/*` | keystroke session recordings |
| `var/lib/cowrie/downloads/*` | files captured during sessions |
| `var/lib/cowrie/fs.pickle` | **the Decima filesystem - never delete** |

### Reset session/log data (clear test data, keep fs.pickle)

Save as `reset-cowrie-logs.sh`, run `sudo bash reset-cowrie-logs.sh`:

```bash
#!/usr/bin/env bash
set -e
sudo systemctl stop cowrie
sudo rm -f /home/cowrie/cowrie/var/log/cowrie/cowrie.log*
sudo rm -f /home/cowrie/cowrie/var/log/cowrie/cowrie.json*
sudo rm -f /home/cowrie/cowrie/var/lib/cowrie/tty/*
sudo rm -f /home/cowrie/cowrie/var/lib/cowrie/downloads/*
sudo systemctl start cowrie
echo "Cowrie session data cleared; service restarted."
```

> The box is live: verify emptiness with the service **stopped**, because internet scanners
> repopulate the logs within minutes of starting. The wipe sets a clean baseline, not a
> permanently empty state.

---

## Gotchas hit during this build (so you don't repeat them)

- **`scp` port flag is `-P`** (uppercase) - opposite of `ssh`'s `-p`.
- **`/tmp` sticky bit** blocks `mv` of files you don't own - copy as `ubuntu`, then chown to cowrie.
- **The `cowrie` user has no sudo / no password.** For root tasks, `exit` to `ubuntu`.
- **Cowrie state dir is `/home/cowrie/cowrie`**, not `/home/cowrie`.
- **Ubuntu 24.04 `ssh.socket`** overrides the `Port` directive - disable it (Phase 1).
- **Cowrie `ls` never sorts by time** - alphabetical only. Don't rely on mtime for lures.
- **ufw was inactive here** - its rules/`before.rules` do nothing until `ufw enable`; used plain
  iptables for the redirect.
- **SSH banner stays Debian** to match the Debian-based emulated filesystem.
- **Don't mix `cowrie` CLI with systemd** once the unit is installed (stale PID).
