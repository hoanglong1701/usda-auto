"""Trang 111 (Vang bac vat chat): no cong (#gdd) va than hut ngan sach (#gdbd) theo IMF World Economic Outlook.

Lay tu API SDMX cua IMF (api.imf.org, khong bi chan voi may chu GitHub nhu DataMapper):
- GGXWDG_NGDP: no gop cua chinh phu, % GDP  -> var DATA trong #gdd
- NGDPD: GDP danh nghia, ty USD             -> var USD = no % GDP x GDP (nghin ty USD)
- GGXCNL_NGDP: can can ngan sach, % GDP     -> var D trong #gdbd
Chay hang ngay nua cuoi thang 4 va thang 10; khi IMF chua ra WEO moi thi so khong doi va job bo qua.
CHI sua trang 111, luu ban cu vao data/backup truoc khi ghi.
"""
import re
import csv
import io
import json
import requests
import wp

PAGE = 111
Y0 = 2001
KEYS = ["USA", "JPN", "DEU", "EURO", "GBR", "FRA", "ITA", "CAN", "CHN", "IND", "WEOWORLD"]
SDMX_CODE = {"WEOWORLD": "G001", "EURO": "G163"}
URL = "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.RES/WEO/+/%s.GGXWDG_NGDP+GGXCNL_NGDP+NGDPD.A"
# tu nam nay tro di bat buoc IMF phai co so; cac nam truoc thieu thi giu so cu tren web
NAM_BAT_BUOC = 2010


def lay_imf():
    """{chi tieu: {ma nuoc: {nam: gia tri}}}"""
    codes = [SDMX_CODE.get(c, c) for c in KEYS]
    r = requests.get(URL % "+".join(codes), timeout=120,
                     headers={"User-Agent": wp.UA, "Accept": "application/vnd.sdmx.data+csv;version=2.0.0"})
    r.raise_for_status()
    back = {v: k for k, v in SDMX_CODE.items()}
    out = {}
    for x in csv.DictReader(io.StringIO(r.text)):
        if not x.get("OBS_VALUE"):
            continue
        c = back.get(x["COUNTRY"], x["COUNTRY"])
        out.setdefault(x["INDICATOR"], {}).setdefault(c, {})[int(x["TIME_PERIOD"][:4])] = float(x["OBS_VALUE"])
    for k in ("GGXWDG_NGDP", "GGXCNL_NGDP", "NGDPD"):
        if k not in out:
            raise RuntimeError("API IMF thieu chi tieu %s" % k)
    return out


def so(v, nd):
    v = round(v, nd)
    return int(v) if v == int(v) else v


def chuoi(imf, cu, n, nd, lo, hi, ten):
    """Mang n nam tu Y0 cho tung nuoc; nam cu thieu so thi giu so tren web."""
    out = {}
    for k in KEYS:
        row = imf.get(k, {})
        arr = []
        for i in range(n):
            y = Y0 + i
            v = row.get(y)
            if v is None:
                old = (cu.get(k) or [None] * n)[i]
                if y >= NAM_BAT_BUOC:
                    raise RuntimeError("IMF thieu %s %s nam %d" % (ten, k, y))
                arr.append(old)
                continue
            if not lo <= v <= hi:
                raise RuntimeError("%s %s nam %d bat thuong: %s" % (ten, k, y, v))
            arr.append(so(v, nd))
        out[k] = arr
    return out


def doc_khoi(raw, moc, bien):
    """Tim 'var <bien>={...};' nam sau moc id (chi 1 lan trong khoi)."""
    i = raw.find(moc)
    if i < 0:
        raise RuntimeError("Trang 111 khong co %s" % moc)
    j = raw.find("<!-- /wp:html -->", i)
    m = list(re.finditer(r"var %s=(\{.*?\});" % bien, raw[i:j]))
    if len(m) != 1:
        raise RuntimeError("Khoi %s: tim thay %d lan 'var %s=' (can 1)" % (moc, len(m), bien))
    m = m[0]
    return i + m.start(1), i + m.end(1), json.loads(m.group(1))


def lech(moi, cu):
    """So o so lieu khac nhau va thay doi lon nhat."""
    dem, mx = 0, 0.0
    for k, arr in moi.items():
        for a, b in zip(arr, cu.get(k, [])):
            if a is not None and b is not None and a != b:
                dem += 1
                mx = max(mx, abs(a - b))
    return dem, mx


def tinh(raw):
    s1, e1, no_cu = doc_khoi(raw, 'id="gdd"', "DATA")
    s2, e2, usd_cu = doc_khoi(raw, 'id="gdd"', "USD")
    s3, e3, bd_cu = doc_khoi(raw, 'id="gdbd"', "D")
    n = len(no_cu["USA"])
    imf = lay_imf()
    no = chuoi(imf["GGXWDG_NGDP"], no_cu, n, 1, 0, 400, "no cong")
    bd = chuoi(imf["GGXCNL_NGDP"], bd_cu, n, 1, -40, 20, "can can ngan sach")
    gdp = imf["NGDPD"]
    usd = {}
    for k in KEYS:
        arr = []
        for i in range(n):
            g = gdp.get(k, {}).get(Y0 + i)
            arr.append(so(no[k][i] * g / 100 / 1000, 2) if (g is not None and no[k][i] is not None) else usd_cu[k][i])
        usd[k] = arr
    return [(s1, e1, no, no_cu), (s2, e2, usd, usd_cu), (s3, e3, bd, bd_cu)]


def js(d):
    return json.dumps(d, separators=(",", ":"), ensure_ascii=False)


def run():
    raw = wp.get_raw(PAGE)
    khoi = tinh(raw)
    tom = []
    for ten, (_, _, moi, cu) in zip(("no %GDP", "no USD", "ngan sach"), khoi):
        dem, mx = lech(moi, cu)
        tom.append("%s %d o doi (max %.1f)" % (ten, dem, mx))
    if all(js(m) == js(c) for _, _, m, c in khoi):
        return "IMF chua co so moi, trang 111 giu nguyen"
    dem, mx = lech(khoi[0][2], khoi[0][3])
    if mx > 40:
        raise RuntimeError("No cong thay doi bat thuong (toi %.1f diem %% GDP), khong ghi: %s" % (mx, "; ".join(tom)))
    new = raw
    for s, e, moi, _ in sorted(khoi, key=lambda x: -x[0]):
        new = new[:s] + js(moi) + new[e:]
    wp.backup_raw(PAGE, raw)
    back = wp.set_raw(PAGE, new)
    for _, _, moi, _ in khoi:
        if js(moi) not in back:
            raise RuntimeError("Doc lai trang 111 khong thay so moi")
    return "da cap nhat trang 111 theo WEO moi: " + "; ".join(tom)


def run_dry():
    raw = wp.get_raw(PAGE)
    khoi = tinh(raw)
    out = []
    for ten, (_, _, moi, cu) in zip(("no %GDP", "no USD", "ngan sach"), khoi):
        dem, mx = lech(moi, cu)
        out.append("%s %d o doi (max %.2f)" % (ten, dem, mx))
        for k in ("USA", "CHN", "WEOWORLD"):
            print(ten, k, "cu:", cu[k][-8:], "moi:", moi[k][-8:])
    return "chay thu, khong ghi: " + "; ".join(out)
