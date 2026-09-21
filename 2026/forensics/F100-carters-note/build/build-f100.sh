#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# F100 - CARTER'S NOTE
# Artifact build script v2 (expanded, realistic)
# ═══════════════════════════════════════════════════════════════════
#
# What this builds:
#   - A 300MB FAT32 USB image
#   - Realistic detective's USB backup contents (~30 cases, family photos,
#     reference docs, personal files, HR investigation folder)
#   - 5 deleted files (3 red herrings + 2 operational fragments)
#
# Target final size:
#   - Raw image: 300 MB
#   - Compressed: ~150-220 MB depending on JPG/PDF compression
#
# Requirements (install before running):
#   sudo apt install dosfstools imagemagick python3 python3-reportlab
#   # Or on Fedora/RHEL:
#   sudo dnf install dosfstools ImageMagick python3 python3-reportlab
#
# Usage:
#   chmod +x build-f100.sh
#   ./build-f100.sh
#
# Output:
#   /tmp/f100-build/usb-0412-a.img       (raw)
#   /tmp/f100-build/usb-0412-a.img.gz    (compressed for distribution)
#
# ═══════════════════════════════════════════════════════════════════

set -e

WORK=/tmp/f100-build
IMG="${WORK}/usb-0412-a.img"
MNT="${WORK}/mnt"
IMG_SIZE_MB=300

# Color output for clarity
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[-]${NC} $1"; exit 1; }

# ═══════════════════════════════════════════════════════════════════
# 0. PRE-CHECKS
# ═══════════════════════════════════════════════════════════════════

log "Pre-flight checks..."

for cmd in dd mkfs.vfat sudo mount umount convert python3 sync gzip strings; do
  command -v "$cmd" >/dev/null 2>&1 || err "Missing: $cmd"
done

python3 -c "import reportlab" 2>/dev/null || err "Missing Python: reportlab (pip install reportlab)"

# Clean previous build
sudo umount "${MNT}" 2>/dev/null || true
rm -rf "${WORK}"
mkdir -p "${WORK}" "${MNT}"

# ═══════════════════════════════════════════════════════════════════
# 1. CREATE FAT32 IMAGE
# ═══════════════════════════════════════════════════════════════════

log "Creating ${IMG_SIZE_MB} MB FAT32 image..."
dd if=/dev/zero of="${IMG}" bs=1M count=${IMG_SIZE_MB} status=none
mkfs.vfat -F 32 -n "USB-0412-A" "${IMG}" > /dev/null

log "Mounting image..."
sudo mount -o loop,uid=$(id -u),gid=$(id -g) "${IMG}" "${MNT}"

# ═══════════════════════════════════════════════════════════════════
# 2. PYTHON HELPER: Generate realistic case PDFs
# ═══════════════════════════════════════════════════════════════════

cat > "${WORK}/gen_case_pdf.py" << 'PYEOF'
#!/usr/bin/env python3
"""Generate a realistic-looking redacted case file PDF (multi-page, with embedded image)."""
import sys
import random
import os
import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

CASE_NUM = sys.argv[1]
CASE_TYPE = sys.argv[2]
OUT = sys.argv[3]
DATE = sys.argv[4] if len(sys.argv) > 4 else "REDACTED"
EMBED_IMG = sys.argv[5] if len(sys.argv) > 5 else None  # optional placeholder image path

doc = SimpleDocTemplate(OUT, pagesize=letter,
                        topMargin=0.75*inch, bottomMargin=0.75*inch,
                        leftMargin=0.75*inch, rightMargin=0.75*inch)
styles = getSampleStyleSheet()
header_style = ParagraphStyle('header', parent=styles['Heading1'], fontSize=14, alignment=1)
sub_style = ParagraphStyle('sub', parent=styles['Heading2'], fontSize=11, alignment=0, spaceBefore=12, spaceAfter=6)
body_style = ParagraphStyle('body', parent=styles['Normal'], fontSize=10, leading=14)
small_style = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.grey)

story = []

# ── Page 1: Cover/Summary ────────────────────────────────────────
story.append(Paragraph("NEW YORK POLICE DEPARTMENT - 14th PRECINCT", header_style))
story.append(Paragraph("CASE FILE - REDACTED", header_style))
story.append(Spacer(1, 0.3*inch))

meta = [
    ['Case Number:',          CASE_NUM],
    ['Classification:',       CASE_TYPE],
    ['Date Opened:',          DATE],
    ['Investigating Officer:', 'Det. J. Carter, Badge #████'],
    ['Status:',               random.choice(['Active', 'Closed', 'Under Review', 'Pending DA Decision'])],
    ['Precinct:',             '14th'],
    ['Reviewing Captain:',    '████████████ Moreno'],
    ['IAB Reference:',        f'IAB-2024-{random.randint(1000, 9999)}'],
    ['Evidence Voucher:',     f'EV-████-{random.randint(10000, 99999)}'],
]
table = Table(meta, colWidths=[2.0*inch, 4.0*inch])
table.setStyle(TableStyle([
    ('FONT', (0,0), (-1,-1), 'Helvetica', 10),
    ('FONT', (0,0), (0,-1), 'Helvetica-Bold', 10),
    ('LINEBELOW', (0,0), (-1,-1), 0.25, colors.lightgrey),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('TOPPADDING', (0,0), (-1,-1), 6),
    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
]))
story.append(table)

