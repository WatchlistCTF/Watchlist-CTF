#!/usr/bin/env python3
"""
F275 Dead Drop - LNK file builder v2
Fixed: LinkInfo offsets, StringData encoding, TrackerDataBlock format
"""
import struct, os, datetime, random

# ─── Challenge metadata ───────────────────────────────────────────────────────
HOSTNAME = "DECIMA-WS-07"
USERNAME = "n.shaw"
MAC_BYTES = bytes.fromhex("001A4FC28E3D")
OUT = "/tmp/lnk_build"
os.makedirs(OUT, exist_ok=True)

# ─── LNK Header constants ─────────────────────────────────────────────────────
CLSID = bytes.fromhex("0114020000000000C000000000000046")
FLAG_HAS_LINK_INFO   = 0x00000002
FLAG_HAS_REL_PATH    = 0x00000008
FLAG_HAS_WORKING_DIR = 0x00000010
FLAG_IS_UNICODE      = 0x00000080
FILE_ATTR_ARCHIVE    = 0x00000020

def filetime(dt):
    """datetime → Windows FILETIME (100ns intervals since 1601-01-01 UTC)"""
    epoch = datetime.datetime(1601,1,1,tzinfo=datetime.timezone.utc)
    d = dt.replace(tzinfo=datetime.timezone.utc) - epoch
    return int(d.total_seconds() * 10_000_000)

def make_header(link_flags, ctime, atime, mtime):
    h = struct.pack('<I', 0x4C)          # HeaderSize
    h += CLSID                            # LinkCLSID
    h += struct.pack('<I', link_flags)    # LinkFlags
    h += struct.pack('<I', FILE_ATTR_ARCHIVE) # FileAttributes
    h += struct.pack('<Q', filetime(ctime))   # CreationTime
    h += struct.pack('<Q', filetime(atime))   # AccessTime
    h += struct.pack('<Q', filetime(mtime))   # WriteTime
    h += struct.pack('<I', 0)             # FileSize
    h += struct.pack('<I', 0)             # IconIndex
    h += struct.pack('<I', 1)             # ShowCommand NORMAL
    h += struct.pack('<H', 0)             # HotKey
    h += b'\x00' * 10                    # Reserved
    assert len(h) == 0x4C
    return h

def make_link_info_network(net_share):
    """LinkInfo with CommonNetworkRelativeLink only (no VolumeID)."""
    net_name = net_share.encode('ascii') + b'\x00'
    dev_name = b'\x00'

    # CommonNetworkRelativeLink
    cnrl_hdr_size = 0x14  # 5 fields × 4 bytes
    cnrl_size = cnrl_hdr_size + len(net_name) + len(dev_name)
    cnrl = struct.pack('<IIIII',
        cnrl_size,
        0,                          # flags
        cnrl_hdr_size,              # NetNameOffset
        cnrl_hdr_size + len(net_name),  # DeviceNameOffset
        0,                          # NetworkProviderType
    ) + net_name + dev_name

    # LinkInfo header (0x1C = 28 bytes)
    li_hdr   = 0x1C
    cnrl_off = li_hdr
    sfx_off  = cnrl_off + len(cnrl)
    suffix   = b'\x00'
    li_size  = li_hdr + len(cnrl) + len(suffix)

    li = struct.pack('<IIIIIII',
        li_size,
        li_hdr,
        0x00000002,  # CommonNetworkRelativeLinkAndPathSuffix
        0,           # VolumeIDOffset (not present)
        0,           # LocalBasePathOffset (not present)
        cnrl_off,    # CommonNetworkRelativeLinkOffset
        sfx_off,     # CommonPathSuffixOffset
    ) + cnrl + suffix
    return li

def ustr(s):
    """Unicode string block: CountChars(2) + UTF-16LE"""
    enc = s.encode('utf-16-le')
    return struct.pack('<H', len(s)) + enc

