"""USDA WASDE (esmis .txt) -> trang 801, khoa wasde: so lieu My va the gioi cua ngo, dau tuong, lua mi.

Moi chi tieu co 2 gia tri: [thang truoc, thang nay] cua nien vu moi (cot cuoi cung cua bang).
"""
import re
import datetime
import requests
import wp

LIST_URL = "https://esmis.nal.usda.gov/publication/world-agricultural-supply-and-demand-estimates"
PAGE = 801
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def nums(s):
    s = re.sub(r"\b\d/", " ", s)          # bo chu thich 2/ 3/ ...
    return [float(x.replace(",", "")) for x in NUM.findall(s)]


def find(L, pat, start=0, end=None):
    end = len(L) if end is None else end
    for i in range(start, end):
        if re.search(pat, L[i]):
            return i
    return -1


def row(L, label, a, b, need=2):
    """Gia tri `need` cot cuoi cua dong dau tien co nhan `label` trong [a,b)."""
    i = find(L, r"^\s*" + label, a, b)
    if i < 0:
        raise RuntimeError("WASDE: khong thay dong '%s'" % label)
    v = nums(L[i][len(re.match(r"^\s*" + label, L[i]).group(0)):])
    if len(v) < need:
        raise RuntimeError("WASDE: dong '%s' thieu so: %s" % (label, L[i]))
    return v[-need:]


def months(L, a, b):
    """('Sep','Oct') tu dong tieu de cot."""
    for i in range(a, min(b, len(L))):
        m = re.search(r"\b(%s)\s+(%s)\s*$" % ("|".join(MON), "|".join(MON)), L[i])
        if m:
            return m.group(1), m.group(2)
    raise RuntimeError("WASDE: khong thay tieu de thang")


def us_block(L, title, sub=None):
    a = find(L, title)
    if a < 0:
        raise RuntimeError("WASDE: khong thay bang " + title)
    if sub:
        a = find(L, r"^\s*%s\s*$" % sub, a)
        if a < 0:
            raise RuntimeError("WASDE: khong thay muc " + sub)
    b = a + 45
    d = {
        "yield": row(L, r"Yield per Harvested Acre", a, b),
        "prod": row(L, r"Production", a, b),
        "end": row(L, r"Ending Stocks", a, b),
        "price": row(L, r"Avg\.\s*FarmPrice", a, b),
    }
    return d


def world_end(L, title):
    """Ton kho cuoi vu the gioi 2026/27: 2 dong Sep/Oct ngay sau dong 'World'."""
    a = find(L, title)
    if a < 0:
        raise RuntimeError("WASDE: khong thay bang " + title)
    y = find(L, r"\d{4}/\d{2}\s+Proj", a, a + 140)
    w = find(L, r"^\s*World", y, y + 3)
    if y < 0 or w < 0:
        raise RuntimeError("WASDE: khong thay dong World trong " + title)
    r1, r2 = L[w + 1], L[w + 2]
    if not (re.match(r"^\s*(%s)\b" % "|".join(MON), r1) and re.match(r"^\s*(%s)\b" % "|".join(MON), r2)):
        raise RuntimeError("WASDE: dong thang the gioi khong dung dinh dang: %s | %s" % (r1, r2))
    return [nums(r1[r1.index(r1.split()[0]) + 3:])[-1], nums(r2[r2.index(r2.split()[0]) + 3:])[-1]]


def parse(text):
    L = text.replace("\r", "").split("\n")
    m = re.search(r"WASDE - \d+ - \d+\s+([A-Z][a-z]+)\s+(\d{4})", text)
    if not m:
        raise RuntimeError("WASDE: khong thay thang/nam bao cao")
    mon = "%s-%02d" % (m.group(2), ["January", "February", "March", "April", "May", "June", "July", "August",
                                    "September", "October", "November", "December"].index(m.group(1)) + 1)
    a = find(L, r"U\.S\. Wheat Supply and Use")
    pm, cm = months(L, a, a + 12)
    my = re.search(r"(\d{4}/\d{2}) Proj", "\n".join(L[a:a + 12]))
    D = {
        "mon": mon, "pm": pm, "cm": cm, "my": my.group(1) if my else None,
        "ngo": us_block(L, r"U\.S\. Feed Grain and Corn Supply and Use", "CORN"),
        "dau_tuong": us_block(L, r"U\.S\. Soybeans and Products Supply and Use"),
        "lua_mi": us_block(L, r"U\.S\. Wheat Supply and Use"),
    }
    D["ngo"]["w_end"] = world_end(L, r"World Corn Supply and Use")
    D["dau_tuong"]["w_end"] = world_end(L, r"World Soybean Supply and Use")
    D["lua_mi"]["w_end"] = world_end(L, r"World Wheat Supply and Use")
    # kiem tra hop ly
    c = D["ngo"]
    if not (100 < c["yield"][1] < 300 and 5000 < c["prod"][1] < 30000 and 0 < c["price"][1] < 20):
        raise RuntimeError("WASDE: so ngo bat thuong %s" % c)
    s = D["dau_tuong"]
    if not (30 < s["yield"][1] < 80 and 2000 < s["prod"][1] < 8000 and 5 < s["price"][1] < 30):
        raise RuntimeError("WASDE: so dau tuong bat thuong %s" % s)
    w = D["lua_mi"]
    if not (20 < w["yield"][1] < 100 and 800 < w["prod"][1] < 3500 and 2 < w["price"][1] < 20):
        raise RuntimeError("WASDE: so lua mi bat thuong %s" % w)
    for k in ("ngo", "dau_tuong", "lua_mi"):
        if not (30 < D[k]["w_end"][1] < 600):
            raise RuntimeError("WASDE: ton kho the gioi bat thuong %s" % k)
    return D


def latest_url():
    r = requests.get(LIST_URL, timeout=60, headers={"User-Agent": wp.UA})
    r.raise_for_status()
    m = re.search(r'href="([^"]+wasde\d+\.txt)"', r.text)
    if not m:
        raise RuntimeError("Khong thay link WASDE .txt")
    u = m.group(1)
    if u.startswith("/"):
        u = "https://esmis.nal.usda.gov" + u
    return u


def run():
    t = requests.get(latest_url(), timeout=90, headers={"User-Agent": wp.UA}).text
    D = parse(t)
    if not wp.enabled():
        return "chua cau hinh WordPress; da parse %s" % D["mon"]
    old = wp.load(PAGE).get("wasde", {})
    if old == {**old, **D} and old:
        return "khong co bao cao moi (%s)" % D["mon"]
    D["at"] = datetime.date.today().isoformat()
    wp.update_key(PAGE, "wasde", D)
    return "da cap nhat WASDE %s" % D["mon"]
