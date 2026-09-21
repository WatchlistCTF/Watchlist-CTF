#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# F100 - CARTER'S NOTE - Test / Verification Script
# ═══════════════════════════════════════════════════════════════════
#
# What this checks:
#   1. Image file exists and is valid FAT32
#   2. Total file count on disk (should be ~150+)
#   3. Per-folder size sanity check
#   4. Spot-check case PDFs (each should be 50-200 KB)
#   5. Spot-check family JPGs (each should be 500KB-1.5MB)
#   6. Deleted files are recoverable (via testdisk/photorec or sleuthkit)
#   7. Base64 fragments present in image bytes (anti-strings test)
#   8. Plain-text flag NOT present (anti-shortcut test)
#   9. Decode fragments and verify they combine to the correct flag
#
# Usage:
#   ./test-f100.sh /path/to/usb-0412-a.img
#   ./test-f100.sh                   # uses default /tmp/f100-build/usb-0412-a.img
#
# Requirements:
#   - sudo (for loop mount)
#   - sleuthkit (fls, icat) - optional but recommended for deleted-file test
#       sudo apt install sleuthkit
#
# ═══════════════════════════════════════════════════════════════════

set -e

IMG="${1:-/tmp/f100-build/usb-0412-a.img}"
MNT="/tmp/f100-test-mnt"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

PASS=0
FAIL=0
WARN=0

pass()  { echo -e "  ${GREEN}✓${NC} $1";          PASS=$((PASS+1)); }
fail()  { echo -e "  ${RED}✗${NC} $1";            FAIL=$((FAIL+1)); }
warn()  { echo -e "  ${YELLOW}!${NC} $1";         WARN=$((WARN+1)); }
info()  { echo -e "  ${BLUE}·${NC} $1"; }
hdr()   { echo ""; echo -e "${BOLD}▸ $1${NC}"; }

# Cleanup function
cleanup() {
  sudo umount "${MNT}" 2>/dev/null || true
  rmdir "${MNT}" 2>/dev/null || true
}
trap cleanup EXIT

# ═══════════════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  F100 - CARTER'S NOTE - verification"
echo "═══════════════════════════════════════════════════════════════════"
echo "  Image: ${IMG}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# 1. IMAGE EXISTS & IS VALID FAT32
# ═══════════════════════════════════════════════════════════════════
hdr "Image integrity"

if [ ! -f "${IMG}" ]; then
  fail "Image not found at ${IMG}"
  exit 1
fi
pass "Image file exists"

IMG_SIZE=$(du -h "${IMG}" | cut -f1)
IMG_BYTES=$(stat -c%s "${IMG}")
info "Raw size: ${IMG_SIZE} (${IMG_BYTES} bytes)"

# Detect filesystem
FS_TYPE=$(file "${IMG}" | grep -oE "FAT \(.*\)" || echo "unknown")
if echo "${FS_TYPE}" | grep -q "FAT"; then
  pass "Filesystem: FAT32 detected"
else
  warn "Filesystem detection unclear: $(file "${IMG}" | head -1)"
fi

# ═══════════════════════════════════════════════════════════════════
# 2. MOUNT THE IMAGE
# ═══════════════════════════════════════════════════════════════════
hdr "Mounting image"

mkdir -p "${MNT}"
if sudo mount -o loop,ro "${IMG}" "${MNT}" 2>/dev/null; then
  pass "Mounted read-only at ${MNT}"
else
  fail "Failed to mount image"
  exit 1
fi

# ═══════════════════════════════════════════════════════════════════
# 3. FILE COUNT
# ═══════════════════════════════════════════════════════════════════
hdr "File inventory"

TOTAL_FILES=$(find "${MNT}" -type f 2>/dev/null | wc -l)
info "Visible files on image: ${TOTAL_FILES}"

if [ "${TOTAL_FILES}" -ge 100 ]; then
  pass "File count looks realistic (≥100 expected)"
elif [ "${TOTAL_FILES}" -ge 50 ]; then
  warn "File count low: ${TOTAL_FILES} (expected ~100+)"