story.append(PageBreak())

# ── Body: Investigation Notes (3-7 pages of narrative) ──────────
templates = [
    "On {date}, at approximately ████ hours, officers responded to a report of {ctype} at ████████████████████. Upon arrival, ████████████████████████████████████ was observed. ████████████ identified herself as ████████ and provided the following statement: \"████████████████████████████████████████████████████ ██████████████████████████████.\" Evidence collected: ████ items, logged under voucher #████-████. Photographs taken: ████ exposures, archived to ████████.",
    "Witness ████████ (DOB REDACTED, address ████████████████) provided sworn testimony stating ████████████████████████████ ████████████████ ████████████████████████ ████████████████. Witness was interviewed at the 14th Precinct on {date} from ████ to ████ hours. ████████████████ ████████████ ████████████. Witness signed statement ████████████ in the presence of ████████ ████████████.",
    "Forensic analysis of evidence recovered from ████████████ scene yielded ████ latent prints (████ identifiable), ████ samples for DNA processing (sent to ████████████ lab on ████████), and ████ items of physical evidence. All items processed through ████████ chain of custody, log #████-████-████. Initial laboratory findings: ████████████ inconclusive, ████████████ pending, ████████████ excluded.",
    "Subject of interest: ████████ ████████, DOB ██/██/████, last known address ████████████████████████████████. Subject ████████ ████████ ████ ████████████ ████████████████████████. Prior history: ████ arrests for ████████, ████████, ████████, and ████████. Last known associates: ████████, ████████, ████████. Outstanding warrants: ████.",
    "Surveillance footage from ████████████████████ was reviewed for the period ████ to ████ hours on {date}. ████████████████████ was identified entering the location at approximately ████ hours and exiting at ████ hours. Footage timestamps cross-referenced with cell tower data from ████████ carrier. Subject ████████████████ throughout the observation period.",
    "Interview conducted with subject on {date} at ████ hours in interview room ████. Miranda rights administered at ████ hours; subject acknowledged understanding and ████████████████ counsel. Initial statement: \"████████████████████████████████████████████████ ████████████████████████.\" Subject's account ████████████ with physical evidence at ████████████████████████.",
    "Vehicle of interest: ████ ████████████ ████, plate ███ ████, registered to ████████ ████████ of ████████████████████. Vehicle recovered from ████████████████████ on {date}. Forensic sweep of vehicle revealed ████████████████ in trunk, ████████████████ on dashboard, and ████ ████████████████ items in glove compartment. Vehicle impounded under voucher #████-████.",
    "Telephone records subpoenaed under court order ████-████ (Judge ████████████, signed {date}). Records covering period ████████ to ████████ show ████ outgoing calls to subjects of interest, ████ incoming from same. Pattern analysis indicates ████████████████████████████████ during the relevant timeframe. Records sealed; access restricted to lead investigator and ADA ████████████.",
    "Financial records review per Bank Secrecy Act subpoena: subject accounts at ████████████████ Bank show deposits totaling $████,████ over ████ months from ████████████ unknown origin. Cash withdrawals at ATMs in ████ different boroughs, often within ████ hours of ████████████. Suspicious Activity Reports filed ████ times by ████████ different financial institutions.",
    "Cell tower analysis indicates subject's device pinged towers ████, ████, and ████ during the relevant window, placing subject within ████ blocks of the incident location between ████ and ████ hours. Device went dark at ████ hours; came back online at ████ hours at a tower ████ miles away, consistent with vehicle travel time.",
]

# Each PDF gets 4-8 narrative sections (= effectively several pages)
num_sections = random.randint(5, 9)
section_titles = ["Initial Response", "Scene Investigation", "Witness Statements",
                  "Forensic Findings", "Subject Interviews", "Surveillance Review",
                  "Vehicle Examination", "Records Analysis", "Financial Review",
                  "Cellular Records", "Follow-up Actions", "Pending Items"]
random.shuffle(section_titles)

for i in range(num_sections):
    title = section_titles[i] if i < len(section_titles) else f"Supplemental {i}"
    story.append(Paragraph(title, sub_style))
    # 3-5 paragraphs per section
    for _ in range(random.randint(3, 5)):
        text = random.choice(templates).format(date=DATE, ctype=CASE_TYPE.lower())
        story.append(Paragraph(text, body_style))
        story.append(Spacer(1, 0.1*inch))

# Optional embedded image (looks like a redacted photo/diagram)
if EMBED_IMG and os.path.exists(EMBED_IMG):
    story.append(PageBreak())
    story.append(Paragraph("Evidence Photograph - REDACTED", sub_style))
    story.append(Image(EMBED_IMG, width=4.5*inch, height=3.4*inch))
    story.append(Paragraph(f"Photo ID: EV-{CASE_NUM}-001 // Filed: {DATE} // Officer: ████████", small_style))

# Closing
story.append(Spacer(1, 0.3*inch))
story.append(Paragraph(f"<b>Reporting Officer:</b> Det. J. Carter, Badge #████", body_style))
story.append(Paragraph(f"<b>Reviewing Supervisor:</b> ████████████, Badge #████", body_style))
story.append(Paragraph(f"<b>Filed:</b> {DATE}", body_style))
story.append(Paragraph(f"<b>Last Updated:</b> ████████████", body_style))

doc.build(story)
PYEOF

