"""Nong san va ENSO (El Nino / La Nina) tu 1970 -> trang du lieu an PAGE (#gd-data).

Nguon:
  - Gia thang dai han: World Bank Pink Sheet (CMO Historical Data Monthly), tu 1970
  - Gia futures hien tai: Yahoo Finance (ZS=F, ZC=F, ZW=F, ZR=F CBOT; KC=F, SB=F ICE US)
  - ONI (Oceanic Nino Index): NOAA CPC
Phan tich:
  - Dot ENSO: ONI >= +0.5 (El Nino) hoac <= -0.5 (La Nina) it nhat 5 mua chong lan lien tiep
  - Bien dong gia 12 thang tinh tu thang bat dau dot, so voi trung binh moi giai doan
  - Tuong quan ONI trung binh 12 thang voi bien dong gia 12 thang (do tre 0, 3, 6 thang)
  - Bien dong gia sau cac su kien thoi tiet dac biet
"""
import io
import re
import math
import datetime
import requests
import wp

PAGE = 1526
UA = {"User-Agent": wp.UA}
Y0 = 1970
# key, ten, cot World Bank, he so doi don vi, don vi hien thi, ma futures, ten futures
# Doi USD/tan cua World Bank ve don vi niem yet cua san: 1 gia dau tuong, lua mi = 27,2155 kg;
# 1 gia ngo = 25,4012 kg; 1 cwt = 100 lb = 45,3592 kg
SP = [
    ("dau_tuong", "Đậu tương", ["Soybeans"], 2.72155, "US cent/giạ", "ZS=F", "CBOT đậu tương (ZS)", "US cent/giạ"),
    ("ngo", "Ngô", ["Maize"], 2.54012, "US cent/giạ", "ZC=F", "CBOT ngô (ZC)", "US cent/giạ"),
    ("lua_mi", "Lúa mì", ["Wheat, US SRW", "Wheat, US HRW"], 2.72155, "US cent/giạ", "ZW=F", "CBOT lúa mì SRW (ZW)", "US cent/giạ"),
    ("gao", "Gạo", ["Rice, Thai 5%"], 0.0453592, "USD/cwt", "ZR=F", "CBOT gạo thô (ZR)", "USD/cwt"),
    ("arabica", "Cà phê arabica", ["Coffee, Arabica"], 100 / 2.20462, "US cent/lb", "KC=F", "ICE US arabica (KC)", "US cent/lb"),
    ("robusta", "Cà phê robusta", ["Coffee, Robusta"], 1000.0, "USD/tấn", None, "ICE châu Âu robusta (RC)", "USD/tấn"),
    ("duong", "Đường", ["Sugar, world"], 100 / 2.20462, "US cent/lb", "SB=F", "ICE US đường số 11 (SB)", "US cent/lb"),
]
# su kien thoi tiet dac biet (thang bat dau, mo ta, mat hang chiu anh huong chinh)
SU_KIEN = [
    ("1975-07", "Sương giá lớn ở Brazil", ["arabica", "robusta"]),
    ("1983-07", "Hạn hán và nắng nóng ở Mỹ", ["ngo", "dau_tuong"]),
    ("1988-06", "Hạn hán ở Mỹ", ["ngo", "dau_tuong", "lua_mi"]),
    ("1993-07", "Lũ lụt Trung Tây nước Mỹ", ["ngo", "dau_tuong"]),
    ("1994-06", "Sương giá ở Brazil", ["arabica", "robusta"]),
    ("2010-08", "Hạn hán Nga, Nga cấm xuất khẩu lúa mì", ["lua_mi", "ngo"]),
    ("2012-07", "Hạn hán ở Mỹ", ["ngo", "dau_tuong"]),
    ("2021-07", "Sương giá ở Brazil", ["arabica", "robusta"]),
    ("2023-07", "Gió mùa yếu, Ấn Độ cấm xuất khẩu gạo trắng", ["gao", "duong"]),
    ("2024-04", "Hạn hán Tây Nguyên và Brazil", ["robusta", "arabica"]),
]


def _m(s):
    return int(s[:4]) * 12 + int(s[5:7]) - 1


def _s(n):
    return "%04d-%02d" % (n // 12, n % 12 + 1)


# ---------------- nguon ----------------
def wb_prices():
    import openpyxl
    page = requests.get("https://www.worldbank.org/en/research/commodity-markets", headers=UA, timeout=60).text
    links = re.findall(r'https?://[^"\']+CMO-Historical-Data-Monthly\.xlsx', page)
    if not links:
        raise RuntimeError("khong tim thay link Pink Sheet")
    b = requests.get(links[0], headers=UA, timeout=120).content
    ws = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True)["Monthly Prices"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(h).strip() if h else "" for h in rows[4]]
    out = {}
    for key, _, cols, k, *_ in SP:
        ser = {}
        for c in cols:
            j = hdr.index(c) if c in hdr else -1
            if j < 0:
                continue
            for r in rows[6:]:
                if not r[0] or not re.match(r"^\d{4}M\d{2}$", str(r[0])):
                    continue
                d = "%s-%s" % (r[0][:4], r[0][5:7])
                v = r[j]
                if isinstance(v, (int, float)) and d not in ser and int(d[:4]) >= Y0:
                    ser[d] = round(v * k, 2)
        if len(ser) < 500:
            raise RuntimeError("Pink Sheet thieu du lieu %s" % key)
        out[key] = ser
    return out


