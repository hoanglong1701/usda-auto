"""Trang 847 (bao cao to chuc quoc te): so lieu IMF + chi so FAO tu dong, lich bao cao theo quy tac.

Cac muc con lai (World Bank GEP, OECD, WTO, loi binh chi tiet) van do tac vu Claude theo quy.
"""
import re
import datetime
import requests
import wp

PAGE = 847
UA = wp.UA
IMF_URL = "https://www.imf.org/external/datamapper/api/v1/%s"
FAO_PAGE = "https://www.fao.org/worldfoodsituation/foodpricesindex/en/"
IMF_KEYS = {"g": "WEOWORLD", "ae": "ADVEC", "us": "USA", "cn": "CHN", "ind": "IND",
            "vn": "VNM", "eu": "EURO", "jp": "JPN"}


def vn(x, nd=1):
    """So sang kieu Viet (dau phay)."""
    return ("%.*f" % (nd, x)).replace(".", ",")


def vdate(d):
    return d.strftime("%d/%m/%Y")


def _get(url, **kw):
    r = requests.get(url, headers={"User-Agent": UA, "Accept": "*/*"}, timeout=90, **kw)
    r.raise_for_status()
    return r


# ---------------------------------------------------------------- IMF
def imf_series(old):
    y0 = old["y0"]
    n = len(old["g"])
    years = [str(y0 + k) for k in range(n)]
    d = _get(IMF_URL % "NGDP_RPCH").json()["values"]["NGDP_RPCH"]
    inf = _get(IMF_URL % "PCPIPCH").json()["values"]["PCPIPCH"]["WEOWORLD"]
    out = {}
    for k, code in IMF_KEYS.items():
        row = d[code]
        arr = []
        for y in years:
            v = row.get(y)
            if v is None:
                raise RuntimeError("IMF thieu %s nam %s" % (code, y))
            arr.append(round(float(v), 1))
        out[k] = arr
    arr = []
    for y in years:
        v = inf.get(y)
        if v is None:
            raise RuntimeError("IMF thieu lam phat nam %s" % y)
        arr.append(round(float(v), 1))
    out["i"] = arr
    # kiem tra hop ly
    for v in out["g"]:
        if not -6 <= v <= 10:
            raise RuntimeError("Tang truong the gioi bat thuong: %s" % v)
    for v in out["i"]:
        if not -1 <= v <= 30:
            raise RuntimeError("Lam phat the gioi bat thuong: %s" % v)
    extra = max(int(y) for y in d["WEOWORLD"].keys())
    return out, extra


def chg_text(new, old):
    dlt = round(new - old, 1)
    if dlt > 0:
        return "tăng %s điểm so với kỳ trước" % vn(dlt)
    if dlt < 0:
        return "giảm %s điểm so với kỳ trước" % vn(-dlt)
    return "không đổi so với kỳ trước"


def update_imf(obj, today, notes):
    old = obj["imf"]
    new, last_year = imf_series(old)
    if all(old.get(k) == v for k, v in new.items()):
        return False
    m = today.month
    if m in (1, 7):
        label = "WEO Update tháng %d/%d" % (m, today.year)
    elif m in (4, 10):
        label = "WEO tháng %d/%d" % (m, today.year)
    else:
        label = "WEO (số liệu cập nhật tháng %d/%d)" % (m, today.year)
    Y = today.year
    idx = Y - old["y0"]
    g, i = new["g"], new["i"]
    s1 = ("%s: tăng trưởng toàn cầu %d ở mức %s%% (%s), năm %d là %s%%; lạm phát toàn cầu %s%% năm %d và %s%% năm %d."
          % (label, Y, vn(g[idx]), chg_text(g[idx], old["g"][idx]), Y + 1, vn(g[idx + 1]),
             vn(i[idx]), Y, vn(i[idx + 1]), Y + 1))
    s2 = ("Chi tiết kịch bản, rủi ro chính và số liệu từng nền kinh tế: xem báo cáo gốc trên imf.org. "
          "Bảng dữ liệu bên dưới lấy trực tiếp từ cơ sở dữ liệu của IMF.")
    old.update(new)
    old["upd"] = label
    hl = obj["rep"]["imf"]["hl"]
    hl[0] = s1
    if len(hl) > 1:
        hl[1] = s2
    else:
        hl.append(s2)
    # hang WEO trong bang rp
    nxt_m, nxt_y = (4, today.year) if m <= 3 else ((10, today.year) if m <= 9 else (4, today.year + 1))
    for row in obj["rep"]["imf"]["rp"]:
        if row[0].startswith("World Economic Outlook"):
            row[2] = "Tháng %d/%d" % (m, today.year)
            row[3] = "Tháng %d/%d (dự kiến)" % (nxt_m, nxt_y)
    notes.append("IMF: số liệu mới (%s)" % label)
    if last_year != old["y0"] + len(old["g"]) - 1:
        notes.append("IMF co du lieu den nam %d, trang chi giu den %d" % (last_year, old["y0"] + len(old["g"]) - 1))
    if Y != 2026:
        notes.append("NAM MOI: can chinh chi so KPI trong widget trang 106 (imf.g[8] la nam 2026)")
    return True