# ═══════════════════════════════════════════════════════════════════
# 3. PYTHON HELPER: Generate reference manual PDFs
# ═══════════════════════════════════════════════════════════════════

cat > "${WORK}/gen_reference_pdf.py" << 'PYEOF'
#!/usr/bin/env python3
"""Generate a reference manual PDF with N pages of plausible content."""
import sys
import os
import random
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.units import inch
from reportlab.lib import colors

TITLE = sys.argv[1]
OUT = sys.argv[2]
PAGES = int(sys.argv[3])
EMBED_IMG = sys.argv[4] if len(sys.argv) > 4 else None

doc = SimpleDocTemplate(OUT, pagesize=letter)
styles = getSampleStyleSheet()
heading_style = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=13, spaceAfter=10)
body_style = ParagraphStyle('body', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=8)

story = []
story.append(Paragraph(TITLE, styles['Title']))
story.append(Spacer(1, 0.3*inch))
story.append(Paragraph("DEPARTMENT REFERENCE MANUAL - FOR INTERNAL USE ONLY", body_style))
story.append(Paragraph("Last revised: REDACTED // Distribution: Restricted to sworn officers", body_style))
story.append(PageBreak())

# Diverse content blocks (more variety = harder to compress)
content_blocks = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae.",
    "At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident, similique sunt in culpa qui officia deserunt mollitia animi.",
    "Procedural note: All officers shall comply with the standards set forth herein. Deviations from documented protocol must be approved in writing by a supervisor of rank Lieutenant or above. Documentation requirements shall be maintained in accordance with Department Order ████-██.",
    "Cross-reference: See also Section ████, Subsection ████, regarding chain-of-custody requirements for evidence recovered at scenes involving multiple suspects or witnesses.",
    "Caution: Failure to adhere to these procedures may result in inadmissibility of evidence at trial. Officers are reminded that the burden of preserving evidentiary integrity rests with the first responding officer and persists through all subsequent transfers.",
]

for page in range(PAGES):
    story.append(Paragraph(f"Section {page+1}: {TITLE} - Part {page+1}", heading_style))
    story.append(Spacer(1, 0.1*inch))
    # 6-10 paragraphs per page (was 5-8 - slightly heavier)
    for _ in range(random.randint(7, 11)):
        story.append(Paragraph(random.choice(content_blocks), body_style))

    # Embed a placeholder figure on every 3rd page
    if EMBED_IMG and os.path.exists(EMBED_IMG) and page % 3 == 0 and page > 0:
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph(f"Figure {page+1}-A: Reference diagram (redacted)", body_style))
        story.append(Image(EMBED_IMG, width=4.0*inch, height=3.0*inch))

    if page < PAGES - 1:
        story.append(PageBreak())

doc.build(story)
PYEOF

chmod +x "${WORK}/gen_case_pdf.py" "${WORK}/gen_reference_pdf.py"

# ═══════════════════════════════════════════════════════════════════
# 4. BUILD DIRECTORY STRUCTURE
# ═══════════════════════════════════════════════════════════════════

log "Creating directory structure..."

mkdir -p "${MNT}/case_files/2024"
mkdir -p "${MNT}/case_files/2023"
mkdir -p "${MNT}/case_files/2022"
mkdir -p "${MNT}/case_files/archive/unsolved_cold"
mkdir -p "${MNT}/case_files/archive/high_profile"
mkdir -p "${MNT}/reference/interview_templates"
mkdir -p "${MNT}/family/2023_vacation"
mkdir -p "${MNT}/family/2024_birthday"
mkdir -p "${MNT}/family/taylor_school"
mkdir -p "${MNT}/family/thanksgiving_2024"
mkdir -p "${MNT}/personal/recipes"
mkdir -p "${MNT}/personal/music"
mkdir -p "${MNT}/HR_investigation/known_dirty"
mkdir -p "${MNT}/HR_investigation/photos/crime_scene_thumbnails"
mkdir -p "${MNT}/HR_investigation/photos/surveillance"

# ═══════════════════════════════════════════════════════════════════
# 4.5 GENERATE SHARED REDACTED IMAGE (embedded in case PDFs)
# ═══════════════════════════════════════════════════════════════════

log "Generating shared redacted-block image for embedding..."

REDACTED_IMG="${WORK}/redacted_block.jpg"
convert -size 800x600 "plasma:#1a1a1a-#3a3a3a" \
  +noise gaussian \
  -fill black -draw "rectangle 100,100 700,500" \
  -fill "#888888" -gravity center \
  -pointsize 32 -annotate +0+0 "REDACTED" \
  -quality 85 "${REDACTED_IMG}"

# ═══════════════════════════════════════════════════════════════════
# 5. GENERATE CASE FILES (2024)
# ═══════════════════════════════════════════════════════════════════

log "Generating 2024 case files (15 cases)..."

CASES_2024=(
  "04-2783|Robbery|01/12/2024"
  "04-2891|Assault|01/28/2024"
  "04-3052|Homicide|02/14/2024"
  "04-3155|Burglary|03/02/2024"
  "04-3201|Assault-DV|03/18/2024"
  "04-3344|Grand Larceny|04/05/2024"
  "04-3422|Robbery|04/22/2024"
  "04-3501|Aggravated Assault|05/11/2024"
  "04-3578|Homicide|06/03/2024"
  "04-3640|Burglary|07/14/2024"
  "04-3712|Robbery|08/01/2024"
  "04-3789|Homicide|08/26/2024"
  "04-3855|Larceny|09/15/2024"
  "04-3920|Assault|10/02/2024"
  "04-4001|Robbery|10/28/2024"
)

