#!/usr/bin/env python3
"""
O100 *Cadence* - reference solver / answer key.

Works from the .docx ONLY. Does not import common.py.

  python3 solve_o100.py [file.docx]     (default: ../files/7ac6142bb8e8c0ea.docx)
  Needs only the Python 3 standard library. No network access.

Stages:
  01 the memo text says nothing
  02 read metadata -> find the pointers, reject the two decoy authors
  03 open the container -> recover the deleted (w:del) paragraph
  04 the flag is in the deleted text; confirm the real author correlates
"""

import re
import sys
import zipfile

PASS = 0
FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {label}" + (f": {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f": {detail}" if detail else ""))
    return cond


def main(path):
    print("=" * 70)
    print(" O100 CADENCE - reference solve")
    print("=" * 70)

    z = zipfile.ZipFile(path)
    core = z.read("docProps/core.xml").decode()
    app = z.read("docProps/app.xml").decode()
    doc = z.read("word/document.xml").decode()

    # ---------------------------------------------------------- STAGE 01
    print("\n[STAGE 01] The memo text says nothing")
    # extract visible paragraph text (w:t runs, NOT w:delText)
    visible = " ".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc))
    check("no flag in the visible memo text", "number{" not in visible,
          "the answer is not in what it says")

    # ---------------------------------------------------------- STAGE 02
    print("\n[STAGE 02] Read metadata - find pointers, reject decoy authors")
    creator = _tag(core, "dc:creator")
    lastmod = _tag(core, "cp:lastModifiedBy")
    created = _tag(core, "dcterms:created")
    template = _tag(app, "Template")
    print(f"    dc:creator       = {creator!r}   (matches byline? decoy)")
    print(f"    lastModifiedBy   = {lastmod!r}   (service account? decoy)")
    print(f"    created          = {created!r}")
    print(f"    template         = {template!r}")

    check("two author fields look authoritative but disagree",
          creator and lastmod and creator != lastmod,
          f"{creator} vs {lastmod}")
    check("document was authored at an odd hour (cadence tell)",
          created and "T0" in created and int(created[11:13]) < 6,
          f"created {created}")
    # the template path leaks a username that is NEITHER decoy
    user = None
    m = re.search(r"Users\\([^\\]+)\\", template or "")
    if m:
        user = m.group(1)
    check("template path leaks a username that matches no author field",
          user and user != creator and user != lastmod,
          f"template username = {user!r}")

    # ---------------------------------------------------------- STAGE 03
    print("\n[STAGE 03] Open the container - recover the deleted paragraph")
    del_author = None
    m = re.search(r'<w:del [^>]*w:author="([^"]+)"', doc)
    if m:
        del_author = m.group(1)
    deleted = "".join(re.findall(r"<w:delText[^>]*>([^<]*)</w:delText>", doc))
    check("a tracked deletion exists", bool(deleted), f"{len(deleted)} chars recovered")
    check("the deletion's author matches the template-path username",
          del_author and del_author == user, f"del author = {del_author!r}")

    # ---------------------------------------------------------- STAGE 04
    print("\n[STAGE 04] The flag is in the deleted text")
    print(f"    recovered deleted line:\n      {deleted}")
    m = re.search(r"number\{[^}]+\}", deleted)
    flag = m.group(0) if m else None
    check("flag recovered from the deleted text", bool(flag), flag)

    # confirm the real author is corroborated by 3 independent signals
    initials = "".join(w[0] for w in (user or "").split(".")).upper() if user else ""
    # deleted line is signed with initials; check they appear
    signed = bool(re.search(r"--\s*([A-Z]{2})\s*:", deleted))
    check("real author corroborated (template + del-author + signed initials)",
          bool(user) and del_author == user and signed,
          f"user={user}, del_author={del_author}, signed={signed}")

    if flag:
        print(f"\n    FLAG: {flag}")
        check("assembled flag matches expected",
              flag == "number{the_author_is_not_the_byline}", flag)

    return finish()


def _tag(xml, tag):
    m = re.search(rf"<{tag}[^>]*>([^<]*)</{tag}>", xml)
    return m.group(1) if m else None


def finish():
    print("\n" + "=" * 70)
    print(f" RESULT: {PASS}/{PASS+FAIL} checks passed")
    print("=" * 70)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    import os
    default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "files", "7ac6142bb8e8c0ea.docx")
    p = sys.argv[1] if len(sys.argv) > 1 else default
    sys.exit(main(p))
