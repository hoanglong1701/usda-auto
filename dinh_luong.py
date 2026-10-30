"""Cap nhat trang du lieu an 478 (cong cu dinh luong Vang/Bac, widget #gdq tren trang 111).

Thay tac vu Claude "Cap nhat cong cu dinh luong Vang Bac (Thu 3 12h)" - giu DUNG quy tac cua tac vu do:
 - Moi dong tuan la ngay Thu Sau; gia tri = so lieu cua chinh ngay Thu Sau, chua co thi lay ngay gan nhat truoc do
   (ngay thuc te ghi vao last).
 - Yahoo (gia dong cua): GC=F -> G (1 so le), SI=F -> S (2), DX-Y.NYB -> DXI (2). Chi lay nen da chot phien.
 - FRED API: DGS10 -> Y10, DGS2 -> Y2, T10YIE -> BE, DTWEXBGS -> DXB (2), DFEDTARU -> FF (last.FT).
   Y10, Y2, BE lay cung mot ngay chung gan nhat; RY = Y10 - BE.
 - CFTC COT Disaggregated (file www.cftc.gov/dea/newcot/f_disagg.txt; API publicreporting chan 403): CG/CS = (Managed Money long - short) / OI x 100 (1 so le),
   bao cao Thu Ba cung tuan. last.CG/CS = [ngay bao cao, MM rong, OI].
 - CPI (FRED CPIAUCSL, % so cung ky): dong Thu Sau tu ngay 16 tro di dung thang lien truoc, truoc ngay 16 dung thang truoc nua.
 - C_DXY_Y10, C_G_RY, C_S_RY: tuong quan 60 phien cua % ngay (DXY, vang, bac) va thay doi diem co ban (Y10, RY).
 - ev (FOMC): them ky hop trong lich FOMC, dien cot con trong. nf (NFP): them ky moi tu ALFRED, dien cot con trong.
 - rx: dong moi cho bang phan ung CPI, PCE loi (10 nam), trang 111 ghep vao cac dong co san.
 - Them cac tuan con thieu + sua 3 tuan gan nhat neu nguon da hieu chinh.
Kiem tra truoc khi ghi (khong dat -> raise, KHONG ghi): cau truc, do dai mang, ngay cach nhau 7 ngay, khong null,
bien dong bat thuong (vang/bac > 8%/tuan, loi suat > 0,40 diem %/tuan, FF doi ma FRED khong co thay doi lai suat).
Bien moi truong DINH_LUONG_DRY=1: chi so sanh/in, khong ghi.
"""
import io
import os
import csv
import json
import datetime
import urllib.request

import requests

import wp

PAGE_ID = 478
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
UTC = datetime.timezone.utc
FRED_API = "https://api.stlouisfed.org/fred/series/observations"
CFTC_FILE = "https://www.cftc.gov/dea/newcot/f_disagg.txt"
COT_CODES = {"CG": "088691", "CS": "084691"}  # GOLD, SILVER - COMMODITY EXCHANGE INC.
FIX_WEEKS = 3
W_KEYS = ["dates", "G", "S", "RY", "Y10", "Y2", "FF", "DXB", "DXI", "BE", "CPI", "CG", "CS",
          "C_DXY_Y10", "C_G_RY", "C_S_RY"]
KEEP = ["CPI", "C_DXY_Y10", "C_G_RY", "C_S_RY"]
D = datetime.date.fromisoformat
FIX_KEEP = 6  # so tuan gan nhat tinh lai CPI va tuong quan
CUA_SO = 60  # phien cua tuong quan truot
FOMC = ["2026-10-28", "2026-12-09"]  # ngay cong bo; het lich thi msg nhac bo sung
RX_TU = {"cpi10": "2026-09-11", "pce10": "2026-08-26"}  # bang tren trang 111 da co den cac ngay nay
FRED_SERIES = "https://api.stlouisfed.org/fred/series"


def _now():
    return datetime.datetime.now(UTC)