# ---------------------------------------------------------------- FAO
def first_friday(y, m):
    d = datetime.date(y, m, 1)
    d = d + datetime.timedelta(days=(4 - d.weekday()) % 7)
    if m == 1 and d.day <= 2:  # ngay le dau nam: FAO thuong cong bo tuan sau
        d += datetime.timedelta(days=7)
    return d


def fao_series(start="2019-01"):
    html = _get(FAO_PAGE).text
    mm = re.search(r'href="([^"]*food_price_indices_data[^"]*\.csv[^"]*)"', html)
    if not mm:
        raise RuntimeError("Khong thay link CSV cua FAO")
    u = mm.group(1).replace("&amp;", "&")
    if u.startswith("/"):
        u = "https://www.fao.org" + u
    text = _get(u).content.decode("utf-8-sig", errors="replace")
    rows = []
    for ln in text.splitlines():
        m = re.match(r"^\s*(\d{4})-(\d{2})\s*,(.*)$", ln)
        if not m:
            continue
        key = "%s-%s" % (m.group(1), m.group(2))
        if key < start:
            continue
        parts = [p.strip().strip('"') for p in m.group(3).split(",")]
        try:
            v = [round(float(p), 1) for p in parts[:6]]
        except ValueError:
            break  # thang chua day du
        if len(v) < 6:
            break
        rows.append((key, v))
    if not rows:
        raise RuntimeError("CSV FAO khong co dong du lieu")
    # lien tuc theo thang
    y, mth = int(start[:4]), int(start[5:])
    for key, _ in rows:
        if key != "%04d-%02d" % (y, mth):
            raise RuntimeError("Thang FAO khong lien tuc tai %s" % key)
        mth += 1
        if mth > 12:
            y, mth = y + 1, 1
    for key, v in rows:
        if not 60 <= v[0] <= 260:
            raise RuntimeError("FFPI bat thuong %s %s" % (key, v[0]))
    cols = {n: [r[1][k] for r in rows] for k, n in enumerate("fmdcos")}
    cols["months"] = [r[0] for r in rows]
    return cols


ORD = {2: "hai", 3: "ba", 4: "bốn", 5: "năm", 6: "sáu", 7: "bảy", 8: "tám", 9: "chín", 10: "mười"}


def pct(a, b):
    return (a / b - 1) * 100


def sgn(x, nd=1):
    return ("+" if x >= 0 else "−") + vn(abs(x), nd) + "%"


def fao_texts(c):
    f = c["f"]
    last = len(f) - 1
    ym = c["months"][last]
    y, m = int(ym[:4]), int(ym[5:])
    py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
    mom = pct(f[last], f[last - 1])
    yoy = pct(f[last], f[last - 12]) if last >= 12 else None
    s = "Chỉ số giá lương thực FAO (FFPI) tháng %d/%d: %s điểm, %s %s%% so với tháng %d" % (
        m, y, vn(f[last]), "tăng" if mom >= 0 else "giảm", vn(abs(mom)), pm)
    if yoy is not None:
        s += " và %s %s%% so với cùng kỳ" % ("cao hơn" if yoy >= 0 else "thấp hơn", vn(abs(yoy)))
    s += "."
    # chuoi tang/giam lien tiep
    n = 1
    up = f[last] >= f[last - 1]
    k = last
    while k > 0 and ((f[k] >= f[k - 1]) == up):
        n += 1
        k -= 1
    n -= 1
    if n >= 2:
        s += " Tháng %s thứ %s liên tiếp" % ("tăng" if up else "giảm", ORD.get(n, str(n)))
        # cao nhat/thap nhat ke tu
        j = None
        for t in range(last - 1, -1, -1):
            if (f[t] >= f[last]) if up else (f[t] <= f[last]):
                j = t
                break
        if j is not None and last - j > 3:
            jy, jm = int(c["months"][j][:4]), int(c["months"][j][5:])
            s += ", mức %s kể từ tháng %d/%d" % ("cao nhất" if up else "thấp nhất", jm, jy)
        s += "."
    ny, nm = (y, m + 2) if m + 2 <= 12 else (y + 1, m + 2 - 12)
    nxt = first_friday(ny, nm)
    parts = []
    for key, name in (("c", "Ngũ cốc"), ("o", "dầu thực vật"), ("s", "đường"), ("m", "thịt"), ("d", "sữa")):
        a = c[key]
        parts.append("%s %s (%s)" % (name, vn(a[last]), sgn(pct(a[last], a[last - 1]))))
    s2 = "%s so với tháng trước. Kỳ công bố tiếp theo (dự kiến): %s." % (", ".join(parts), vdate(nxt))
    rel_last = first_friday(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1)
    return s, s2, rel_last, nxt, (m, y)


