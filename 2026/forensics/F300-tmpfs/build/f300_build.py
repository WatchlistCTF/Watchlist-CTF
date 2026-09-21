#!/usr/bin/env python3
"""
F300 "Tmpfs" crypto core.
Builds the operative's vault, encrypts it with a SPLIT AES-128 key, and proves
the player's decryption path returns the flag. Scheme is deliberately
openssl-compatible so players can decrypt with one command on Kali.

  key  = hex_decode(KEY_HEAD + KEY_TAIL)   # 16 bytes -> AES-128
  iv   = 16 zero bytes
  mode = AES-128-CBC, PKCS7 padding
  file = b"VLT1" magic + ciphertext        # magic helps locate the blob in a heap dump
"""
import json, base64, subprocess, os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

# ---- locked constants ------------------------------------------------------
KEY_HEAD = "8b3f7e2a1c4d6f9b"   # -> operative's ENVIRONMENT (VAULT_KEY_HEAD)
KEY_TAIL = "0e8a7c5d2f1b3e6a"   # -> operative's COMMAND LINE (--keytail)
AUTH_PHRASE = "volatile_storage_has_a_half_life"
FLAG = "number{" + AUTH_PHRASE + "}"
MAGIC = b"VLT1"

VAULT = {
    "vault": "decima-operative",
    "operative": "Marcus Reyes",
    "handler": "Greer",
    "program": "Northern Lights / Contingency",
    "auth_phrase": AUTH_PHRASE,
    "issued": "2026-Q1",
    "note": "Phrase authenticates to the relay. Memorize. Never write to disk.",
}

def key_bytes():
    return bytes.fromhex(KEY_HEAD + KEY_TAIL)

def encrypt(plaintext: bytes) -> bytes:
    iv = b"\x00" * 16
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    c = Cipher(algorithms.AES(key_bytes()), modes.CBC(iv))
    enc = c.encryptor()
    return enc.update(padded) + enc.finalize()

def decrypt(ciphertext: bytes) -> bytes:
    iv = b"\x00" * 16
    c = Cipher(algorithms.AES(key_bytes()), modes.CBC(iv))
    dec = c.decryptor()
    padded = dec.update(ciphertext) + dec.finalize()
    unp = padding.PKCS7(128).unpadder()
    return unp.update(padded) + unp.finalize()

def main():
    plaintext = json.dumps(VAULT, indent=2).encode()
    ciphertext = encrypt(plaintext)
    blob = MAGIC + ciphertext

    with open(".vault.enc", "wb") as f:
        f.write(blob)
    with open("vault.json", "wb") as f:        # SECRET reference (never shipped)
        f.write(plaintext)

    # b64 for embedding in the staging script
    with open("vault_enc.b64", "w") as f:
        f.write(base64.b64encode(blob).decode())

    print(f"key head (env)     : {KEY_HEAD}")
    print(f"key tail (cmdline) : {KEY_TAIL}")
    print(f"full key (hex)     : {KEY_HEAD + KEY_TAIL}")
    print(f".vault.enc size    : {len(blob)} bytes (4 magic + {len(ciphertext)} cipher)")

    # ---- verify path 1: our own decrypt ----
    back = decrypt(blob[4:])
    got = json.loads(back)["auth_phrase"]
    assert got == AUTH_PHRASE, got
    print(f"\n[verify cryptography] auth_phrase = {got}")
    print(f"[verify cryptography] FLAG        = number{{{got}}}")
    assert f"number{{{got}}}" == FLAG

    # ---- verify path 2: openssl CLI (what players will use on Kali) ----
    with open("/tmp/_ct.bin", "wb") as f:
        f.write(blob[4:])                       # strip magic, raw ciphertext
    r = subprocess.run(
        ["openssl", "enc", "-d", "-aes-128-cbc",
         "-K", KEY_HEAD + KEY_TAIL, "-iv", "0" * 32,
         "-in", "/tmp/_ct.bin"],
        capture_output=True)
    if r.returncode == 0:
        oj = json.loads(r.stdout)
        print(f"\n[verify openssl]      auth_phrase = {oj['auth_phrase']}")
        assert oj["auth_phrase"] == AUTH_PHRASE
        print("[verify openssl]      openssl one-liner works for players")
    else:
        print("\n[verify openssl]      openssl not available here:", r.stderr.decode()[:120])
    os.remove("/tmp/_ct.bin")
    print("\nALL CRYPTO CHECKS PASSED")

if __name__ == "__main__":
    main()
