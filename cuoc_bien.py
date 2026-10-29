"""Cuoc bien ngu coc hang tuan tu USDA Grain Transportation Report (GTR, ams.usda.gov) -> khoa "cuoc" cua trang 1791.

GTR ra thu Nam; Table 20 "Ocean freight rates for selected shipments" la cac hop dong thue tau thuc te (tuyen, ngay ky,
ky xep hang, USD/tan), kem binh quan thang vung Vinh My / PNW di Nhat Ban. Moi tuyen giu muc moi nhat (toi da 180 ngay),
trang 299 cong voi gia FOB hang ngay (khoa "cs" trang 1728) de ra gia ve hien tai.
thu(): in cac trang co bang cuoc bien, khong ghi.
"""
import io
import re
import datetime
import requests
from pypdf import PdfReader
import wp

PAGE = 1791
GTR = "https://www.ams.usda.gov/services/transportation-analysis/gtr"
UA = {"User-Agent": wp.UA}
GIU_NGAY = 180
# vung xuat trong GTR -> ten tren web (khop ten nguon FOB tren trang 299)
XUAT = {"U.S. Gulf": "Mỹ (vùng Vịnh)", "PNW": "Mỹ (PNW)", "Brazil": "Brazil", "River Plate": "Argentina",
        "Argentina": "Argentina", "Vancouver": "Canada", "Canada": "Canada", "Black Sea": "Biển Đen", "Russia": "Nga",
        "Ukraine": "Ukraine", "Australia": "Úc", "France": "Pháp", "U.S. East Coast": "Mỹ (bờ Đông)", "Great Lakes": "Mỹ (Ngũ Hồ)"}
NHAP = {"N. China": "Trung Quốc", "S. China": "Trung Quốc", "China": "Trung Quốc", "Japan": "Nhật Bản",
        "Vietnam": "Việt Nam", "Thailand": "Thái Lan", "Indonesia": "Indonesia", "Jordan": "Jordan", "France": "Pháp",
        "Korea": "Hàn Quốc", "S. Korea": "Hàn Quốc", "South Korea": "Hàn Quốc", "Taiwan": "Đài Loan", "Egypt": "Ai Cập",
        "Mexico": "Mexico", "Philippines": "Philippines", "Morocco": "Maroc", "Algeria": "Algeria", "Tunisia": "Tunisia",
        "Saudi Arabia": "Ả Rập Xê Út", "Bangladesh": "Bangladesh", "Spain": "Tây Ban Nha", "Italy": "Ý",
        "Colombia": "Colombia", "Peru": "Peru", "Malaysia": "Malaysia", "Pakistan": "Pakistan", "Iran": "Iran",
        "Turkey": "Thổ Nhĩ Kỳ", "Netherlands": "Hà Lan", "Israel": "Israel", "Yemen": "Yemen", "Sudan": "Sudan",
        "Ethiopia": "Ethiopia", "Kenya": "Kenya", "Nigeria": "Nigeria", "Guatemala": "Guatemala", "Venezuela": "Venezuela"}
DONG = re.compile(r"^(.+?)\s+(Heavy grain|Light grain|Grain|Wheat|Corn|Soybeans?|Sorghum|Bulk grain|Soybean meal)\s+"
                  r"([A-Z][a-z]{2,4}\.? \d{1,2}, \d{4})\s+(.+?\d{4})\s+([\d,]+)\s+([\d.]+)", re.I)
