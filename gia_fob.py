"""Gia FOB nong san theo cang xuat khau (USDA FAS, ban tin Grain/Oilseeds: World Markets and Trade, hang thang)
va cau truc gia ky han CBOT (contango/backwardation). Ban dau chi co che do do (thu) de xem bo cuc bang trong PDF.
"""
import io
import re
import requests
from pypdf import PdfReader
import wp

UA = {"User-Agent": wp.UA}
PDF = {
    "grain": "https://apps.fas.usda.gov/psdonline/circulars/grain.pdf",
    "oilseeds": "https://apps.fas.usda.gov/psdonline/circulars/oilseeds.pdf",
}
KHOA = re.compile(r"(F\.?O\.?B|Export Quotation|Export Price|Gulf|Paranagua|Rosario|Up River|Black Sea|Rouen)", re.I)


def trang_pdf(url):
    r = requests.get(url, headers=UA, timeout=120)
    r.raise_for_status()
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages]


def thu():
    out = []
    for k, u in PDF.items():
        ps = trang_pdf(u)
        out.append("== %s: %d trang" % (k, len(ps)))
        for i, t in enumerate(ps):
            if len(KHOA.findall(t)) >= 3:
                out.append("-- %s trang %d --\n%s" % (k, i + 1, t[:6000]))
    for s in ("ZCZ26.CBT", "ZSF27.CBT", "ZMZ26.CBT", "ZLZ26.CBT", "ZWZ26.CBT"):
        try:
            r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%s" % s,
                             params={"range": "5d", "interval": "1d"}, headers=UA, timeout=30)
            j = r.json()["chart"]["result"][0]["meta"]
            out.append("yahoo %s %s %s" % (s, r.status_code, j.get("regularMarketPrice")))
        except Exception as e:  # noqa: BLE001
            out.append("yahoo %s LOI %s" % (s, e))
    print("\n".join(out))
    return "da in %d muc" % len(out)