for entry in "${CASES_2024[@]}"; do
  IFS='|' read -r num ctype date <<< "$entry"
  fname="${num}_${ctype// /}.pdf"
  python3 "${WORK}/gen_case_pdf.py" "$num" "$ctype" "${MNT}/case_files/2024/${fname}" "$date" "${REDACTED_IMG}"
done

cat > "${MNT}/case_files/2024/case_summary_2024.txt" << 'EOF'
2024 caseload summary - running notes
========================================

Total active: 15
Closed: 4
Pending DA: 3
Cold: 0

Year-to-date observations:
- Robbery pattern in 24th district week 14-18 - same MO
- 03-2891 victim refused to ID - suspect known to her
- 03-3052 - connected to 03-3578? Same neighborhood, similar wound pattern
- Need to revisit 03-3344 in Jan - DA wants more forensics

Personal note: Captain wants me to take on the Quinn task force
work. I'm declining. He doesn't know why.

- J
EOF

# ═══════════════════════════════════════════════════════════════════
# 6. GENERATE CASE FILES (2023 - 12 cases)
# ═══════════════════════════════════════════════════════════════════

log "Generating 2023 case files (12 cases)..."

CASES_2023=(
  "03-2218|Homicide|01/08/2023"
  "03-2456|Robbery|02/14/2023"
  "03-2589|Burglary|03/22/2023"
  "03-2701|Assault|04/15/2023"
  "03-2834|Larceny|05/07/2023"
  "03-2978|Homicide|06/01/2023"
  "03-3055|Robbery|07/19/2023"
  "03-3128|Aggravated Assault|08/12/2023"
  "03-3201|Burglary|09/05/2023"
  "03-3287|Homicide|10/02/2023"
  "03-3344|Grand Larceny|11/14/2023"
  "03-3422|Robbery|12/19/2023"
)

for entry in "${CASES_2023[@]}"; do
  IFS='|' read -r num ctype date <<< "$entry"
  fname="${num}_${ctype// /}.pdf"
  python3 "${WORK}/gen_case_pdf.py" "$num" "$ctype" "${MNT}/case_files/2023/${fname}" "$date" "${REDACTED_IMG}"
done

cat > "${MNT}/case_files/2023/case_summary_2023.txt" << 'EOF'
2023 caseload summary
=====================

Total worked: 12
Closed: 8
Cold: 1 (03-2978 - see notes)
Unresolved: 3

03-2978 stuck with me. Witness said she saw a uniform leaving
the scene. Internal review went nowhere. Captain told me to
drop it.

I have not dropped it.

- J
EOF

# ═══════════════════════════════════════════════════════════════════
# 7. GENERATE CASE FILES (2022 - 8 cases)
# ═══════════════════════════════════════════════════════════════════

log "Generating 2022 case files (8 cases)..."

CASES_2022=(
  "02-1547|Homicide|02/03/2022"
  "02-1689|Robbery|03/22/2022"
  "02-1823|Burglary|05/14/2022"
  "02-1967|Assault|07/02/2022"
  "02-2105|Larceny|08/19/2022"
  "02-2244|Homicide|09/30/2022"
  "02-2389|Robbery|11/11/2022"
  "02-2501|Aggravated Assault|12/27/2022"
)

for entry in "${CASES_2022[@]}"; do
  IFS='|' read -r num ctype date <<< "$entry"
  fname="${num}_${ctype// /}.pdf"
  python3 "${WORK}/gen_case_pdf.py" "$num" "$ctype" "${MNT}/case_files/2022/${fname}" "$date" "${REDACTED_IMG}"
done

cat > "${MNT}/case_files/2022/case_summary_2022.txt" << 'EOF'
2022 caseload summary
=====================

Total worked: 8 (lighter year - extended leave Q2)
Closed: 6
Cold: 2

The two cold ones (02-1547 and 02-2244) - both vics had
no obvious enemies, both cleanly executed. Different
neighborhoods, different MOs, different weapons.

But the timing bothers me. Both within a week of each
other being witness to something. Both about to testify.

- J
EOF

# ═══════════════════════════════════════════════════════════════════
# 8. ARCHIVE FOLDER (cold cases + high profile)
# ═══════════════════════════════════════════════════════════════════

log "Generating archive case files..."

# Cold cases - including PoI Easter eggs
python3 "${WORK}/gen_case_pdf.py" "02-1547" "Cold-Homicide-ELIAS-assoc" "${MNT}/case_files/archive/unsolved_cold/02-1547_homicide_ELIAS_assoc.pdf" "02/03/2022" "${REDACTED_IMG}"
python3 "${WORK}/gen_case_pdf.py" "01-0834" "Disappearance" "${MNT}/case_files/archive/unsolved_cold/01-0834_disappearance.pdf" "07/19/2021" "${REDACTED_IMG}"
python3 "${WORK}/gen_case_pdf.py" "02-2244" "Cold-Homicide" "${MNT}/case_files/archive/unsolved_cold/02-2244_homicide.pdf" "09/30/2022" "${REDACTED_IMG}"