SEAS = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6, "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}


def oni():
    t = requests.get("https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt", headers=UA, timeout=60).text
    out = {}
    for ln in t.splitlines()[1:]:
        p = ln.split()
        if len(p) == 4 and p[0] in SEAS:
            # mua 3 thang gan voi thang giua: DJF -> thang 1
            out["%s-%02d" % (p[1], SEAS[p[0]])] = float(p[3])
    if len(out) < 800:
        raise RuntimeError("ONI qua it dong")
    return out


def futures():
    out = {}
    for key, _, _, _, _, sym, ten, dv in SP:
        if not sym:
            continue
        j = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/" + sym,
                         params={"range": "2y", "interval": "1d"}, headers=UA, timeout=60).json()
        res = j["chart"]["result"][0]
        ts, cl = res["timestamp"], res["indicators"]["quote"][0]["close"]
        pts = [(datetime.datetime.fromtimestamp(a, datetime.timezone.utc).date(), c) for a, c in zip(ts, cl) if c]
        last = pts[-1]

        def back(days):
            lim = last[0] - datetime.timedelta(days=days)
            c = [p for p in pts if p[0] <= lim]
            return c[-1][1] if c else None
        y0 = [p for p in pts if p[0].year < last[0].year]

        def pc(a):
            return round((last[1] / a - 1) * 100, 1) if a else None
        out[key] = {"ten": ten, "dv": dv, "ngay": last[0].isoformat(), "gia": round(last[1], 2),
                    "w1": pc(back(7)), "m1": pc(back(30)), "ytd": pc(y0[-1][1] if y0 else None), "y1": pc(back(365)),
                    "hd": res["meta"].get("shortName") or ""}
    return out


# ---------------- phan tich ----------------
def episodes(o):
    keys = sorted(o)
    eps, cur = [], None
    for d in keys:
        v = o[d]
        typ = "el" if v >= 0.5 else ("la" if v <= -0.5 else None)
        if cur and typ == cur["t"]:
            cur["end"] = d
            cur["peak"] = max(cur["peak"], abs(v))
            continue
        if cur:
            eps.append(cur)
        cur = {"t": typ, "start": d, "end": d, "peak": abs(v)} if typ else None
    if cur:
        eps.append(cur)
    res = []
    for e in eps:
        n = _m(e["end"]) - _m(e["start"]) + 1
        dang = e["end"] == keys[-1]
        # dot dang dien ra: hien ca khi chua du 5 mua (dang hinh thanh)
        if (n < 5 and not (dang and n >= 3)) or int(e["start"][:4]) < Y0 - 1:
            continue
        pk = e["peak"]
        e["muc"] = "rất mạnh" if pk >= 2 else ("mạnh" if pk >= 1.5 else ("vừa" if pk >= 1 else "yếu"))
        e["dang_dien_ra"] = dang
        e["hinh_thanh"] = dang and n < 5
        e["peak"] = round(pk, 2)
        res.append(e)
    return res


def chg(ser, a, b):
    if a in ser and b in ser and ser[a]:
        return (ser[b] / ser[a] - 1) * 100
    return None


def mean(x):
    x = [v for v in x if v is not None]
    return sum(x) / len(x) if x else None


