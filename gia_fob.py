"""Gia FOB nong san theo cang xuat khau va cau truc gia ky han CBOT (contango/backwardation)
-> trang du lieu an "du-lieu-fob".

- FOB lua mi va ngo: ban tin "Grain: World Markets and Trade" cua USDA FAS (so lieu cua Hoi dong Ngu coc
  Quoc te IGC), hang thang. Ban tin hat co dau chi co bieu do (khong co so) nen chua co FOB dau tuong,
  kho dau, dau dau theo cang.
- FOB theo cang cho ca dau tuong, kho dau, dau dau va ngo, lua mi Nga/Ukraine: bang cong khai cua
  GrainsPrices.com (ban mien phi tre khoang 3 thang).
- Duong cong ky han: gia cuoi cua cac hop dong CBOT (Yahoo Finance) trong khoang 15 thang toi.
Che do thu() in noi dung cac trang co bang gia trong PDF de kiem tra bo cuc.
"""
import io
import html
import re
import datetime
import requests
from pypdf import PdfReader
import wp

SLUG = "du-lieu-fob"
UA = {"User-Agent": wp.UA}
PDF = {
    "grain": "https://apps.fas.usda.gov/psdonline/circulars/grain.pdf",
    "oilseeds": "https://apps.fas.usda.gov/psdonline/circulars/oilseeds.pdf",
}
KHOA = re.compile(r"(F\.?O\.?B|Export Quotation|Export Price|Gulf|Paranagua|Rosario|Up River|Black Sea|Rouen)", re.I)
THANG = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9,
         "oct": 10, "nov": 11, "dec": 12}
THANG_DAI = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6, "July": 7,
             "August": 8, "September": 9, "October": 10, "November": 11, "December": 12}

# San pham: (ma goc CBOT, cac thang giao hang, ten, don vi)
KY_HAN = {
    "ngo": ("ZC", "HKNUZ", "Ngô (CBOT)", "US cent/giạ"),
    "dau": ("ZS", "FHKNQUX", "Đậu tương (CBOT)", "US cent/giạ"),
    "kho": ("ZM", "FHKNQUVZ", "Khô đậu tương (CBOT)", "USD/tấn thiếu"),
    "dd": ("ZL", "FHKNQUVZ", "Dầu đậu tương (CBOT)", "US cent/pound"),
    "mi": ("ZW", "HKNUZ", "Lúa mì mềm đỏ vụ đông SRW (CBOT)", "US cent/giạ"),
    "mic": ("KE", "HKNUZ", "Lúa mì cứng đỏ vụ đông HRW (KC)", "US cent/giạ"),
}
MA_THANG = "FGHJKMNQUVXZ"

LUA_MI = [("Argentina", "Argentina"), ("Australia", "Úc"), ("Canada", "Canada"), ("EU", "EU"),
          ("Russia", "Nga"), ("United States", "Mỹ")]
NGO = [(r"Argentina, Up River", "Argentina (Up River)"), (r"Brazil, Paranagu\S*", "Brazil (Paranaguá)"),
       (r"Ukraine\*?", "Ukraine"), (r"U\.S\. 3YC, Gulf", "Mỹ (vùng Vịnh)")]

GP_URL = "https://grainsprices.com/markets/fob"
# (dau ten khu vuc tren trang, dau ten mat hang, ten hien thi)
GP = {
    "ngo": [("FOB US Gulf", "Corn", "Mỹ (vùng Vịnh)"), ("FOB Brazil", "Corn", "Brazil (Paranaguá)"),
            ("FOB Argentina", "Corn", "Argentina"), ("FOB Ukraine", "Corn", "Ukraine"),
            ("FOB Russia", "Corn", "Nga (Biển Đen)")],
    "dau": [("FOB Brazil", "Soybeans", "Brazil (Paranaguá)"), ("FOB US Gulf", "Soybeans", "Mỹ (vùng Vịnh)"),
            ("FOB Argentina", "Soybeans", "Argentina"), ("FOB Ukraine", "Soybeans", "Ukraine")],
    "kho": [("FOB Argentina", "Soybean Meal", "Argentina"), ("FOB Brazil", "Soybean Meal", "Brazil (Paranaguá)"),
            ("FOB US Gulf", "Soybean Meal", "Mỹ (vùng Vịnh)")],
    "dd": [("FOB Argentina", "Soybean Oil", "Argentina"), ("FOB Brazil", "Soybean Oil", "Brazil (Paranaguá)"),
           ("FOB Netherlands", "Soybean Oil", "Hà Lan (Rotterdam)")],
    "mi": [("FOB Russia", "Wheat 12.5%", "Nga (12,5% đạm)"), ("FOB France", "Wheat 12%", "EU (Pháp, 12% đạm)"),
           ("FOB US Gulf", "Wheat SRW", "Mỹ (SRW)"), ("FOB US Gulf", "Wheat HRW", "Mỹ (HRW 12%)"),
           ("FOB Ukraine", "Wheat 12.5%", "Ukraine (12,5% đạm)"), ("FOB Argentina", "Wheat 12.5%", "Argentina (12,5% đạm)"),
           ("FOB Australia", "Wheat Premium", "Úc (APW1)")],
}