# ---------------------------------------------------------------- nguon

def yahoo(symbol):
    """{date: close} chi gom nen da chot (nen ngay D chot sau 22:00 UTC ngay D)."""
    r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%s" % symbol,
                     params={"range": "1y", "interval": "1d"}, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    cutoff = (_now() - datetime.timedelta(hours=22)).date()
    out = {}
    for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
        d = datetime.datetime.fromtimestamp(t, UTC).date()
        if c is not None and d <= cutoff:
            out[d] = float(c)
    if not out:
        raise RuntimeError("Yahoo %s: khong co du lieu" % symbol)
    return out


def fred(series_id, key, start):
    url = (FRED_API + "?series_id=%s&api_key=%s&file_type=json&observation_start=%s"
           % (series_id, key, start.isoformat()))
    req = urllib.request.Request(url, headers={"User-Agent": "gdhh247-dinhluong/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        obs = json.loads(r.read().decode("utf-8")).get("observations", [])
    out = {D(o["date"]): float(o["value"]) for o in obs if o.get("value") not in (None, "", ".")}
    if not out:
        raise RuntimeError("FRED %s: khong co du lieu" % series_id)
    return out


def fred_json(path, key, **params):
    params.update(api_key=key, file_type="json")
    r = requests.get(FRED_SERIES + path, params=params, headers={"User-Agent": "gdhh247-dinhluong/1.0"}, timeout=30)
    r.raise_for_status()
    return r.json()


def ban_tin(sid, key, tu):
    """[(ngay cong bo, [gia tri theo thang tai ngay do])] cac lan cong bo them thang moi sau ngay tu (yyyy-mm-dd)."""
    out, cuoi = [], None
    for v in fred_json("/vintagedates", key, series_id=sid, realtime_start=tu)["vintage_dates"]:
        obs = fred_json("/observations", key, series_id=sid, realtime_start=v, realtime_end=v,
                        observation_start=(D(v) - datetime.timedelta(days=500)).isoformat())["observations"]
        obs = [o for o in obs if o["value"] != "."]
        if cuoi is not None and obs[-1]["date"] > cuoi:
            out.append((v, [(o["date"], float(o["value"])) for o in obs]))
        cuoi = obs[-1]["date"] if cuoi is None or obs[-1]["date"] > cuoi else cuoi
    return out


def cot_file():
    """Doc file COT Disaggregated tuan hien tai (www.cftc.gov/dea/newcot/f_disagg.txt).
    Tra ve {ma hop dong: {ngay bao cao: (MM rong, OI)}} gom tuan hien tai va tuan truoc
    (tuan truoc suy tu cot thay doi). Chi so cot 0-based: [2] ngay, [3] ma, [7] OI, [13] MM long,
    [14] MM short, [55] thay doi OI, [61] thay doi MM long, [62] thay doi MM short."""
    r = requests.get(CFTC_FILE, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    out = {}
    for row in csv.reader(io.StringIO(r.text)):
        if len(row) < 63:
            continue
        code = row[3].strip()
        if code not in COT_CODES.values():
            continue
        f = lambda i: float(row[i].strip())
        d = D(row[2].strip())
        oi, lo, sh = f(7), f(13), f(14)
        out[code] = {
            d: (lo - sh, oi),
            d - datetime.timedelta(days=7): ((lo - f(61)) - (sh - f(62)), oi - f(55)),
        }
    for k, code in COT_CODES.items():
        if code not in out:
            raise RuntimeError("CFTC: file %s khong co dong %s (ma %s)" % (CFTC_FILE, k, code))
    return out


def on_or_before(series, day):
    """(ngay, gia tri) cua diem gan nhat <= day, hoac None."""
    ks = [d for d in series if d <= day]
    return (max(ks), series[max(ks)]) if ks else None


# ---------------------------------------------------------------- tinh mot dong tuan

def week_row(fri, src, need_cot=True):
    """Tra ve (gia tri cac cot, ngay thuc te dung cho last).
    need_cot=False (khi sua tuan cu): file COT chi co 2 tuan gan nhat, tuan cu hon thi bo qua CG/CS."""
    v, used = {}, {}
    for k, sym, nd in (("G", "GC=F", 1), ("S", "SI=F", 2), ("DXI", "DX-Y.NYB", 2)):
        p = on_or_before(src[sym], fri)
        if not p:
            raise RuntimeError("Yahoo %s: khong co gia truoc %s" % (sym, fri))
        used[k], v[k] = p[0], round(p[1], nd)
    # Y10, Y2, BE cung ngay chung gan nhat
    common = set(d for d in src["DGS10"] if d <= fri) & set(src["DGS2"]) & set(src["T10YIE"])
    if not common:
        raise RuntimeError("FRED: khong co ngay chung DGS10/DGS2/T10YIE truoc %s" % fri)
    dc = max(common)
    v["Y10"], v["Y2"], v["BE"] = (round(src["DGS10"][dc], 2), round(src["DGS2"][dc], 2), round(src["T10YIE"][dc], 2))
    v["RY"] = round(v["Y10"] - v["BE"], 2)
    used["Y10"] = used["RY"] = dc
    p = on_or_before(src["DFEDTARU"], fri)
    used["FT"], v["FF"] = p[0], round(p[1], 2)
    p = on_or_before(src["DTWEXBGS"], fri)
    v["DXB"] = round(p[1], 2)
    for k in ("CG", "CS"):
        p = on_or_before(src[k], fri)
        if not p or (fri - p[0]).days > 6:
            if not need_cot:
                continue
            raise RuntimeError("CFTC %s: khong co bao cao cho tuan %s" % (k, fri))
        net, oi = p[1]
        v[k] = round(net / oi * 100, 1)
        used[k] = (p[0], net, oi)
    return v, used


# ---------------------------------------------------------------- cot tinh lai

def thang_lui(day, n):
    """Ngay 1 cua thang cach thang cua day n thang ve truoc."""
    k = day.year * 12 + day.month - 1 - n
    return datetime.date(k // 12, k % 12 + 1, 1)


def cpi_yoy(cpi, month):
    a, b = cpi.get(month), cpi.get(thang_lui(month, 12))
    return round((a / b - 1) * 100, 2) if a and b else None


def tuong_quan(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    c = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    return c / (va * vb) ** 0.5 if va and vb else None


def corr_ngay(gia, ls, fri):
    """Tuong quan CUA_SO phien den fri: % ngay cua gia va thay doi diem co ban cua ls."""
    ds = sorted(d for d in set(gia) & set(ls) if d <= fri)[-(CUA_SO + 1):]
    if len(ds) <= CUA_SO:
        return None
    r = tuong_quan([(gia[y] / gia[x] - 1) * 100 for x, y in zip(ds, ds[1:])],
                   [(ls[y] - ls[x]) * 100 for x, y in zip(ds, ds[1:])])
    return round(r, 2) if r is not None else None


def tinh_lai_tuan(w, src, changes):
    """Tinh lai CPI va 3 cot tuong quan cho FIX_KEEP tuan cuoi."""
    ry = {d: src["DGS10"][d] - src["T10YIE"][d] for d in set(src["DGS10"]) & set(src["T10YIE"])}
    n = len(w["dates"])
    for i in range(n - FIX_KEEP, n):
        fri = D(w["dates"][i])
        moi = {"CPI": cpi_yoy(src["CPIAUCSL"], thang_lui(fri, 1 if fri.day >= 16 else 2)),
               "C_DXY_Y10": corr_ngay(src["DX-Y.NYB"], src["DGS10"], fri),
               "C_G_RY": corr_ngay(src["GC=F"], ry, fri),
               "C_S_RY": corr_ngay(src["SI=F"], ry, fri)}
        for k, x in moi.items():
            if x is not None and abs(w[k][i] - x) > 1e-9:
                changes.append("%s %s: %s -> %s" % (w["dates"][i], k, w[k][i], x))
                w[k][i] = x


# ---------------------------------------------------------------- phan ung gia sau su kien

def phien(gia):
    ds = sorted(gia)
    return ds, {d: i for i, d in enumerate(ds)}


def doi(gia, ds, goc, k):
    """% thay doi tu phien thu goc den phien goc + k; chua du phien thi None."""
    return round((gia[ds[goc + k]] / gia[ds[goc]] - 1) * 100, 2) if goc + k < len(ds) else None


def phan_ung(src, day, moc, lech):
    """[vang..., bac...] theo cac moc phien, tinh tu phien day + lech."""
    out = []
    for sym in ("GC=F", "SI=F"):
        ds, vt = phien(src[sym])
        if day not in vt:
            return None
        out.append([doi(src[sym], ds, vt[day] + lech, k) for k in moc])
    return out[0] + out[1]


def cap_nhat_ev(data, src, changes, notes):
    ev = data["ev"]
    for r in ev[-3:]:
        x = phan_ung(src, D(r[0]), (1, 5, 20), 0)
        for j, v in enumerate(x or []):
            if r[3 + j] is None and v is not None:
                r[3 + j] = v
                changes.append("ev %s cot %d: %s" % (r[0], 3 + j, v))
    co = {r[0] for r in ev}
    for d in FOMC:
        if d in co or D(d) + datetime.timedelta(days=2) > max(src["DFEDTARU"]):
            continue
        truoc = on_or_before(src["DFEDTARU"], D(d))[1]
        sau = on_or_before(src["DFEDTARU"], D(d) + datetime.timedelta(days=2))[1]
        x = phan_ung(src, D(d), (1, 5, 20), 0)
        if x:
            bp = int(round((sau - truoc) * 100))
            ev.append([d, "hike" if bp > 0 else ("cut" if bp < 0 else "hold"), bp] + x)
            changes.append("ev them %s %+d" % (d, bp))
    if _now().date() > D(FOMC[-1]):
        notes.append("HET LICH FOMC trong dinh_luong.py - can bo sung")


def cap_nhat_nf(data, src, key, changes):
    nf = data["nf"]
    for r in nf[-3:]:
        x = phan_ung(src, D(r[0]), (1, 5, 20), -1)
        for j, v in enumerate(x or []):
            if r[5 + j] is None and v is not None:
                r[5 + j] = v
                changes.append("nf %s cot %d: %s" % (r[0], 5 + j, v))
    tn = fred("UNRATE", key, D(nf[-1][0]) - datetime.timedelta(days=120))
    for v, o in ban_tin("PAYEMS", key, nf[-1][0]):
        gt = [x[1] for x in o]
        moi = round(gt[-1] - gt[-2])
        tb = round((gt[-2] - gt[-5]) / 3)
        x = phan_ung(src, D(v), (1, 5, 20), -1)
        if x is None or D(o[-1][0]) not in tn:
            continue
        nf.append([v, "strong" if moi - tb > 50 else ("weak" if moi - tb < -50 else "inline"), moi, tb, tn[D(o[-1][0])]] + x)
        changes.append("nf them %s %+d" % (v, moi))


def cap_nhat_rx(data, src, key, changes):
    """Them dong bang phan ung khi da du 5 phien: [dd/mm/yyyy, ky nay, ky truoc, vang phien, vang 5p, bac phien, bac 5p]."""
    rx = data.setdefault("rx", {})
    for k, sid, nam in (("cpi10", "CPIAUCSL", False), ("pce10", "PCEPILFE", True)):
        hang = rx.setdefault(k, [])
        tu = max([RX_TU[k]] + ["%s-%s-%s" % (r[0][6:], r[0][3:5], r[0][:2]) for r in hang])
        chuoi = fred(sid, key, D(tu) - datetime.timedelta(days=500))
        for v, o in ban_tin(sid, key, tu):
            m = D(o[-1][0])
            if nam:
                a, b = cpi_yoy(chuoi, m), cpi_yoy(chuoi, thang_lui(m, 1))
            else:
                a = round((chuoi[m] / chuoi[thang_lui(m, 1)] - 1) * 100, 1) if m in chuoi else None
                b = round((chuoi[thang_lui(m, 1)] / chuoi[thang_lui(m, 2)] - 1) * 100, 1)
            x = phan_ung(src, D(v), (1, 6), -1)
            if a is None or b is None or x is None or None in x:
                continue
            hang.insert(0, [D(v).strftime("%d/%m/%Y"), round(a, 1), round(b, 1)] + x)
            changes.append("rx %s them %s" % (k, v))


# ---------------------------------------------------------------- kiem tra

def check(old, new):
    w = new["w"]
    if set(new) - {"rx"} != set(old) - {"rx"} or set(new["w"]) != set(old["w"]) or set(new["last"]) != set(old["last"]):
        raise RuntimeError("Cau truc khoa khac ban cu")
    n = len(w["dates"])
    for k in W_KEYS:
        if len(w[k]) != n:
            raise RuntimeError("Mang %s dai %d, dates dai %d" % (k, len(w[k]), n))
    for a, b in zip(w["dates"][-60:], w["dates"][-59:]):
        if (D(b) - D(a)).days != 7:
            raise RuntimeError("Ngay khong cach 7 ngay: %s -> %s" % (a, b))
    if D(w["dates"][-1]).weekday() != 4:
        raise RuntimeError("Dong cuoi khong phai Thu Sau: %s" % w["dates"][-1])
    start = max(0, len(old["w"]["dates"]) - FIX_WEEKS - 1)
    for i in range(start, n):
        for k in W_KEYS[1:]:
            x = w[k][i]
            if x is None or (isinstance(x, float) and x != x):
                raise RuntimeError("Gia tri rong %s tuan %s" % (k, w["dates"][i]))
        if i == 0:
            continue
        for k, lim in (("G", 0.08), ("S", 0.08)):
            if abs(w[k][i] / w[k][i - 1] - 1) > lim:
                raise RuntimeError("%s doi %.1f%% tuan %s - can kiem tra lai nguon"
                                   % (k, (w[k][i] / w[k][i - 1] - 1) * 100, w["dates"][i]))
        for k in ("Y10", "Y2", "RY"):
            if abs(w[k][i] - w[k][i - 1]) > 0.40:
                raise RuntimeError("%s doi %.2f diem %% tuan %s - can kiem tra lai nguon"
                                   % (k, w[k][i] - w[k][i - 1], w["dates"][i]))


# ---------------------------------------------------------------- chay

def run():
    old = wp.load(PAGE_ID)
    data = json.loads(json.dumps(old))
    w = data["w"]
    last_fri = D(w["dates"][-1])
    # Thu Sau gan nhat da chot phien (sau 22:00 UTC Thu Sau)
    cut = (_now() - datetime.timedelta(hours=22)).date()
    target = cut - datetime.timedelta(days=(cut.weekday() - 4) % 7)
    start = last_fri - datetime.timedelta(days=200)  # du cho cua so tuong quan

    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise RuntimeError("Thieu secret FRED_API_KEY")
    src = {s: yahoo(s) for s in ("GC=F", "SI=F", "DX-Y.NYB")}
    for s in ("DGS10", "DGS2", "T10YIE", "DTWEXBGS", "DFEDTARU"):
        src[s] = fred(s, key, start)
    src["CPIAUCSL"] = fred("CPIAUCSL", key, last_fri - datetime.timedelta(days=500))
    cf = cot_file()
    for k, code in COT_CODES.items():
        src[k] = cf[code]

    changes, added = [], []
    # 1) sua cac tuan gan nhat neu nguon da hieu chinh
    n = len(w["dates"])
    for i in range(max(0, n - FIX_WEEKS), n):
        fri = D(w["dates"][i])
        v, _ = week_row(fri, src, need_cot=False)
        for k, x in v.items():
            if abs(w[k][i] - x) > 1e-9:
                changes.append("%s %s: %s -> %s" % (w["dates"][i], k, w[k][i], x))
                w[k][i] = x
    # 2) them tuan con thieu
    fri = last_fri + datetime.timedelta(days=7)
    used = None
    while fri <= target:
        v, used = week_row(fri, src)
        w["dates"].append(fri.isoformat())
        for k in W_KEYS[1:]:
            w[k].append(v[k] if k in v else w[k][-1])
        added.append(fri.isoformat())
        fri += datetime.timedelta(days=7)
    if used is None:
        _, used = week_row(D(w["dates"][-1]), src, need_cot=False)
        for k in ("CG", "CS"):
            used.setdefault(k, (D(data["last"][k][0]), data["last"][k][1], data["last"][k][2]))

    notes = []
    tinh_lai_tuan(w, src, changes)
    cap_nhat_ev(data, src, changes, notes)
    cap_nhat_nf(data, src, key, changes)
    cap_nhat_rx(data, src, key, changes)

    data["asof"] = w["dates"][-1]
    L = data["last"]
    i = -1
    # dinh dang last giong ban cu: [ngay, gia tri]; CG/CS: [ngay bao cao, MM rong, OI]
    L["G"] = [used["G"].isoformat(), w["G"][i]]
    L["S"] = [used["S"].isoformat(), w["S"][i]]
    L["DXI"] = [used["DXI"].isoformat(), w["DXI"][i]]
    L["RY"] = [used["RY"].isoformat(), w["RY"][i]]
    L["Y10"] = [used["Y10"].isoformat(), w["Y10"][i]]
    L["FT"] = [used["FT"].isoformat(), w["FF"][i]]
    for k in ("CG", "CS"):
        d, net, oi = used[k]
        L[k] = [d.isoformat(), int(round(net)), int(round(oi))]

    check(old, data)

    # hop bat thuong chi bao, khong tu them
    last_ev = D(data["ev"][-1][0]) if data.get("ev") else None
    # FRED ghi muc lai suat moi tu ngay co hieu luc (1-2 ngay sau cuoc hop) nen bo qua 3 ngay sau su kien cuoi
    fed_moves = sorted(d for d in src["DFEDTARU"] if last_ev and d > last_ev + datetime.timedelta(days=3)
                       and on_or_before(src["DFEDTARU"], d - datetime.timedelta(days=1))
                       and src["DFEDTARU"][d] != on_or_before(src["DFEDTARU"], d - datetime.timedelta(days=1))[1])
    if fed_moves:
        notes.append("CO THAY DOI LAI SUAT FED MOI (%s) - chua them vao ev" % ", ".join(d.isoformat() for d in fed_moves))

    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", "dinh_luong.json"), "w", encoding="utf-8") as fh:
        json.dump({"asof": data["asof"], "added": added, "changes": changes, "last": data["last"], "notes": notes,
                   "tail": {k: w[k][-4:] for k in W_KEYS}}, fh, ensure_ascii=False, indent=1)

    msg = "them %s; sua %d diem; %s" % (",".join(added) or "khong tuan moi", len(changes), "; ".join(notes))
    if os.environ.get("DINH_LUONG_DRY") or not (added or changes):
        print(json.dumps({"added": added, "changes": changes, "last": data["last"], "rx": data.get("rx"),
                          "ev": data["ev"][-2:], "nf": data["nf"][-2:]}, ensure_ascii=False, indent=1))
        return ("chay thu (khong ghi): " if os.environ.get("DINH_LUONG_DRY") else "khong doi: ") + msg
    wp.save(PAGE_ID, data)
    return "da ghi trang %d den tuan %s: %s" % (PAGE_ID, data["asof"], msg)


def run_dry():
    """Chay thu tren GitHub: tinh va so sanh voi trang 478, KHONG ghi."""
    os.environ["DINH_LUONG_DRY"] = "1"
    return run()