else
  fail "File count too low: ${TOTAL_FILES}"
fi

# Per-folder summary
echo ""
info "Per-folder content size:"
for d in case_files family reference personal HR_investigation; do
  if [ -d "${MNT}/${d}" ]; then
    SIZE=$(du -sh "${MNT}/${d}" 2>/dev/null | cut -f1)
    COUNT=$(find "${MNT}/${d}" -type f | wc -l)
    printf "    %-22s %6s  (%3d files)\n" "${d}/" "${SIZE}" "${COUNT}"
  fi
done

# ═══════════════════════════════════════════════════════════════════
# 4. CASE PDF SIZE SPOT-CHECK
# ═══════════════════════════════════════════════════════════════════
hdr "Case PDF size sanity"

PDF_SAMPLE=$(find "${MNT}/case_files/2024" -name "*.pdf" -type f 2>/dev/null | head -3)
if [ -z "${PDF_SAMPLE}" ]; then
  fail "No case PDFs found in case_files/2024/"
else
  for pdf in ${PDF_SAMPLE}; do
    SIZE_BYTES=$(stat -c%s "${pdf}")
    SIZE_KB=$((SIZE_BYTES / 1024))
    FNAME=$(basename "${pdf}")
    if [ "${SIZE_KB}" -ge 30 ] && [ "${SIZE_KB}" -le 500 ]; then
      pass "${FNAME}: ${SIZE_KB} KB (in expected 30-500 KB range)"
    elif [ "${SIZE_KB}" -lt 30 ]; then
      warn "${FNAME}: ${SIZE_KB} KB - too small (expected 30-500 KB)"
    else
      warn "${FNAME}: ${SIZE_KB} KB - larger than expected"
    fi
  done
fi

# Verify PDF magic number on one file
FIRST_PDF=$(find "${MNT}/case_files/2024" -name "*.pdf" -type f 2>/dev/null | head -1)
if [ -n "${FIRST_PDF}" ]; then
  MAGIC=$(head -c 4 "${FIRST_PDF}" | head -c 4)
  if echo "${MAGIC}" | grep -q "%PDF"; then
    pass "PDF magic number valid"
  else
    fail "PDF magic number invalid - file may be corrupted"
  fi
fi

# ═══════════════════════════════════════════════════════════════════
# 5. FAMILY PHOTO SIZE SPOT-CHECK
# ═══════════════════════════════════════════════════════════════════
hdr "Family JPG size sanity"

JPG_SAMPLE=$(find "${MNT}/family" -name "*.jpg" -type f 2>/dev/null | head -3)
if [ -z "${JPG_SAMPLE}" ]; then
  fail "No JPGs found in family/"
else
  for jpg in ${JPG_SAMPLE}; do
    SIZE_BYTES=$(stat -c%s "${jpg}")
    SIZE_KB=$((SIZE_BYTES / 1024))
    FNAME=$(basename "${jpg}")
    if [ "${SIZE_KB}" -ge 300 ] && [ "${SIZE_KB}" -le 2000 ]; then
      pass "${FNAME}: ${SIZE_KB} KB (in expected 300 KB-2 MB range)"
    elif [ "${SIZE_KB}" -lt 300 ]; then
      warn "${FNAME}: ${SIZE_KB} KB - too small (likely still solid-color)"
    else
      warn "${FNAME}: ${SIZE_KB} KB - larger than expected"
    fi
  done
fi

# Verify JPG validity with `file`
FIRST_JPG=$(find "${MNT}/family" -name "*.jpg" -type f 2>/dev/null | head -1)
if [ -n "${FIRST_JPG}" ]; then
  if file "${FIRST_JPG}" | grep -q "JPEG image data"; then
    pass "JPEG format validated by file(1)"
  else
    fail "JPG file format invalid: $(file "${FIRST_JPG}")"
  fi
fi

# ═══════════════════════════════════════════════════════════════════
# 6. EXPECTED FOLDERS PRESENT
# ═══════════════════════════════════════════════════════════════════
hdr "Expected directory structure"

