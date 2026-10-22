"""Kim loai cong nghiep + nguyen lieu cong nghiep -> trang du lieu an PAGE (#gd-data).

Khoa:
  lme  : gia cash + ton kho LME 6 kim loai (nguon westmetall, 2 nam, diem cuoi moi tuan + phien moi nhat)
  mcs  : top nuoc san xuat theo USGS Mineral Commodity Summaries (cap nhat khi co ban nam moi)
  psd  : can doi cung cau the gioi ca phe, duong cua USDA (PSD), 6 nien vu gan nhat
  bc   : tom tat bao cao cung cau (ICSG, ILZSG, INSG, IAI, ITA, ICO, ISO, CONAB, Cecafe, UNICA...)
         doc tu data/bao_cao.json trong repo (tac vu Claude dinh ky cap nhat file nay)
"""
import os
import io
import re
import json
import datetime
import requests
import wp
from names import vn

PAGE = 1519
UA = {"User-Agent": wp.UA}
METALS = [("cu", "Đồng", "Cu"), ("al", "Nhôm", "Al"), ("zn", "Kẽm", "Zn"),
          ("pb", "Chì", "Pb"), ("ni", "Niken", "Ni"), ("sn", "Thiếc", "Sn")]
MCS_FILE = {"cu": "copper", "al": "aluminum", "zn": "zinc", "pb": "lead", "ni": "nickel", "sn": "tin"}
# don vi goc USGS: nghin tan (cu, al, zn, pb), tan (ni, sn)
MCS_DIV = {"cu": 1, "al": 1, "zn": 1, "pb": 1, "ni": 1000, "sn": 1000}
NAMES = {"UNITED STATES": "Mỹ", "CONGO (KINSHASA)": "CHDC Congo", "KAZAKHSTAN": "Kazakhstan",
         "ZAMBIA": "Zambia", "BOLIVIA": "Bolivia", "ICELAND": "Iceland", "BAHRAIN": "Bahrain",
         "NEW CALEDONIA": "New Caledonia", "RWANDA": "Rwanda", "TAJIKISTAN": "Tajikistan",
         "LAOS": "Lào", "BURMA": "Myanmar", "OTHER COUNTRIES": "Các nước khác",
         "KOREA, REPUBLIC OF": "Hàn Quốc", "UNITED ARAB EMIRATES": "UAE"}
PSD = {"cf": "0711100", "su": "0612000"}
PSD_ATTR = {"sx": 28, "tt": 125, "xk": 88, "nk": 57, "tk": 176, "dk": 20}


def ten(s):
    k = s.strip().upper()
    return NAMES.get(k) or vn(s)