def med(x):
    x = sorted(v for v in x if v is not None)
    if not x:
        return None
    n = len(x)
    return round(x[n // 2] if n % 2 else (x[n // 2 - 1] + x[n // 2]) / 2, 1)


def corr(a, b):
    p = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(p) < 30:
        return None
    mx, my = mean([x for x, _ in p]), mean([y for _, y in p])
    sx = math.sqrt(sum((x - mx) ** 2 for x, _ in p))
    sy = math.sqrt(sum((y - my) ** 2 for _, y in p))
    return round(sum((x - mx) * (y - my) for x, y in p) / (sx * sy), 2) if sx and sy else None


# khung thoi gian quanh thang bat dau dot ENSO: am = truoc (tu N thang truoc den thang bat dau), duong = sau
WIN = [("b12", -12), ("b6", -6), ("b3", -3), ("a3", 3), ("a6", 6), ("a12", 12)]


def wchg(s, d, n):
    if n < 0:
        return chg(s, _s(_m(d) + n), d)
    return chg(s, d, _s(_m(d) + n))


def r1(v):
    return round(v, 1) if v is not None else None


def analyse(px, o, eps):
    months = sorted(o)
    state = {}
    for e in eps:
        for n in range(_m(e["start"]), _m(e["end"]) + 1):
            state[_s(n)] = e["t"]
    res = {"tbw": {w: {} for w, _ in WIN}, "tq": {}, "dot": []}
    for key, *_ in SP:
        s = px[key]
        for w, wn in WIN:
            allc = [wchg(s, d, wn) for d in s]
            el = [wchg(s, e["start"], wn) for e in eps if e["t"] == "el"]
            la = [wchg(s, e["start"], wn) for e in eps if e["t"] == "la"]
            neu = [wchg(s, d, wn) for d in s if d not in state]
            up_el = [v for v in el if v is not None]
            up_la = [v for v in la if v is not None]
            res["tbw"][w][key] = {
                "el": r1(mean(el)), "la": r1(mean(la)), "neu": r1(mean(neu)), "all": r1(mean(allc)),
                "el_tv": med(up_el), "la_tv": med(up_la), "neu_tv": med(neu),
                "el_tang": round(100 * sum(1 for v in up_el if v > 0) / len(up_el)) if up_el else None,
                "la_tang": round(100 * sum(1 for v in up_la if v > 0) / len(up_la)) if up_la else None,
                "n_el": len(up_el), "n_la": len(up_la)}
        # tuong quan: ONI tb 12 thang vs bien dong gia 12 thang sau do tre L thang
        tq = {}
        for lag in (0, 3, 6):
            xa, yb = [], []
            for d in months:
                if int(d[:4]) < Y0:
                    continue
                m0 = _m(d)
                w = [o.get(_s(m0 - i)) for i in range(12)]
                if None in w:
                    continue
                xa.append(sum(w) / 12)
                yb.append(chg(s, _s(m0 - 12 + lag), _s(m0 + lag)))
            tq["l%d" % lag] = corr(xa, yb)
        res["tq"][key] = tq
    res["tb"] = res["tbw"]["a12"]
    for e in eps:
        row = {"t": e["t"], "start": e["start"], "end": e["end"], "peak": e["peak"], "muc": e["muc"],
               "dd": e["dang_dien_ra"], "ht": e["hinh_thanh"], "w": {w: {} for w, _ in WIN}}
        for w, wn in WIN:
            for key, *_ in SP:
                if wn < 0:
                    v = wchg(px[key], e["start"], wn)
                else:
                    end = _s(_m(e["start"]) + wn)
                    if e["dang_dien_ra"] and end not in px[key]:
                        # dot dang dien ra: tinh tu dau dot den thang co gia moi nhat
                        end = max(px[key])
                        row["den"] = end
                    v = chg(px[key], e["start"], end)
                row["w"][w][key] = r1(v)
        row["c"] = row["w"]["a12"]
        res["dot"].append(row)
    sk = []
    for d, mo_ta, ah in SU_KIEN:
        r = {"thang": d, "mo_ta": mo_ta, "ah": ah, "c3": {}, "c12": {}}
        for key, *_ in SP:
            a = chg(px[key], _s(_m(d) - 1), _s(_m(d) + 2))
            b = chg(px[key], _s(_m(d) - 1), _s(_m(d) + 11))
            r["c3"][key] = round(a, 1) if a is not None else None
            r["c12"][key] = round(b, 1) if b is not None else None
        sk.append(r)
    res["su_kien"] = sk
    return res


def build():
    px = wb_prices()
    o = oni()
    eps = episodes(o)
    an = analyse(px, o, eps)
    last = max(px["ngo"])
    m0 = _m("%d-01" % Y0)
    n = _m(last) - m0 + 1
    obj = {
        "asof": datetime.date.today().isoformat(),
        "y0": "%d-01" % Y0,
        "sp": [[k, t, dv] for k, t, _, _, dv, *_ in SP],
        "gia": {k: [px[k].get(_s(m0 + i)) for i in range(n)] for k, *_ in SP},
        "oni": [o.get(_s(m0 + i)) for i in range(_m(max(o)) - m0 + 1)],
        "oni_last": [max(o), o[max(o)]],
        "wb_last": last,
    }
    obj.update(an)
    notes = ["WB den %s" % last, "ONI %s=%s" % (max(o), o[max(o)]), "%d dot ENSO" % len(eps)]
    try:
        obj["fut"] = futures()
        notes.append("futures %s" % obj["fut"]["ngo"]["ngay"])
    except Exception as e:  # noqa
        notes.append("CANH BAO futures: %s" % e)
    return obj, notes


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    obj, notes = build()
    try:
        old = wp.load(PAGE)
        if "fut" not in obj and "fut" in old:
            obj["fut"] = old["fut"]
    except RuntimeError:
        pass
    wp.save(PAGE, obj)
    return "da ghi trang %d: %s" % (PAGE, "; ".join(notes))


if __name__ == "__main__":
    import json
    o, n = build()
    print(n, len(json.dumps(o, ensure_ascii=False, separators=(",", ":"))))
    for e in o["dot"][-8:]:
        print(e)
    print(json.dumps(o["tb"], ensure_ascii=False))
    print(json.dumps(o["tq"], ensure_ascii=False))
    print(json.dumps(o["fut"], ensure_ascii=False)[:800])