cat > "${MNT}/case_files/archive/unsolved_cold/notes_cold_review.txt" << 'EOF'
Notes - cold case review (personal, not for file)
==================================================

Three cases I keep coming back to:

1. 02-1547 (BENTON, R.) - homicide, no suspects.
   Witness saw possible police involvement. Witness
   later recanted. Witness now deceased.

2. 01-0834 (████████, ████) - disappearance, no body.
   Last contact with subject was a phone call to
   an unlisted number. Number traced to a payphone.

3. 02-2244 (████████) - homicide. About to testify
   on an unrelated corruption case. Killed three
   days before scheduled deposition.

The pattern across these and others I haven't pulled yet:
witnesses to police corruption who don't make it to testify.

I am not the first detective to notice this. I am the
first to write it down.

- J
EOF

# High-profile cases
python3 "${WORK}/gen_case_pdf.py" "04-3022" "Homicide-Benton" "${MNT}/case_files/archive/high_profile/04-3022_BENTON_homicide.pdf" "10/15/2024" "${REDACTED_IMG}"
python3 "${WORK}/gen_case_pdf.py" "03-2891" "Internal-Affairs-Review" "${MNT}/case_files/archive/high_profile/03-2891_internal_review.pdf" "08/05/2023" "${REDACTED_IMG}"

# ═══════════════════════════════════════════════════════════════════
# 9. REFERENCE DOCS
# ═══════════════════════════════════════════════════════════════════

log "Generating reference documents..."

python3 "${WORK}/gen_reference_pdf.py" "NY Penal Code Quick Reference 2024" "${MNT}/reference/ny_penal_code_2024.pdf" 20 "${REDACTED_IMG}"
python3 "${WORK}/gen_reference_pdf.py" "NYPD Homicide Investigation Manual" "${MNT}/reference/nypd_homicide_manual.pdf" 30 "${REDACTED_IMG}"
python3 "${WORK}/gen_reference_pdf.py" "Interrogation Techniques Reference" "${MNT}/reference/interrogation_techniques.pdf" 15 "${REDACTED_IMG}"
python3 "${WORK}/gen_reference_pdf.py" "Crime Scene Protocol Quick Guide" "${MNT}/reference/crime_scene_protocol.pdf" 12 "${REDACTED_IMG}"

cat > "${MNT}/reference/interview_templates/witness.docx" << 'EOF'
WITNESS INTERVIEW TEMPLATE - INTERNAL USE
==========================================

Subject: ____________________
Date: ____________________
Officer: ____________________

1. Identify the witness (full legal name, DOB, address, contact)
2. Establish presence at scene (where were they, what time)
3. Establish relationship to victim/suspect (if any)
4. Get narrative in their own words FIRST - don't interrupt
5. Clarifying questions AFTER narrative
6. Read back, confirm accuracy, get signature

Notes: Always record. Always have a second officer present
if possible. Document everything - what they wear, mannerisms,
whether they're being coached by anyone present.
EOF

cat > "${MNT}/reference/interview_templates/suspect.docx" << 'EOF'
SUSPECT INTERVIEW TEMPLATE - INTERNAL USE
==========================================

CRITICAL: Miranda before any questioning. Document time of
Miranda. Document waiver. If subject requests counsel, STOP.

1. Establish identity
2. Read rights - confirm understanding
3. Document Miranda time + waiver (or invocation)
4. If waived: proceed with open-ended questions first
5. Confront with evidence selectively - preserve leverage
6. Document everything verbatim where possible

- J
EOF

cat > "${MNT}/reference/interview_templates/victim.docx" << 'EOF'
VICTIM INTERVIEW TEMPLATE - INTERNAL USE
==========================================

This is the hardest one. Be patient. Be quiet.

1. Establish safety FIRST - are they OK, do they need medical
2. Let them tell their story without interruption
3. Take notes minimally - they need eye contact, not paperwork
4. Ask if they want a victim advocate present
5. Document what they say, but ALSO document what they don't
6. Follow up. Always follow up. Don't be the cop who didn't.

- J
EOF

# ═══════════════════════════════════════════════════════════════════
# 10. FAMILY PHOTOS (realistic generated JPGs)
# ═══════════════════════════════════════════════════════════════════

log "Generating family photos (this takes a moment - realistic content)..."

# Generate a realistic JPG using plasma fractal + noise.
# These DON'T compress well - that's the point.
# Target size per photo: ~500KB-1.5MB at 1920x1440, quality 92.
make_photo() {
  local path="$1"
  local label="$2"
  local hue="$3"  # tint color
  local seed=$RANDOM
  convert -size 1920x1440 "plasma:${hue}-${hue}" \
    -seed "${seed}" \
    +noise gaussian \
    -modulate 100,30 \
    -blur 0x1.2 \
    -fill "white" -gravity south \
    -pointsize 28 -annotate +0+30 "$label" \
    -quality 92 "$path"
}

# Vacation 2023 (15 photos) - warmer tones
for i in $(seq -f "%04g" 4521 4535); do
  make_photo "${MNT}/family/2023_vacation/IMG_${i}.jpg" "vacation 2023" "tomato"
done

# Birthday 2024 (10 photos) - bright tones
for i in $(seq -f "%04g" 5012 5021); do
  make_photo "${MNT}/family/2024_birthday/IMG_${i}.jpg" "taylor birthday" "gold"
done