EXPECTED_DIRS=(
  "case_files/2024"
  "case_files/2023"
  "case_files/2022"
  "case_files/archive/unsolved_cold"
  "case_files/archive/high_profile"
  "reference/interview_templates"
  "family/2023_vacation"
  "family/2024_birthday"
  "family/taylor_school"
  "family/thanksgiving_2024"
  "personal/recipes"
  "personal/music"
  "HR_investigation/known_dirty"
  "HR_investigation/photos/surveillance"
  "HR_investigation/photos/crime_scene_thumbnails"
)

for d in "${EXPECTED_DIRS[@]}"; do
  if [ -d "${MNT}/${d}" ]; then
    pass "${d}/"
  else
    fail "Missing: ${d}/"
  fi
done

# ═══════════════════════════════════════════════════════════════════
# 7. KEY VISIBLE FILES PRESENT
# ═══════════════════════════════════════════════════════════════════
hdr "Key cover files present"

EXPECTED_FILES=(
  "readme.txt"
  "case_files/2024/case_summary_2024.txt"
  "case_files/2023/case_summary_2023.txt"
  "case_files/2022/case_summary_2022.txt"
  "HR_investigation/notes_to_self.txt"
  "HR_investigation/known_dirty/lt_quinn_notes.txt"
  "personal/coffee_order.txt"
  "personal/recipes/mom_lasagna.txt"
)

for f in "${EXPECTED_FILES[@]}"; do
  if [ -f "${MNT}/${f}" ]; then
    pass "${f}"
  else
    fail "Missing: ${f}"
  fi
done

# ═══════════════════════════════════════════════════════════════════
# 8. UNMOUNT BEFORE RAW INSPECTION
# ═══════════════════════════════════════════════════════════════════
sudo umount "${MNT}"

# ═══════════════════════════════════════════════════════════════════
# 9. ANTI-SHORTCUT: FLAG NOT IN PLAIN BYTES
# ═══════════════════════════════════════════════════════════════════
hdr "Anti-shortcut defenses"

if strings "${IMG}" | grep -q "number{her_witness_was_still_breathing}"; then
  fail "Plain-text flag found in image! Anti-shortcut defense broken."
else
  pass "No plain-text flag (strings shortcut blocked)"
fi

if strings "${IMG}" | grep -q "her_witness_was_still_breathing"; then
  fail "Flag content (unwrapped) found in plain image bytes"
else
  pass "Flag content not concatenated in plain form"
fi

# ═══════════════════════════════════════════════════════════════════
# 10. BASE64 FRAGMENTS PRESENT IN RAW BYTES
# ═══════════════════════════════════════════════════════════════════
hdr "Base64 fragments recoverable"

FRAG1_B64="aGVyX3dpdG5lc3M="
FRAG2_B64="X3dhc19zdGlsbF9icmVhdGhpbmc="

if strings "${IMG}" | grep -q "${FRAG1_B64}"; then
  pass "Fragment 1 base64 (${FRAG1_B64}) present"
else
  fail "Fragment 1 NOT found in image bytes"
fi

if strings "${IMG}" | grep -q "${FRAG2_B64}"; then
  pass "Fragment 2 base64 (${FRAG2_B64}) present"
else
  fail "Fragment 2 NOT found in image bytes"
fi

# ═══════════════════════════════════════════════════════════════════
# 11. FRAGMENT DECODE & ASSEMBLY MATH CHECK
# ═══════════════════════════════════════════════════════════════════
hdr "Flag assembly math"

F1_DECODED=$(echo -n "${FRAG1_B64}" | base64 -d)
F2_DECODED=$(echo -n "${FRAG2_B64}" | base64 -d)
COMBINED="${F1_DECODED}${F2_DECODED}"
RECONSTRUCTED_FLAG="number{${COMBINED}}"
EXPECTED_FLAG="number{her_witness_was_still_breathing}"

info "Fragment 1 decodes to: ${F1_DECODED}"
info "Fragment 2 decodes to: ${F2_DECODED}"
info "Combined:              ${COMBINED}"
info "Wrapped:               ${RECONSTRUCTED_FLAG}"

