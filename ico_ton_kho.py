"""Ton kho chung nhan ca phe (arabica New York, robusta London) theo thang tu bao cao ICO Coffee Market Report.

thu(): tai vai bao cao mau, in cac dong co "certified" de viet bo doc.
"""
import io
import re
import requests
from pypdf import PdfReader
import wp

UA = {"User-Agent": wp.UA}


def url(thang, nam):
    """Bao cao thang 9/2026 -> cy2025-26/cmr-0926-e.pdf (nam ca phe tu thang 10)."""
    a = nam - 1 if thang <= 9 else nam
    return "https://www.ico.org/documents/cy%d-%02d/cmr-%02d%02d-e.pdf" % (a, (a + 1) % 100, thang, nam % 100)


def thu():
    for th, n in ((9, 2026), (9, 2025), (9, 2024), (9, 2023), (9, 2022), (9, 2021), (9, 2018), (9, 2016)):
        u = url(th, n)
        r = requests.get(u, headers=UA, timeout=90)
        print("====", u, r.status_code, r.headers.get("Content-Type"), len(r.content))
        if r.status_code != 200 or not r.content.startswith(b"%PDF"):
            continue
        pdf = PdfReader(io.BytesIO(r.content))
        for i, p in enumerate(pdf.pages):
            t = p.extract_text() or ""
            if re.search(r"[Cc]ertified", t):
                print("-- trang", i + 1)
                ls = t.splitlines()
                for j, ln in enumerate(ls):
                    if re.search(r"[Cc]ertified", ln):
                        print("\n".join(ls[max(0, j - 1):j + 16])[:1100])
                        break
    return "chay thu, khong ghi"
