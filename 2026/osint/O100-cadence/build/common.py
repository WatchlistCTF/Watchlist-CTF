"""
O100 *Cadence* - planted truth.

Single source of truth. The generator reads from here; the solver NEVER imports
this (it works from the .docx only).

The lesson: the byline is a costume; the file records the real author, the hour,
and the line they deleted before release.

Two decoy authors (a human name matching the byline + a service account) mean a
one-field read fails. The real author (akessler) is confirmed by three signals:
template path, revision author, and the deleted line's initials. The flag lives
ONLY in the deleted (w:del) paragraph.
"""

# ---------------------------------------------------------------- the flag
FLAG = "number{the_author_is_not_the_byline}"

# ---------------------------------------------------------------- identities
BYLINE = "M. Reyes, Compliance"          # visible signature (decoy 1)
DECOY_CREATOR = "M. Reyes"               # core.xml dc:creator (reinforces decoy 1)
DECOY_LASTMODBY = "svc-docgen"           # core.xml lastModifiedBy (decoy 2: service acct)

REAL_USER = "akessler"                   # the truth - appears in 3 correlating places
REAL_INITIALS = "AK"                     # signs the deleted line

# B200 signpost - planted here (Cadence is the right home; prose/metadata hides it
# naturally, unlike the data-only O200 Manifest). Sits in a revision comment author.
B200_SIGNPOST = "badcode_2014"

# ---------------------------------------------------------------- timestamps
# Authored at 3 a.m. - the cadence tell. Pinned so the .docx is byte-reproducible.
T_CREATED = "2026-09-15T03:14:00Z"
T_MODIFIED = "2026-09-15T03:52:00Z"
T_DELETION = "2026-09-15T03:41:00Z"      # when the line was removed

# ---------------------------------------------------------------- app.xml tells
COMPANY = "Decima Cloud Services"
TEMPLATE_PATH = (
    r"C:\Users\akessler\AppData\Roaming\Microsoft\Templates\NL_internal.dotm"
)
APP_NAME = "Microsoft Office Word"
APP_VERSION = "16.0000"

# ---------------------------------------------------------------- the memo body
MEMO_TITLE = "INTERNAL COMPLIANCE MEMORANDUM"
MEMO_REF = "NL-COMPLIANCE-0915"
MEMO_PARAS = [
    "TO: All Cloud Operations Staff",
    "FROM: M. Reyes, Compliance Office",
    "RE: Q3 Data Handling Attestation",
    "",
    "This memorandum confirms that Decima Cloud Services has completed its "
    "quarterly review of data-handling procedures in accordance with internal "
    "policy DCS-DH-04. All operational teams are reminded to complete the "
    "attestation form by the end of the reporting period.",
    "",
    "No exceptions were identified during this review cycle. Procedures remain "
    "consistent with prior quarters and no remediation is required at this time.",
    "",
    "Questions regarding this attestation may be directed to the Compliance "
    "Office through the standard internal channel.",
    "",
    "M. Reyes",
    "Compliance Office, Decima Cloud Services",
]

# ---------------------------------------------------------------- the DELETED line
# The real author typed this, then deleted it before release. It carries the
# admission + the flag. Recoverable ONLY from the w:del markup.
DELETED_TEXT = (
    f"-- {REAL_INITIALS}: leaving my name off this one. the Q3 audit numbers "
    f"don't reconcile and Reyes won't sign the real version. {FLAG}"
)

# The visible paragraph the deletion is attached to (so the deletion sits inline
# in the document body, as a real edit would).
DELETION_ANCHOR_PARA_INDEX = 6   # after the "No exceptions were identified" para

# ---------------------------------------------------------------- rsid session ids
# Word stamps edit sessions with rsids; the real author's session is consistent.
RSID_SESSION = "00A41D31"


def assert_sane():
    """Fail the build loudly if any load-bearing property is violated."""
    # 1. flag only lives in the deleted text, not in the visible memo
    visible = "\n".join(MEMO_PARAS)
    assert FLAG not in visible, "flag leaked into visible memo text!"
    assert FLAG in DELETED_TEXT, "flag missing from deleted line!"

    # 2. both decoys present and distinct from the real user
    assert DECOY_CREATOR != REAL_USER
    assert DECOY_LASTMODBY != REAL_USER
    assert REAL_USER in TEMPLATE_PATH, "template path must leak the real username"

    # 3. real user's initials sign the deleted line
    assert REAL_INITIALS in DELETED_TEXT

    # 4. the byline names the decoy, not the real author
    assert DECOY_CREATOR.split()[-1] in BYLINE
    assert REAL_USER not in visible, "real username must not appear in visible text"

    # 5. flag well-formed
    assert FLAG.startswith("number{") and FLAG.endswith("}")

    return True


if __name__ == "__main__":
    assert_sane()
    print("planted truth OK")
    print("  flag         :", FLAG)
    print("  byline/decoy :", BYLINE, "/", DECOY_CREATOR, "/", DECOY_LASTMODBY)
    print("  real author  :", REAL_USER, "(via template + rsid + deleted-line initials)")
    print("  deleted line :", DELETED_TEXT[:60], "...")