def trang_pdf(url):
    r = requests.get(url, headers=UA, timeout=120)
    r.raise_for_status()
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages]


def so(t):
    t = t.replace("$", "").replace(",", "").strip()
    try:
        return float(t)
    except ValueError:
        return None


def ngay_bao_cao(text):
    m = re.search(r"Foreign Agricultural Service/USDA\s+\d+\s+(%s)\s+(\d{4})" % "|".join(THANG_DAI), text)
    return "%s-%02d" % (m.group(2), THANG_DAI[m.group(1)]) if m else None


def doc_lua_mi(ps):
    """Dong gia moi nhat: 'Argentina Australia Canada EU Russia United States' roi dong '$252 $315 ...'."""
    for t in ps:
        dong = [d.strip() for d in t.split("\n")]
        for i, d in enumerate(dong):
            if d.startswith("Argentina Australia Canada EU Russia United States") and i + 1 < len(dong):
                gia = re.findall(r"\$(\d[\d,]*)", dong[i + 1])
                if len(gia) == len(LUA_MI):
                    return ngay_bao_cao(t), [[vn, so(g)] for (_, vn), g in zip(LUA_MI, gia)]
    return None, []


def doc_ngo(ps):
    """Bang 'Export bids (fob, US$ per ton) 6-Oct-26 7-Sep-26 6-Oct-25' va cac dong theo nuoc."""
    for t in ps:
        m = re.search(r"Export bids \(fob, US\$ per ton\)\s+(\S+)\s+(\S+)\s+(\S+)", t)
        if not m:
            continue
        ngay = []
        for s in m.groups():
            d = re.match(r"(\d{1,2})-(\w{3})-(\d{2})", s)
            ngay.append("20%s-%02d-%02d" % (d.group(3), THANG[d.group(2).lower()], int(d.group(1))) if d else s)
        rows = []
        for pat, vn in NGO:
            r = re.search(r"^%s\s+(\S+)\s+(\S+)\s+(\S+)" % pat, t, re.M)
            if r:
                rows.append([vn] + [so(x) for x in r.groups()])
        return ngay, rows
    return [], []