def update_fao(obj, today, notes):
    fao = obj["fao"]
    c = fao_series(fao.get("y0", "2019-01"))
    same = all(fao.get(k) == c[k] for k in "fmdcos")
    if same:
        return False
    if len(c["f"]) < len(fao["f"]):
        raise RuntimeError("Chuoi FAO moi ngan hon chuoi cu")
    for k in "fmdcos":
        fao[k] = c[k]
    s1, s2, rel_last, nxt, (m, y) = fao_texts(c)
    hl = obj["rep"]["fao"]["hl"]
    hl[0] = s1
    if len(hl) > 1:
        hl[1] = s2
    else:
        hl.append(s2)
    for row in obj["rep"]["fao"]["rp"]:
        if row[0].startswith("Food Price Index"):
            row[2] = vdate(rel_last)
            row[3] = vdate(nxt) + " (dự kiến)"
    notes.append("FAO: FFPI tháng %d/%d = %s" % (m, y, vn(c["f"][-1])))
    return True


# ---------------------------------------------------------------- Lich
# (to chuc, khoa tim trong ten, ten hien thi, cac thang, ngay danh nghia)
RECUR = [
    ("IMF", "World Economic Outlook", "World Economic Outlook (tháng {m})", (4, 10), 15),
    ("IMF", "WEO Update", "WEO Update", (1, 7), 20),
    ("IMF", "Global Financial Stability", "Global Financial Stability Report", (4, 10), 15),
    ("IMF", "Fiscal Monitor", "Fiscal Monitor", (4, 10), 16),
    ("IMF", "COFER", "COFER (số liệu quý trước)", (3, 6, 9, 12), 30),
    ("World Bank", "Global Economic Prospects", "Global Economic Prospects", (1, 6), 10),
    ("World Bank", "Commodity Markets Outlook", "Commodity Markets Outlook", (4, 10), 25),
    ("World Bank", "International Debt Report", "International Debt Report", (12,), 10),
    ("OECD", "bản đầy đủ", "Economic Outlook (bản đầy đủ)", (6, 12), 3),
    ("OECD", "Interim", "Interim Economic Outlook", (3, 9), 17),
    ("WTO", "Global Trade Outlook", "Global Trade Outlook (cập nhật)", (4, 10), 20),
    ("FAO", "Food Outlook", "Food Outlook; Crop Prospects and Food Situation", (6, 11), 15),
]


def update_cal(obj, today, notes):
    cal = obj["cal"]
    before = [list(r) for r in cal]
    cutoff = (today - datetime.timedelta(days=14)).isoformat()
    cal[:] = [r for r in cal if r[0] >= cutoff]
    horizon = today + datetime.timedelta(days=200)

    def has(org, key, d, tol=25):
        for r in cal:
            if r[2] == org and key in r[3]:
                dd = datetime.date.fromisoformat(r[0])
                if abs((dd - d).days) <= tol:
                    return True
        return False

    def label(d, nominal=True):
        if d.year == today.year:
            return "Tháng %d" % d.month
        return "Tháng %d/%d" % (d.month, d.year)

    for org, key, name, months, day in RECUR:
        for yr in (today.year, today.year + 1):
            for mo in months:
                try:
                    d = datetime.date(yr, mo, day)
                except ValueError:
                    d = datetime.date(yr, mo, 28)
                if d < today or d > horizon:
                    continue
                if has(org, key, d):
                    continue
                cal.append([d.isoformat(), label(d), org, name.replace("{m}", str(mo)), "e"])
    # FFPI: thu Sau dau thang
    for k in range(0, 8):
        y = today.year + (today.month - 1 + k) // 12
        mo = (today.month - 1 + k) % 12 + 1
        d = first_friday(y, mo)
        if d < today or d > horizon:
            continue
        prev_m = mo - 1 if mo > 1 else 12
        if has("FAO", "Food Price Index", d, 10):
            continue
        cal.append([d.isoformat(), d.strftime("%d/%m"), "FAO",
                    "Food Price Index (tháng %d)" % prev_m, "e"])
    cal.sort(key=lambda r: (r[0], r[2], r[3]))
    changed = cal != before
    if changed:
        notes.append("Lịch: đã làm mới (%d dòng)" % len(cal))
    return changed


def run():
    today = datetime.date.today()
    if not wp.enabled():
        return "chua cau hinh WordPress"
    obj = wp.load(PAGE)
    notes, changed = [], False
    errs = []
    for fn in (update_imf, update_fao, update_cal):
        try:
            if fn(obj, today, notes):
                changed = True
        except Exception as e:  # moi nguon doc lap
            errs.append("%s: %s" % (fn.__name__, e))
    if changed:
        obj["asof"] = today.isoformat()
        wp.save(PAGE, obj)
    msg = "; ".join(notes) or "khong thay doi"
    if errs:
        raise RuntimeError(("%s | LOI: %s") % (msg, " | ".join(errs)) if changed else " | ".join(errs))
    return msg