# Taylor school (6 photos) - blue tones
for i in $(seq -f "%04g" 4001 4006); do
  make_photo "${MNT}/family/taylor_school/IMG_${i}.jpg" "taylor school" "steelblue"
done

# Thanksgiving (5 photos) - autumn tones
for i in $(seq -f "%04g" 4801 4805); do
  make_photo "${MNT}/family/thanksgiving_2024/IMG_${i}.jpg" "thanksgiving" "chocolate"
done

# ═══════════════════════════════════════════════════════════════════
# 11. PERSONAL FILES
# ═══════════════════════════════════════════════════════════════════

log "Creating personal files..."

cat > "${MNT}/personal/coffee_order.txt" << 'EOF'
two sugars, no cream
or one sugar with milk if they're out of cream
or just black if I'm pretending to be tough
EOF

cat > "${MNT}/personal/numbers_lottery.txt" << 'EOF'
this week's picks:
07, 14, 22, 31, 38, 46
mega: 12

last week:
03, 11, 19, 27, 33, 41
mega: 08
(zero matches. as usual.)

note to self: the numbers don't pick you. I keep forgetting that.
EOF

cat > "${MNT}/personal/grocery.txt" << 'EOF'
milk
bread
eggs
chicken
something for Taylor's lunch (NOT chips again)
coffee - bigger bag this time
EOF

cat > "${MNT}/personal/reminders.txt" << 'EOF'
- Taylor's parent-teacher: Thursday, 4pm
- Mom's birthday: 14th, get card EARLIER this year
- Annual physical: overdue, schedule it
- Pay water bill before the 20th
- Renew badge ID - expires next month
EOF

cat > "${MNT}/personal/taylor_basketball_schedule.pdf" << 'EOF'
TAYLOR CARTER - JV BASKETBALL SCHEDULE
======================================

Practice: Tues / Thurs, 4:00 - 5:30 PM
Games:    Most Fridays, 6:00 PM home / varies away

Sept 12 - vs. Lincoln (home)
Sept 19 - at Madison (away)
Sept 26 - vs. Truman (home)
Oct  03 - at Roosevelt (away)
Oct  10 - vs. Jefferson (home)
[remainder of season redacted for brevity]

Coach: Patterson
EOF

cat > "${MNT}/personal/recipes/mom_lasagna.txt" << 'EOF'
mom's lasagna
=============

