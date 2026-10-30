"""Gia vang, bac tung ngay tu 1968 (CSV cua GoldPrice.com, CC BY 4.0, phai ghi nguon) cho trang du lieu 478.

Ghi 2 khoa, widget tren trang 111 doc:
  hw {"g": [...], "s": [...]} gia dong cua gan nhat cua moi Thu Sau tu 1970-01-02 den truoc ngay dau cua w.dates
     (thay chuoi noi suy tu binh quan thang o che do "Tu 1970").
  dd {"asof": ngay, "g": [dot...], "s": [dot...]} moi dot [ten, ngay dinh, gia dinh, ngay day, gia day, %] la muc giam
     lon nhat tu dinh den day trong cua so cua dot; dot cuoi tinh den ngay moi nhat.
Truoc 2015 la gia fix LBMA, sau do la gia dong cua cua Metals.dev; dong Thu Bay, Chu Nhat la gia chep lai nen bo.
"""
import datetime
import requests
import wp

PAGE = 478
URL = "https://goldprice.com/%s-price-history.csv"
D = datetime.date.fromisoformat
DOT = [("1974-1976", "1974-01-01", "1976-12-31"), ("1980-1999", "1980-01-01", "2001-12-31"),
       ("2008", "2008-01-01", "2008-12-31"), ("2011-2015", "2011-01-01", "2016-01-31"),
       ("2020-2022", "2020-06-01", "2022-12-31"), ("2026", "2026-01-01", "2099-12-31")]


def doc(ten):
    """[(ngay, gia)] theo thu tu thoi gian, chi ngay thuong."""
    r = requests.get(URL % ten, headers={"User-Agent": wp.UA}, timeout=60)
    r.raise_for_status()
    out = {}
    for l in r.text.splitlines():
        p = l.strip().split(",")
        if len(p) != 2 or l.startswith(("#", "date")):
            continue
        d, v = D(p[0]), float(p[1])
        if v > 0 and d.weekday() <= 4:
            out[d] = v
    if len(out) < 14000:
        raise RuntimeError("CSV %s chi co %d dong" % (ten, len(out)))
    if (datetime.date.today() - max(out)).days > 10:
        raise RuntimeError("CSV %s cu, dong cuoi %s" % (ten, max(out)))
    return sorted(out.items())


def thu_sau(ds, dau, cuoi):
    """Gia dong cua gan nhat cua moi Thu Sau tu dau den truoc cuoi."""
    out, i, f = [], 0, dau
    while f < cuoi:
        while i + 1 < len(ds) and ds[i + 1][0] <= f:
            i += 1
        out.append(ds[i][1])
        f += datetime.timedelta(days=7)
    return out


def giam_sau(ds, a, b, nd):
    """Muc giam lon nhat tu dinh den day trong cua so [a, b]."""
    dinh, tot = None, None
    for d, v in ds:
        if not D(a) <= d <= D(b):
            continue
        if dinh is None or v > dinh[1]:
            dinh = (d, v)
        if tot is None or v / dinh[1] < tot[3] / tot[1]:
            tot = (dinh[0], dinh[1], d, v)
    return [tot[0].isoformat(), round(tot[1], nd), tot[2].isoformat(), round(tot[3], nd), round((tot[3] / tot[1] - 1) * 100, 1)]


def tinh(obj):
    g, s = doc("gold"), doc("silver")
    dau, cuoi = datetime.date(1970, 1, 2), D(obj["w"]["dates"][0])
    hw = {"g": [round(x, 1) for x in thu_sau(g, dau, cuoi)], "s": [round(x, 2) for x in thu_sau(s, dau, cuoi)]}
    dd = {"asof": min(g[-1][0], s[-1][0]).isoformat(),
          "g": [[t] + giam_sau(g, a, b, 1) for t, a, b in DOT],
          "s": [[t] + giam_sau(s, a, b, 2) for t, a, b in DOT]}
    return hw, dd


def run(dry=False):
    obj = wp.load(PAGE)
    hw, dd = tinh(obj)
    moc = dict(zip(("74", "80"), (dd["g"][0][4], dd["g"][1][4])))
    if moc["74"] != 103.5 or moc["80"] != 252.8:
        raise RuntimeError("Moc lich su khac thuong: %s" % moc)
    msg = "%d tuan; den %s; vang 2026 %s%%, bac 2026 %s%%" % (len(hw["g"]), dd["asof"], dd["g"][-1][5], dd["s"][-1][5])
    if dry:
        print(dd)
        return "(thu) " + msg
    obj = wp.load(PAGE)  # doc lai ngay truoc khi ghi
    obj["hw"], obj["dd"] = hw, dd
    wp.save(PAGE, obj)
    return msg


def thu():
    return run(dry=True)
