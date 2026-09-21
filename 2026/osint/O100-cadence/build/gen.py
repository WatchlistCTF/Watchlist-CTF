#!/usr/bin/env python3
"""
O100 *Cadence* - generator.

Builds NL-COMPLIANCE-0915.docx:
  - a bland compliance memo (visible text says nothing)
  - core.xml : dc:creator=M. Reyes (decoy), lastModifiedBy=svc-docgen (decoy),
               3 a.m. created/modified timestamps
  - app.xml  : Template path leaking the real username, Company
  - document.xml : a real w:del/w:delText tracked deletion (author=akessler)
               carrying the admission + the flag

Deterministic: pinned timestamps => byte-reproducible.
"""

import argparse
import io
import os
import re
import zipfile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

import common as C


def _build_base_docx():
    """The visible memo, plus the inline deletion, as an in-memory docx."""
    d = Document()

    # core properties we can set via the API (creator + created/modified)
    cp = d.core_properties
    cp.author = C.DECOY_CREATOR          # dc:creator (decoy 1)
    cp.last_modified_by = C.DECOY_LASTMODBY  # cp:lastModifiedBy (decoy 2)
    cp.title = C.MEMO_TITLE
    cp.category = "Compliance"
    # created/modified set here, but python-docx writes them as the current tz;
    # we normalize the exact strings during the zip rewrite for reproducibility.

    d.add_heading(C.MEMO_TITLE, level=1)
    d.add_paragraph(f"Ref: {C.MEMO_REF}")

    anchor_para = None
    body_paras = [p for p in C.MEMO_PARAS]
    for i, text in enumerate(body_paras):
        p = d.add_paragraph(text)
        if i == C.DELETION_ANCHOR_PARA_INDEX:
            anchor_para = p

    if anchor_para is None:
        anchor_para = d.add_paragraph("")

    # --- inject a REAL tracked deletion into the anchor paragraph ---
    # <w:del w:author="akessler" w:date="..."><w:r><w:delText>...</w:delText></w:r></w:del>
    delel = OxmlElement("w:del")
    delel.set(qn("w:author"), C.REAL_USER)
    delel.set(qn("w:date"), C.T_DELETION)
    delel.set(qn("w:id"), "1")
    run = OxmlElement("w:r")
    # rPr with an rsid so it reads as a real edit session
    rpr = OxmlElement("w:rPr")
    run.append(rpr)
    dt = OxmlElement("w:delText")
    dt.set(qn("xml:space"), "preserve")
    dt.text = C.DELETED_TEXT
    run.append(dt)
    delel.append(run)
    anchor_para._p.append(delel)

    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _patch_and_normalize(raw):
    """
    Rewrite the docx zip to:
      - normalize core.xml timestamps (reproducibility + the 3 a.m. tell)
      - set lastModifiedBy to the service-account decoy
      - inject Template path + Company + rsid into app.xml / settings.xml
      - pin all zip member mtimes
    """
    src = zipfile.ZipFile(io.BytesIO(raw))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(src.namelist()):
            data = src.read(name)

            if name == "docProps/core.xml":
                text = data.decode()
                # pin created/modified to the planted 3 a.m. values
                text = re.sub(
                    r"(<dcterms:created[^>]*>)[^<]*(</dcterms:created>)",
                    r"\g<1>" + C.T_CREATED + r"\g<2>", text)
                text = re.sub(
                    r"(<dcterms:modified[^>]*>)[^<]*(</dcterms:modified>)",
                    r"\g<1>" + C.T_MODIFIED + r"\g<2>", text)
                # ensure lastModifiedBy is the decoy service account
                if "lastModifiedBy" in text:
                    text = re.sub(
                        r"(<cp:lastModifiedBy>)[^<]*(</cp:lastModifiedBy>)",
                        r"\g<1>" + C.DECOY_LASTMODBY + r"\g<2>", text)
                else:
                    text = text.replace(
                        "</cp:coreProperties>",
                        f"<cp:lastModifiedBy>{C.DECOY_LASTMODBY}</cp:lastModifiedBy>"
                        "</cp:coreProperties>")
                data = text.encode()

            elif name == "docProps/app.xml":
                text = data.decode()
                # inject Template + Company (the username tell lives in Template)
                inject = (f"<Template>{_xml_escape(C.TEMPLATE_PATH)}</Template>"
                          f"<Company>{C.COMPANY}</Company>")
                if "</Properties>" in text:
                    # avoid duplicating a Company tag if present
                    text = re.sub(r"<Company>[^<]*</Company>", "", text)
                    text = re.sub(r"<Template>[^<]*</Template>", "", text)
                    text = text.replace("</Properties>", inject + "</Properties>")
                data = text.encode()

            elif name == "word/settings.xml":
                text = data.decode()
                # add an rsid session so the edit reads as a real Word session
                rsids = (f'<w:rsids><w:rsidRoot w:val="{C.RSID_SESSION}"/>'
                         f'<w:rsid w:val="{C.RSID_SESSION}"/></w:rsids>')
                if "<w:rsids>" not in text and "</w:settings>" in text:
                    text = text.replace("</w:settings>", rsids + "</w:settings>")
                data = text.encode()

            # pin mtime for reproducibility
            zi = zipfile.ZipInfo(name, date_time=(2026, 9, 15, 3, 52, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o600 << 16
            z.writestr(zi, data)

    return out.getvalue()


def _xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def generate(out_dir):
    C.assert_sane()
    os.makedirs(out_dir, exist_ok=True)
    raw = _build_base_docx()
    final = _patch_and_normalize(raw)
    path = os.path.join(out_dir, "NL-COMPLIANCE-0915.docx")
    with open(path, "wb") as f:
        f.write(final)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../build")
    args = ap.parse_args()
    p = generate(args.out)
    print("[*] O100 Cadence generated")
    print(f"    file : {os.path.getsize(p)} B  {p}")
    print(f"    flag : {C.FLAG}")