def make_tracker_block(hostname, mac_bytes):
    """
    TrackerDataBlock (ExtraData signature 0xA0000003).
    MachineID = hostname (NetBIOS name, null-padded to 16 bytes)
    Droid[0]  = UUID v1 with MAC embedded in last 6 bytes (node field)
    """
    machine_id = hostname.encode('ascii')[:16].ljust(16, b'\x00')

    def uuid_with_mac(mac):
        # time_low(4) time_mid(2) time_hi_version(2) clock_seq(2) node(6)
        tl = random.randint(0, 0xFFFFFFFF)
        tm = random.randint(0, 0xFFFF)
        th = 0x1000 | random.randint(0, 0x0FFF)      # version 1
        cs = 0x8000 | random.randint(0, 0x3FFF)       # variant RFC 4122
        # Pack as little-endian GUID (Windows GUID byte order)
        return struct.pack('<IHH', tl, tm, th) + struct.pack('>H', cs) + mac

    droid1      = uuid_with_mac(mac_bytes)
    droid2      = uuid_with_mac(os.urandom(6))
    droidbirth1 = uuid_with_mac(mac_bytes)
    droidbirth2 = uuid_with_mac(os.urandom(6))

    # Inner = Length(4) + Version(4) + MachineID(16) + 4×GUID(16) = 88 = 0x58
    inner = (struct.pack('<II', 0x58, 0) +   # Length2, Version
             machine_id +
             droid1 + droid2 + droidbirth1 + droidbirth2)
    assert len(inner) == 88

    # Block = BlockSize(4) + Signature(4) + inner(88) = 96 = 0x60
    block = struct.pack('<II', 0x60, 0xA0000003) + inner
    assert len(block) == 96
    return block

def build_lnk(net_share, rel_path, work_dir, hostname, mac_bytes, ctime, atime, mtime):
    link_flags = (FLAG_HAS_LINK_INFO | FLAG_HAS_REL_PATH |
                  FLAG_HAS_WORKING_DIR | FLAG_IS_UNICODE)

    header      = make_header(link_flags, ctime, atime, mtime)
    link_info   = make_link_info_network(net_share)
    string_data = ustr(rel_path) + ustr(work_dir)
    extra_data  = make_tracker_block(hostname, mac_bytes) + struct.pack('<I', 0)

    return header + link_info + string_data + extra_data

# ─── Timestamps ───────────────────────────────────────────────────────────────
stomped = datetime.datetime(2019, 3, 14, 9, 26, 53)   # pi day - deliberate
real    = datetime.datetime(2026, 9,  2, 14, 32, 17)

# ─── Build LNK files ──────────────────────────────────────────────────────────
files = [
    ("briefing_summary.lnk",
     f"\\\\{HOSTNAME}\\ops\\northern-lights\\",
     f"..\\Users\\{USERNAME}\\Documents\\briefing_summary.pdf",
     f"C:\\Users\\{USERNAME}\\Documents",
     stomped),
    ("schedule_q3.lnk",
     f"\\\\{HOSTNAME}\\ops\\q3-planning\\",
     f"..\\Users\\{USERNAME}\\Documents\\schedule_q3.xlsx",
     f"C:\\Users\\{USERNAME}\\Documents",
     stomped),
    ("device_check.lnk",
     f"\\\\{HOSTNAME}\\admin\\device-inventory\\",
     f"..\\Users\\{USERNAME}\\Desktop\\device_check.txt",
     f"C:\\Users\\{USERNAME}\\Desktop",
     real),
]

for fname, net, rel, wd, ts in files:
    data = build_lnk(net, rel, wd, HOSTNAME, MAC_BYTES, ts, ts, ts)
    path = f"{OUT}/{fname}"
    open(path, 'wb').write(data)
    print(f"Written: {fname} ({len(data)} bytes)")

# ─── Verify ───────────────────────────────────────────────────────────────────
print("\n--- Verification ---")
import LnkParse3, json

for fname, *_ in files:
    path = f"{OUT}/{fname}"
    with open(path,'rb') as f:
        lnk = LnkParse3.lnk_file(f)
    d = lnk.get_json()
    print(f"\n{fname}:")
    li = d.get('link_info',{})
    cnrl = li.get('location_info',{})
    print(f"  net_name:    {cnrl.get('net_name', cnrl.get('common_network_relative_link',{}).get('net_name','?'))}")
    print(f"  rel_path:    {d.get('data',{}).get('relative_path','?')}")
    print(f"  working_dir: {d.get('data',{}).get('working_directory','?')}")
    tr = d.get('extra',{}).get('DISTRIBUTED_LINK_TRACKER_BLOCK',{})
    print(f"  machine_id:  {tr.get('machine_identifier','NOT FOUND')}")
    print(f"  droid[0]:    {tr.get('droid_volume_identifier', tr.get('droid_file_identifier','NOT FOUND'))}")
    print(f"  ctime:       {d.get('header',{}).get('creation_time','?')}")
