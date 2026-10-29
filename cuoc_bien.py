"""Cuoc bien ngu coc hang tuan tu USDA Grain Transportation Report (GTR, ams.usda.gov).

thu(): tai GTR moi nhat, in cac trang co bang cuoc bien de viet bo doc.
"""
import io
import re
import requests
from pypdf import PdfReader
import wp

GTR = "https://www.ams.usda.gov/services/transportation-analysis/gtr"
UA = {"User-Agent": wp.UA}


def moi_nhat():
    h = requests.get(GTR, headers=UA, timeout=60).text
    ds = re.findall(r'/sites/default/files/media/GTR(\d{2})(\d{2})(\d{4})\.pdf', h)
    if not ds:
        raise RuntimeError("Khong thay link GTR")
    m, d, y = max(ds, key=lambda x: (x[2], x[0], x[1]))
    url = "https://www.ams.usda.gov/sites/default/files/media/GTR%s%s%s.pdf" % (m, d, y)
    return url, PdfReader(io.BytesIO(requests.get(url, headers=UA, timeout=120).content))


def thu():
    url, pdf = moi_nhat()
    print(url, len(pdf.pages), "trang")
    for i, p in enumerate(pdf.pages):
        t = p.extract_text() or ""
        if re.search(r"ocean|vessel|freight|Shanghai|China", t, re.I):
            print("==== trang", i + 1)
            print(t[:6000])
    return "chay thu, khong ghi"