(her actual recipe - don't change it)

1 lb ground beef
1 lb italian sausage
2 jars marinara (the brand mom uses, not the cheap one)
1 lb ricotta
2 cups mozzarella shredded
1/2 cup parmesan
1 egg
fresh basil
lasagna noodles (no-boil are fine, fight me on this)

brown meat, mix ricotta + egg + parmesan + basil
layer: sauce / noodles / ricotta mix / meat / cheese
repeat 3 times
bake 375 for 45 min, covered for 30, uncovered for 15

let it sit 10 min before cutting or it falls apart
EOF

cat > "${MNT}/personal/recipes/chocolate_chip.txt" << 'EOF'
chocolate chip cookies - Taylor's favorite
==========================================

2 1/4 cups flour
1 tsp baking soda
1 tsp salt
1 cup butter (softened)
3/4 cup sugar
3/4 cup brown sugar
2 eggs
1 tsp vanilla
2 cups chocolate chips

cream butter + sugars
add eggs + vanilla
add dry ingredients
fold in chips

bake 375 for 9-11 minutes
let cool on the sheet for 2 min before moving

makes ~3 dozen if Taylor doesn't eat the dough
EOF

cat > "${MNT}/personal/recipes/thanksgiving_turkey.txt" << 'EOF'
thanksgiving turkey method
==========================

dry brine 24-48 hours ahead. salt + pepper + thyme.

day-of:
- room temp 1 hour before roasting
- 425 for first 30 min
- drop to 325 until 160 internal (breast)
- rest 30 min minimum

stuffing OUTSIDE the bird. always. mom is wrong about this
and I will die on this hill.
EOF

cat > "${MNT}/personal/music/workout.m3u" << 'EOF'
#EXTM3U
#EXTINF:0,Aretha Franklin - Respect
Respect.mp3
#EXTINF:0,James Brown - Get Up
GetUp.mp3
#EXTINF:0,Lizzo - Good as Hell
GoodAsHell.mp3
#EXTINF:0,Whitney Houston - I Wanna Dance with Somebody
IWannaDance.mp3
EOF

cat > "${MNT}/personal/music/focus.m3u" << 'EOF'
#EXTM3U
#EXTINF:0,Miles Davis - Kind of Blue
KindOfBlue.mp3
#EXTINF:0,John Coltrane - A Love Supreme
ALoveSupreme.mp3
#EXTINF:0,Nina Simone - Feeling Good
FeelingGood.mp3
EOF

cat > "${MNT}/personal/music/road_trip.m3u" << 'EOF'
#EXTM3U
#EXTINF:0,Marvin Gaye - What's Going On
WhatsGoingOn.mp3
#EXTINF:0,Stevie Wonder - Superstition
Superstition.mp3
EOF

# ═══════════════════════════════════════════════════════════════════
# 12. HR INVESTIGATION FOLDER (Carter's secret work - worldbuilding)
# ═══════════════════════════════════════════════════════════════════

log "Creating HR_investigation folder..."

cat > "${MNT}/HR_investigation/notes_to_self.txt" << 'EOF'
HR investigation - running notes
================================

This is for me. Not for the file. Not for the precinct.
Not for anyone who works in this building.

What I know:
- HR is real. Multiple officers across multiple precincts.
- They've been operating since at least 2018, possibly earlier.
- They use precinct resources for non-precinct work.
- They eliminate witnesses to corruption - including civilians.
- They have at least one captain-level cover.

What I don't know:
- Full membership list.
- Who at HQ knows and is looking the other way.
- Whether IAB is compromised.
- How they communicate when they don't trust the system.

What I'm doing:
- Building a list of suspected members (see known_dirty/).
- Documenting timeline (see timeline_2024.txt).
- Cross-referencing with cold cases (see archive/).
- Not telling anyone what I'm doing.

If something happens to me - the truth is in pieces.
The pieces are deliberate.

- J
EOF

cat > "${MNT}/HR_investigation/known_dirty/officer_simmons_notes.txt" << 'EOF'
Officer Patrick SIMMONS - observations
======================================

Badge: ████
Precinct: 14th (us)
Years on: ~12

Why he's on the list:
- Three times I've seen him meeting with subjects
  he had no reason to be meeting with
- His arrest reports always have gaps
- His witnesses tend to disappear
- He has a side income he can't explain

Not enough for a charge. Enough for a watch.

- J
EOF

cat > "${MNT}/HR_investigation/known_dirty/officer_terney_notes.txt" << 'EOF'
Officer Michael TERNEY - observations
======================================

Badge: ████
Precinct: 14th (us)
Years on: ~8

Why he's on the list:
- Simmons's partner
- Always backs Simmons's story
- Has been overheard taking calls in code
- Wife drives a car he can't afford on his salary

- J
EOF

cat > "${MNT}/HR_investigation/known_dirty/lt_quinn_notes.txt" << 'EOF'
Lt. Patrick QUINN - observations
================================

Badge: ████
Rank: Lieutenant
Years on: ~22

Why he's at the top of the list:
- He chooses the cases. He chooses who works them.
- He shut down the Benton investigation personally.
- He has access to every precinct's case files
  via the regional task force.
- He's the only common thread across the cold cases
  I've found.

He is dangerous. He is connected.
If I confront him, I lose. If I prove it, he loses.

The proof is what I am working on.

- J
EOF

cat > "${MNT}/HR_investigation/connections.txt" << 'EOF'
Connection map - Operation HR
=============================

Suspected node graph (as understood, 11/01/2024):

       Lt. QUINN (14th, central)
        /     |     \
   SIMMONS  TERNEY   ████████
   (14th)   (14th)   (5th?)
      \      |        /
       \     |       /
        cases pulled / suppressed
                |
        cold case bodies
        (Benton, ████████, ████████)

Quinn is the conductor. The officers are the orchestra.
There's at least one more. Maybe two.

I don't know who pays them or who they answer to
above Quinn. That's the next layer.

I am one detective. This is too big for one detective.

But it is mine until it isn't.

- J
EOF

cat > "${MNT}/HR_investigation/timeline_2024.txt" << 'EOF'
HR timeline - 2024 observations
================================

Jan 12 - Database query log shows Quinn pulled BENTON file (case closed in 2022, no reason to pull)
Feb 03 - Benton family reports anonymous threat. No record filed.
Feb 14 - Simmons photographed entering a known HR hangout (Tortilla)
Mar 02 - Database query log: Quinn pulled three additional cold case files in one night
Mar 18 - Witness in 04-3201 (DV case) recants statement after visit from "officer" - unnamed
Apr 05 - Terney was overtime on a night his shift was off. No incident reports filed.
Apr 22 - Anonymous tipline call mentions HR by name. Call transcript "lost" in routing.
May 11 - I find draft of suppressed report in shared drive. Saved a copy.
Jun 03 - Quinn assigned me to a task force I declined. He asked why. I said personal reasons.
Aug 26 - Captain Moreno hints that I'm being watched. Doesn't say by whom.
Oct 02 - Three names appear in database access log in two weeks. All flagged with same query pattern.
Nov 08 - I am writing this. They don't know I know.
EOF

# Generate realistic surveillance photos (dark, grainy, consistent with the theme)
for i in $(seq 1 4); do
  convert -size 1600x1200 "plasma:#1a1a1a-#3a3a3a" \
    -seed $RANDOM \
    +noise gaussian \
    -modulate 80,20 \
    -blur 0x1.5 \
    -fill "#888888" -gravity south \
    -pointsize 22 -annotate +0+20 "surveillance ${i} - REDACTED" \
    -quality 88 "${MNT}/HR_investigation/photos/surveillance/surv_${i}.jpg"
done

# Crime scene thumbnails (even darker, more processed look)
for i in $(seq 1 5); do
  convert -size 1600x1200 "plasma:#0f0f0f-#2a2a2a" \
    -seed $RANDOM \
    +noise gaussian \
    -modulate 70,15 \
    -blur 0x1.8 \
    -fill "#777777" -gravity south \
    -pointsize 22 -annotate +0+20 "scene ${i} - REDACTED" \
    -quality 88 "${MNT}/HR_investigation/photos/crime_scene_thumbnails/scene_${i}.jpg"
done

# ═══════════════════════════════════════════════════════════════════
# 13. README (sets the tone for visitors to the drive)
# ═══════════════════════════════════════════════════════════════════

cat > "${MNT}/readme.txt" << 'EOF'
This is a backup. Don't tell IT.

- Joss
EOF

# ═══════════════════════════════════════════════════════════════════
# 14. CREATE THE FILES WE'LL DELETE
# ═══════════════════════════════════════════════════════════════════

log "Creating the files that will be deleted..."

# RED HERRING 1: birthday ideas (mundane)
cat > "${MNT}/personal/birthday_ideas.txt" << 'EOF'
Taylor turns 16 next month. Maybe a watch.
Or the laptop he's been asking for.
Or just dinner at his favorite place - that
might mean more to him than I think.

Need to ask Mom what she's getting him so we
don't double up like last year.
EOF

# RED HERRING 2: draft resignation (emotional decoy)
cat > "${MNT}/case_files/2024/draft_resignation.docx" << 'EOF'
To Captain Moreno:

I can't do this job if it means looking the
other way. I'm not writing this to actually
file it. I'm writing this because I needed
to see the words on the page.

Tomorrow I'll go back. Tomorrow I'll keep
working. But tonight I needed to write this.

- J. Carter
EOF

# RED HERRING 3: password hints (tempting but unrelated)
cat > "${MNT}/personal/password_hints.txt" << 'EOF'
hints for me only:
- bank: first dog + first apartment number
- email: mom's maiden + birth year
- precinct system: precinct number + badge

NEVER write the actual passwords.
NEVER let anyone see this file.

I am writing this and immediately regretting it.
EOF

# OPERATIONAL FILE 1: hidden cipher note (fragment 1)
# fragment 1 base64 = aGVyX3dpdG5lc3M=  (decodes to "her_witness")
cat > "${MNT}/personal/.cipher_note" << 'EOF'
Reminder to self:
The lock on the back door needs WD-40.
Pick up Taylor's prescription Thursday.
The thing I cannot say:

aGVyX3dpdG5lc3M=

- J
EOF

# OPERATIONAL FILE 2: the main note (fragment 2 + instructions)
# fragment 2 base64 = X3dhc19zdGlsbF9icmVhdGhpbmc=  (decodes to "_was_still_breathing")
cat > "${MNT}/case_files/2024/note_0847.txt" << 'EOF'
From the desk of D. Carter / 14th Precinct
Date: 11/08 - DO NOT FILE - DO NOT QUERY

Pulled the database access log last night. Three names
in two weeks. All flagged with the same query pattern.
All dead within 30 days of the query.

This isn't random. Someone has access to the system
and is using it as a kill list. Not the perps. The vics.

I can't put this anywhere they can see it. If I'm wrong,
my career. If I'm right, it's worse.

If you found this - listen.

The number is in two pieces. I split them.
First piece is with the household reminders.
Second piece is here:

X3dhc19zdGlsbF9icmVhdGhpbmc=

Read both. Combine. Wrap in the format.

- Joss
EOF

# ═══════════════════════════════════════════════════════════════════
# 15. DELETE THE FILES (this is what makes them recoverable)
# ═══════════════════════════════════════════════════════════════════

sync
sleep 1

log "Deleting the planted files (so they become recoverable)..."

rm "${MNT}/personal/birthday_ideas.txt"
rm "${MNT}/case_files/2024/draft_resignation.docx"
rm "${MNT}/personal/password_hints.txt"
rm "${MNT}/personal/.cipher_note"
rm "${MNT}/case_files/2024/note_0847.txt"

sync
sleep 1

# ═══════════════════════════════════════════════════════════════════
# 16. UNMOUNT & VERIFY
# ═══════════════════════════════════════════════════════════════════

log "Unmounting image..."
sudo umount "${MNT}"

log "Verifying anti-shortcut defenses..."

# Anti-shortcut: confirm flag NOT present as plain text
if strings "${IMG}" | grep -q "number{her_witness_was_still_breathing}"; then
  err "Flag found as plain string! Defense broken."
else
  log "  ✓ No plaintext flag in image (strings shortcut blocked)"
fi

# Verify fragment 1 present
if strings "${IMG}" | grep -q "aGVyX3dpdG5lc3M="; then
  log "  ✓ Fragment 1 base64 present in image bytes"
else
  err "Fragment 1 NOT found - investigate"
fi

# Verify fragment 2 present
if strings "${IMG}" | grep -q "X3dhc19zdGlsbF9icmVhdGhpbmc="; then
  log "  ✓ Fragment 2 base64 present in image bytes"
else
  err "Fragment 2 NOT found - investigate"
fi

# ═══════════════════════════════════════════════════════════════════
# 17. COMPRESS FOR DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════

log "Compressing for distribution..."
gzip -9 -k "${IMG}"

# ═══════════════════════════════════════════════════════════════════
# 18. FINAL REPORT
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "F100 - CARTER'S NOTE - Build complete"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
log "Raw image:    ${IMG}"
log "Compressed:   ${IMG}.gz"
echo ""
ls -lh "${IMG}" "${IMG}.gz" | awk '{print "  " $5 "  " $9}'
echo ""
echo "Next steps:"
echo "  1. Test with Autopsy: open ${IMG} and confirm 5 deleted files appear"
echo "  2. Verify recoverable text content"
echo "  3. Verify base64 fragments decode and combine correctly"
echo "  4. Upload ${IMG}.gz to CTFd / S3 / R2 for distribution"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