if [ "${RECONSTRUCTED_FLAG}" = "${EXPECTED_FLAG}" ]; then
  pass "Reconstructed flag matches expected"
else
  fail "Flag mismatch! Got ${RECONSTRUCTED_FLAG}, expected ${EXPECTED_FLAG}"
fi

# ═══════════════════════════════════════════════════════════════════
# 12. SLEUTHKIT DELETED-FILE RECOVERY (optional)
# ═══════════════════════════════════════════════════════════════════
hdr "Deleted-file recovery"

if command -v fls >/dev/null 2>&1; then
  # fls lists deleted files (marked with *)
  DELETED_COUNT=$(fls -r -d "${IMG}" 2>/dev/null | wc -l)
  info "fls (sleuthkit) reports ${DELETED_COUNT} deleted entries"

  if [ "${DELETED_COUNT}" -ge 5 ]; then
    pass "At least 5 deleted files visible (expected 5: 3 red herrings + 2 operational)"
  elif [ "${DELETED_COUNT}" -ge 3 ]; then
    warn "${DELETED_COUNT} deleted files visible - expected 5"
  else
    fail "Only ${DELETED_COUNT} deleted files visible - recovery may have issues"
  fi

  # Look for the specific filenames we expect
  echo ""
  info "Looking for expected deleted filenames:"
  EXPECTED_DELETED=(
    "birthday_ideas"
    "draft_resignation"
    "password_hints"
    "cipher_note"
    "note_0847"
  )
  for fname in "${EXPECTED_DELETED[@]}"; do
    if fls -r -d "${IMG}" 2>/dev/null | grep -qi "${fname}"; then
      pass "  Deleted entry contains: ${fname}"
    else
      warn "  Could not locate deleted entry: ${fname}"
    fi
  done
else
  warn "sleuthkit (fls) not installed - skipping deleted-file recovery check"
  info "Install with: sudo apt install sleuthkit"
fi

# ═══════════════════════════════════════════════════════════════════
# 13. COMPRESSED SIZE CHECK (if .gz exists)
# ═══════════════════════════════════════════════════════════════════
hdr "Compressed artifact size"

GZ="${IMG}.gz"
if [ -f "${GZ}" ]; then
  GZ_SIZE_BYTES=$(stat -c%s "${GZ}")
  GZ_SIZE_MB=$((GZ_SIZE_BYTES / 1024 / 1024))
  info "Compressed size: ${GZ_SIZE_MB} MB"

  if [ "${GZ_SIZE_MB}" -ge 30 ] && [ "${GZ_SIZE_MB}" -le 250 ]; then
    pass "Compressed size in realistic range (30-250 MB)"
  elif [ "${GZ_SIZE_MB}" -lt 5 ]; then
    fail "Compressed size only ${GZ_SIZE_MB} MB - image likely mostly empty"
  elif [ "${GZ_SIZE_MB}" -lt 30 ]; then
    warn "Compressed size only ${GZ_SIZE_MB} MB - content may still be sparse"
  else
    warn "Compressed size ${GZ_SIZE_MB} MB - larger than expected but functional"
  fi
else
  warn "No .gz file at ${GZ} - compression test skipped"
fi

# ═══════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo -e "  ${BOLD}SUMMARY${NC}"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "  ${GREEN}Passed: ${PASS}${NC}"
echo -e "  ${YELLOW}Warnings: ${WARN}${NC}"
echo -e "  ${RED}Failed: ${FAIL}${NC}"
echo "═══════════════════════════════════════════════════════════════════"

if [ "${FAIL}" -eq 0 ] && [ "${WARN}" -le 2 ]; then
  echo -e "${GREEN}${BOLD}  ✓ F100 artifact looks good. Ship it.${NC}"
  echo ""
  exit 0
elif [ "${FAIL}" -eq 0 ]; then
  echo -e "${YELLOW}${BOLD}  ! F100 has warnings but no failures. Review above.${NC}"
  echo ""
  exit 0
else
  echo -e "${RED}${BOLD}  ✗ F100 has failures. Fix before shipping.${NC}"
  echo ""
  exit 1
fi
