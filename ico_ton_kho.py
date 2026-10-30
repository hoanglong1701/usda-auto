"""Ton kho chung nhan ca phe (arabica New York, robusta London) theo thang tu bao cao ICO Coffee Market Report,
Table 5 "Certified stocks on the New York and London futures markets", don vi trieu bao 60 kg.
Ghi khoa "thang" cua trang du lieu 1884 ({"ara": [["yyyy-mm", so]...], "rob": [...]}), giu nguyen cac khoa khac.

Moi nam ca phe (thang 10 den thang 9) doc bao cao moi nhat co bang. Bao cao ICO co luc dao nhan 2 dong (bao cao
2025/26 ghi "New York" cho so London): cac nam da xac nhan nam trong DAO_NHAN, nam moi kiem tra theo thang lien truoc.
"""
import io
import re
import time
import datetime
from statistics import median
import requests
from pypdf import PdfReader
import wp

UA = {"User-Agent": wp.UA}
PAGE = 1884
NAM_DAU = 2013
PHIEN = 3  # tang khi doi cach xu ly de doc lai toan bo lich su
# nam ca phe co bang ghi nhan nguoc: 2025/26 (loi van cung bao cao ghi 8/2026 London 0,83, My 0,24)
DAO_NHAN = {2025}
THANG = {m: i + 1 for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"))}


def url(thang, nam):
    """Bao cao thang 9/2026 -> cy2025-26/cmr-0926-e.pdf (nam ca phe tu thang 10)."""
    a = nam - 1 if thang <= 9 else nam
    return "https://www.ico.org/documents/cy%d-%02d/cmr-%02d%02d-e.pdf" % (a, (a + 1) % 100, thang, nam % 100)


def bang(t):
    """Chu 1 trang -> (['yyyy-mm'...], [dong New York], [dong London]) hoac None."""
    i = t.find("Table 5")
    if i >= 0:
        t = t[i:]
    h = re.search(r"((?:[A-Z][a-z]{2}-\d{2}\s+){6,})", t)
    ny = re.search(r"New York\s+((?:\d+\.\d+\s*){6,})", t)
    ld = re.search(r"London\s+((?:\d+\.\d+\s*){6,})", t)
    if not (h and ny and ld):
        return None
    th, a, b = [], [float(x) for x in ny.group(1).split()], [float(x) for x in ld.group(1).split()]
    for x in h.group(1).split():
        if x[:3] not in THANG:
            return None
        th.append("20%s-%02d" % (x[4:6], THANG[x[:3]]))
    if not len(th) == len(a) == len(b):
        return None
    return th, a, b


def doc(thang, nam):
    r = requests.get(url(thang, nam), headers=UA, timeout=90)
    time.sleep(1)
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        return None
    try:
        for p in PdfReader(io.BytesIO(r.content)).pages:
            t = p.extract_text() or ""
            if "ertified stocks on the New York" in t:
                x = bang(t)
                if x:
                    return x
    except Exception as e:  # noqa  mot file loi thi bo qua, thu bao cao thang truoc
        print("Loi doc", url(thang, nam), str(e)[:100])
    return None


def nam_ca_phe(a, hom_nay):
    """Bao cao moi nhat co bang cua nam ca phe a/a+1."""
    ds = [(m, a + 1) for m in range(9, 0, -1)] + [(m, a) for m in (12, 11, 10)]
    for th, n in ds:
        if (n, th) <= (hom_nay.year, hom_nay.month):
            x = doc(th, n)
            if x:
                print("Nam ca phe %d/%d: bao cao %02d/%d, %d thang" % (a, a + 1, th, n, len(x[0])))
                return x
    print("Nam ca phe %d/%d: khong doc duoc" % (a, a + 1))
    return None


def ghep(ara, rob, x, nam):
    """Them 1 bang vao chuoi; dao lai 2 dong khi bao cao ghi nhan nguoc. Tra ve True neu da dao."""
    th, a, b = x
    truoc = sorted(m for m in ara if m < th[0])[-3:]
    dao = nam in DAO_NHAN
    if truoc and nam > max(DAO_NHAN):
        # nam moi: chi dao khi chenh lech that ro; hai dong gan nhau thi tinh lien tuc khong noi len dieu gi
        pa, pr = median(ara[m] for m in truoc), median(rob[m] for m in truoc)
        d1 = abs(pa - a[0]) + abs(pr - b[0])
        d2 = abs(pa - b[0]) + abs(pr - a[0])
        dao = d2 < 0.6 * d1
    if dao:
        a, b = b, a
    for m, v1, v2 in zip(th, a, b):
        if not (0.01 <= v1 <= 8 and 0.01 <= v2 <= 8):
            raise RuntimeError("Ton kho ICO bat thuong %s: %s %s" % (m, v1, v2))
        ara[m], rob[m] = v1, v2
    return dao


def bo_gai(d):
    """Bo thang nhay > 40% so voi ca 2 thang ben canh trong khi 2 thang do gan nhau: gan nhu chac la loi go so."""
    ms = sorted(d)
    bo = []
    for i in range(1, len(ms) - 1):
        a, x, b = d[ms[i - 1]], d[ms[i]], d[ms[i + 1]]
        if abs(a - b) <= 0.2 * max(a, b) and abs(x - a) > 0.4 * a and abs(x - b) > 0.4 * b:
            bo.append(ms[i])
    for m in bo:
        del d[m]
    return bo


def run():
    hom_nay = datetime.date.today()
    obj = wp.load(PAGE) or {}
    cu = obj.get("thang") or {}
    if cu.get("phien") != PHIEN:  # doi cach xu ly thi doc lai tu dau
        cu = {}
    ara, rob = dict(cu.get("ara") or []), dict(cu.get("rob") or [])
    moi = hom_nay.year if hom_nay.month >= 10 else hom_nay.year - 1
    dau = moi - 1 if ara else NAM_DAU
    dao, thieu = [], []
    for a in range(dau, moi + 1):
        x = nam_ca_phe(a, hom_nay)
        if not x:
            thieu.append(a)
            continue
        if ghep(ara, rob, x, a):
            dao.append(a)
    if len(ara) < 24:
        raise RuntimeError("Chi doc duoc %d thang ton kho ICO" % len(ara))
    bo = bo_gai(ara) + bo_gai(rob)
    thang = {"phien": PHIEN, "nguon": "ICO Coffee Market Report", "ara": sorted(ara.items()), "rob": sorted(rob.items())}
    thang["ara"] = [list(x) for x in thang["ara"]]
    thang["rob"] = [list(x) for x in thang["rob"]]
    obj = wp.load(PAGE) or {}  # doc lai ngay truoc khi ghi, tac vu Claude cung ghi trang nay
    if obj.get("thang") == thang:
        return "Ton kho ICO khong doi (%d thang)" % len(ara)
    obj["thang"] = thang
    wp.save(PAGE, obj)
    return "Ton kho ICO: %d thang, %s den %s; dao nhan nam %s; thieu nam %s; bo diem %s" % (
        len(ara), min(ara), max(ara), dao or "-", thieu or "-", bo or "-")