THANG = {m: i + 1 for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"))}


def moi_nhat():
    h = requests.get(GTR, headers=UA, timeout=60).text
    ds = re.findall(r'/sites/default/files/media/GTR(\d{2})(\d{2})(\d{4})\.pdf', h)
    if not ds:
        raise RuntimeError("Khong thay link GTR")
    m, d, y = max(ds, key=lambda x: (x[2], x[0], x[1]))
    url = "https://www.ams.usda.gov/sites/default/files/media/GTR%s%s%s.pdf" % (m, d, y)
    return "%s-%s-%s" % (y, m, d), PdfReader(io.BytesIO(requests.get(url, headers=UA, timeout=120).content))


def ngay(s):
    m = re.match(r"([A-Za-z]{3})[a-z]*\.? (\d{1,2}), (\d{4})", s)
    return "%s-%02d-%02d" % (m.group(3), THANG[m.group(1).lower()], int(m.group(2))) if m else None


def tach(vung):
    """'U.S. Gulf N. China' -> ('U.S. Gulf', 'N. China')."""
    for x in sorted(XUAT, key=len, reverse=True):
        if vung.startswith(x + " "):
            return x, vung[len(x) + 1:].strip()
    return None, vung


def doc(pdf):
    """[(xuat, nhap, loai, ngay ky, ky xep, tan, USD/tan)], {thang: (vinh, pnw)}"""
    t = ""
    for p in pdf.pages:
        s = p.extract_text() or ""
        if "Ocean freight rates for selected shipments" in s:
            t = s
            break
    if not t:
        raise RuntimeError("GTR khong co bang cuoc bien (Table 20)")
    rows, la = [], []
    for ln in t.splitlines():
        m = DONG.match(ln.strip())
        if not m:
            continue
        x, n = tach(m.group(1))
        if not x:
            la.append(m.group(1))
            continue
        rows.append((XUAT[x], NHAP.get(n, n), m.group(2), ngay(m.group(3)), m.group(4).strip(),
                     int(m.group(5).replace(",", "")), float(m.group(6))))
    nb = {}
    for m in re.finditer(r"([A-Z][a-z]+ \d{4})\s+\$([\d.]+)\s+\$([\d.]+)\s+\$([\d.]+)", t):
        nb[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return rows, nb, la


def run():
    so, pdf = moi_nhat()
    rows, nb, la = doc(pdf)
    if not rows:
        raise RuntimeError("Khong doc duoc dong cuoc nao trong GTR %s" % so)
    for r in rows:
        if not 5 <= r[6] <= 300:
            raise RuntimeError("Cuoc bat thuong: %s" % (r,))
    obj = wp.load(PAGE) or {}
    old = obj.get("cuoc") or {}
    tuyen = dict(old.get("tuyen") or {})
    han = (datetime.date.today() - datetime.timedelta(days=GIU_NGAY)).isoformat()
    for x, n, loai, nk, kx, tan, usd in rows:
        k = "%s|%s" % (x, n)
        cu = tuyen.get(k)
        if nk and (not cu or cu[1] <= nk):
            tuyen[k] = [usd, nk, kx, "GTR %s" % so]
    for th, (vinh, pnw) in nb.items():  # binh quan thang di Nhat Ban, chi dung khi khong co hop dong moi hon
        try:
            d = datetime.datetime.strptime(th, "%B %Y").date().replace(day=15).isoformat()
        except ValueError:
            continue
        for x, v in (("Mỹ (vùng Vịnh)", vinh), ("Mỹ (PNW)", pnw)):
            k = x + "|Nhật Bản"
            if not tuyen.get(k) or tuyen[k][1] < d:
                tuyen[k] = [v, d, "bình quân tháng %s" % d[5:7] + "/" + d[:4], "GTR %s" % so]
    tuyen = {k: v for k, v in tuyen.items() if v[1] >= han}
    cuoc = {"gtr": so, "tuyen": tuyen}
    if old == cuoc:
        return "Cuoc bien khong doi (GTR %s)" % so
    obj = wp.load(PAGE) or {}  # doc lai ngay truoc khi ghi
    obj["cuoc"] = cuoc
    wp.save(PAGE, obj)
    return "da ghi cuoc bien GTR %s: %d tuyen%s" % (so, len(tuyen), ("; bo qua vung xuat: " + ", ".join(la)) if la else "")


def thu():
    so, pdf = moi_nhat()
    rows, nb, la = doc(pdf)
    print("GTR", so)
    for r in rows:
        print(r)
    print("binh quan thang:", nb)
    print("vung xuat chua biet:", la)
    return "chay thu, khong ghi"