def bo_the(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", s)).split())


def doc_gp():
    """Bang FOB cua GrainsPrices: moi khu vuc la mot <thead> (o dau la ten khu vuc) roi cac dong
    ten mat hang, gia USD/tan, thay doi, duong cong, ngay ('Jul, 28 2026')."""
    r = requests.get(GP_URL, headers=UA, timeout=60)
    r.raise_for_status()
    bang = {}
    for khoi in r.text.split("<thead>")[1:]:
        m = re.search(r"<th[^>]*>([^<]+)</th>", khoi)
        if not m:
            continue
        rows = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", khoi, re.S):
            td = [bo_the(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(td) < 5 or not so(td[1]):
                continue
            try:
                ngay = datetime.datetime.strptime(td[4], "%b, %d %Y").date().isoformat()
            except ValueError:
                ngay = None
            rows.append((td[0], so(td[1]), so(td[2]), ngay))
        bang[html.unescape(m.group(1)).strip()] = rows
    out = {}
    for k, ds in GP.items():
        rows = []
        for kv, sp, vn in ds:
            for ten_kv, rs in bang.items():
                if ten_kv.startswith(kv):
                    for t, g, c, d in rs:
                        if t.startswith(sp):
                            rows.append([vn, g, c, d])
                            break
                    break
        out[k] = rows
    return out


def hop_dong(goc, thang_giao, so_thang=15):
    """Cac hop dong tu thang sau toi khoang 15 thang toi (bo thang dang giao hang)."""
    t = datetime.date.today()
    out = []
    for k in range(1, so_thang + 1):
        y, m = t.year + (t.month - 1 + k) // 12, (t.month - 1 + k) % 12 + 1
        c = MA_THANG[m - 1]
        if c in thang_giao:
            out.append(("%s%s%02d.CBT" % (goc, c, y % 100), "%02d/%d" % (m, y)))
    return out


def gia_yahoo(sym):
    r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%s" % sym,
                     params={"range": "5d", "interval": "1d"}, headers=UA, timeout=30)
    if r.status_code != 200:
        return None
    res = (r.json().get("chart") or {}).get("result") or []
    return res[0]["meta"].get("regularMarketPrice") if res else None


def cau_truc(curve):
    """Contango neu hop dong ke tiep cao hon hop dong gan nhat, backwardation neu thap hon."""
    if len(curve) < 2:
        return None
    p0, p1 = curve[0][2], curve[1][2]
    xa = curve[-1]
    for c in curve:  # hop dong xa khoang 1 nam
        if c is not curve[0] and abs((int(c[1][3:]) - int(curve[0][1][3:])) * 12 + int(c[1][:2]) - int(curve[0][1][:2]) - 12) <= 1:
            xa = c
            break
    g = (p1 - p0) / p0 * 100
    loai = "contango" if g > 0.15 else ("backwardation" if g < -0.15 else "phẳng")
    return {"loai": loai, "gan": round(g, 2), "xa": round((xa[2] - p0) / p0 * 100, 2), "ky_xa": xa[1]}


def tim_trang(s):
    base = wp._cfg()[0] + "/index.php/wp-json/wp/v2/pages"
    r = s.get(base, params={"slug": SLUG, "context": "edit", "_fields": "id"}, timeout=60)
    r.raise_for_status()
    if not r.json():
        raise RuntimeError("Chua co trang du lieu %s" % SLUG)
    return r.json()[0]["id"]


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    pid = tim_trang(wp._sess())
    obj = wp.load(pid) or {}
    notes = []

    ps = trang_pdf(PDF["grain"])
    k_mi, mi = doc_lua_mi(ps)
    ngay_ngo, ngo = doc_ngo(ps)
    if mi:
        obj["mi"] = {"ky": k_mi, "gia": mi}
        ls = [x for x in obj.get("mi_ls", []) if x[0] != k_mi]
        ls.append([k_mi, mi])
        obj["mi_ls"] = sorted(ls)[-36:]
    else:
        notes.append("khong doc duoc FOB lua mi")
    if ngo:
        obj["ngo"] = {"ngay": ngay_ngo, "gia": ngo}
    else:
        notes.append("khong doc duoc FOB ngo")
    so_gp = 0
    try:
        gp = doc_gp()
        so_gp = sum(len(v) for v in gp.values())
        if so_gp:
            obj["gp"] = gp
        else:
            notes.append("khong doc duoc GrainsPrices")
    except Exception as e:  # noqa
        notes.append("GrainsPrices: %s" % e)

    kh = {}
    for k, (goc, tg, ten, dv) in KY_HAN.items():
        curve = []
        for sym, nhan in hop_dong(goc, tg):
            p = gia_yahoo(sym)
            if p:
                curve.append([sym.split(".")[0], nhan, p])
        if len(curve) >= 2:
            kh[k] = {"ten": ten, "dv": dv, "c": curve, "kq": cau_truc(curve)}
        else:
            notes.append("thieu gia ky han %s" % k)
    if len(kh) < 4:
        raise RuntimeError("Chi lay duoc duong cong ky han %d/6 san pham: %s" % (len(kh), "; ".join(notes)))
    obj["kh"] = kh
    obj["asof"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
    wp.save(pid, obj)
    tom = ", ".join("%s %s" % (k, v["kq"]["loai"]) for k, v in kh.items())
    return "FOB lua mi %s (%d nuoc), ngo %s (%d nuoc), GrainsPrices %d dong; ky han: %s%s" % (
        k_mi, len(mi), ngay_ngo[0] if ngay_ngo else "-", len(ngo), so_gp, tom,
        ("; " + "; ".join(notes)) if notes else "")


def thu():
    out = []
    for k, u in PDF.items():
        ps = trang_pdf(u)
        out.append("== %s: %d trang" % (k, len(ps)))
        for i, t in enumerate(ps):
            if len(KHOA.findall(t)) >= 3:
                out.append("-- %s trang %d --\n%s" % (k, i + 1, t[:6000]))
    print("\n".join(out))
    ps = trang_pdf(PDF["grain"])
    print("lua mi:", doc_lua_mi(ps))
    print("ngo:", doc_ngo(ps))
    for k, (goc, tg, ten, dv) in KY_HAN.items():
        print(k, hop_dong(goc, tg))
    return "da in %d muc" % len(out)