# ---------------- LME (westmetall) ----------------
def _wm_year(sym, year):
    r = requests.get("https://www.westmetall.com/en/markdaten.php",
                     params={"action": "table", "field": "LME_%s_cash" % sym, "year": year},
                     headers=UA, timeout=60)
    r.raise_for_status()
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S):
        c = [re.sub(r"<[^>]+>|&nbsp;", " ", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(c) < 4:
            continue
        try:
            d = datetime.datetime.strptime(c[0].replace(".", ""), "%d %B %Y").date()
            p = float(c[1].replace(",", ""))
            s = int(c[3].replace(",", "")) if c[3].replace(",", "").isdigit() else None
        except ValueError:
            continue
        out.append((d, p, s))
    return out


def lme():
    y = datetime.date.today().year
    res = {}
    for k, n, sym in METALS:
        rows = _wm_year(sym, y) + _wm_year(sym, y - 1)
        rows = sorted({r[0]: r for r in rows}.values())
        if len(rows) < 100:
            raise RuntimeError("westmetall %s chi co %d dong" % (sym, len(rows)))
        # diem cuoi moi tuan ISO
        wk = {}
        for r in rows:
            wk[r[0].isocalendar()[:2]] = r
        w = sorted(wk.values())
        last = rows[-1]
        if (datetime.date.today() - last[0]).days > 6:
            raise RuntimeError("westmetall %s du lieu cu (%s)" % (sym, last[0]))
        res[k] = {"n": n, "d": [r[0].isoformat() for r in w], "p": [r[1] for r in w], "s": [r[2] for r in w],
                  "last": [last[0].isoformat(), last[1], last[2]]}
    return res


# ---------------- USGS MCS ----------------
_NUM = re.compile(r"^(?:—|NA|W|XX|[<>]?\d[\d,]*(?:\.\d+)?)$")


def _num(t):
    t = t.lstrip("<>").replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def mcs_table(m, year):
    from pypdf import PdfReader
    r = requests.get("https://pubs.usgs.gov/periodicals/mcs%d/mcs%d-%s.pdf" % (year, year, MCS_FILE[m]), headers=UA, timeout=90)
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        return None
    t = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    i = -1
    for key in ("World Mine", "World Smelter", "World Refinery"):
        i = t.find(key)
        if i >= 0:
            break
    if i < 0:
        raise RuntimeError("MCS %s khong thay bang the gioi" % m)
    head, rows = None, []
    for ln in t[i:].split("\n")[1:]:
        ln = ln.strip()
        if head is None:
            if re.search(r"\b20\d\d\b.*\b20\d\de?\b", ln):
                head = [int(x[:4]) for x in re.findall(r"20\d\de?", ln)][:2]
            continue
        toks = [x[1:] if re.match(r"^e\d", x) else x for x in ln.split()]
        vals = []
        while toks and _NUM.match(toks[-1]):
            vals.insert(0, toks.pop())
        name = re.sub(r"\s+e$", "", re.sub(r"[\d,]+$", "", " ".join(toks))).strip()
        if not name or not vals:
            if rows:
                break
            continue
        rows.append((name, vals))
        if name.startswith("World total"):
            break
    if not head or not rows or not rows[-1][0].startswith("World total"):
        raise RuntimeError("MCS %s doc bang loi" % m)
    div = MCS_DIV[m]

    def grp(off):
        top, world = [], None
        for name, v in rows:
            a, b = _num(v[off]) if len(v) > off else None, _num(v[off + 1]) if len(v) > off + 1 else None
            a = a / div if a is not None else None
            b = b / div if b is not None else None
            if name.startswith("World total"):
                world = [a, b]
            elif name != "Other countries" and (a or b):
                top.append([ten(name), a, b])
        top.sort(key=lambda x: -(x[2] or x[1] or 0))
        return {"top": top[:10], "world": world}

    out = {"y": head, "chinh": grp(0)}
    if m == "cu":
        out["tinh_luyen"] = grp(2)
    return out


def mcs(old):
    y = datetime.date.today().year
    for year in (y, y - 1):
        if old and old.get("nam") == year:
            return old
        test = mcs_table("cu", year)
        if test is None:
            continue
        res = {"nam": year, "m": {"cu": test}}
        for k, _, _ in METALS[1:]:
            res["m"][k] = mcs_table(k, year)
        return res
    return old


# ---------------- USDA PSD ----------------
def _psd(path):
    r = requests.get("https://api.fas.usda.gov/api/psd" + path,
                     headers={"X-Api-Key": os.environ["FAS_API_KEY"].strip(), "User-Agent": wp.UA}, timeout=90)
    r.raise_for_status()
    return r.json()


def psd():
    y = datetime.date.today().year + 1
    res = {}
    for k, code in PSD.items():
        years, rows = [], []
        for my in range(y, y - 9, -1):
            try:
                d = _psd("/commodity/%s/world/year/%d" % (code, my))
            except requests.HTTPError:
                d = []
            if not d:
                continue
            v = {a: None for a in PSD_ATTR}
            for r in d:
                for a, aid in PSD_ATTR.items():
                    if r.get("attributeId") == aid:
                        v[a] = r.get("value")
            # duong khong co dong Domestic Consumption: tinh tu can doi
            if v["tt"] is None and None not in (v["dk"], v["sx"], v["nk"], v["xk"], v["tk"]):
                v["tt"] = v["dk"] + v["sx"] + v["nk"] - v["xk"] - v["tk"]
            if v["sx"]:
                years.insert(0, my)
                rows.insert(0, v)
            if len(years) == 6:
                break
        if len(years) < 3:
            raise RuntimeError("PSD %s qua it nien vu" % k)
        res[k] = {"y": years, **{a: [r[a] for r in rows] for a in PSD_ATTR}}
    return res


# ---------------- tong hop ----------------
def build(old):
    obj = dict(old or {})
    notes = []
    obj["lme"] = lme()
    notes.append("LME %s" % obj["lme"]["cu"]["last"][0])
    try:
        obj["mcs"] = mcs(obj.get("mcs"))
        notes.append("USGS %s" % (obj["mcs"] or {}).get("nam"))
    except Exception as e:  # noqa
        notes.append("CANH BAO USGS: %s" % e)
    if os.environ.get("FAS_API_KEY", "").strip():
        try:
            obj["psd"] = psd()
            notes.append("PSD ca phe %s" % obj["psd"]["cf"]["y"][-1])
        except Exception as e:  # noqa
            notes.append("CANH BAO PSD: %s" % e)
    try:
        obj["bc"] = json.load(open(os.path.join("data", "bao_cao.json"), encoding="utf-8"))
        notes.append("bao cao %d muc" % len(obj["bc"].get("ds", [])))
    except Exception as e:  # noqa
        notes.append("CANH BAO bao_cao.json: %s" % e)
    obj["asof"] = datetime.date.today().isoformat()
    return obj, notes


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    try:
        old = wp.load(PAGE)
    except RuntimeError:
        old = {}
    obj, notes = build(old)
    wp.save(PAGE, obj)
    return "da ghi trang %d: %s" % (PAGE, "; ".join(notes))


if __name__ == "__main__":
    o, n = build({})
    s = json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    print(n, len(s))
    print(json.dumps(o.get("mcs"), ensure_ascii=False)[:3000])
