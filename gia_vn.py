"""Gia vang bac trong nuoc so voi quoc te -> trang du lieu an 178 (du-lieu-gia-vang-bac).

Chuyen tu pipeline tren may anh Long (Pipeline gia kim loai quy, pipeline_daily.bat), giu nguyen
cau truc #gd-data cua trang 178 va cong thuc quy doi. Ban tren may van chay lam du phong
(push_wp.py bo qua neu trang 178 da duoc cap nhat trong 6 gio).

Nguon:
  - Gia quoc te USD/oz: api.gold-api.com (XAU, XAG)
  - Ty gia USD/VND: feed XML Vietcombank (gioi han 1 request / 5 phut)
  - Bac: Phu Quy (gia luong + gia kg niem yet san), lich su 1 nam qua API statistics-price
  - Vang: SJC chinh chu (vang mieng 1L/10L/1KG, chi nhanh Ho Chi Minh); du phong: SJC theo Phu Quy
Lich su luu trong data/gia_vn/*.csv cua repo. Moi lan chay chi GHEP them du lieu moi
(SJC: 85 ngay gan nhat, Phu Quy: 1 nam), khong bao gio thay ca file bang ban ngan hon.
"""
import os
import re
import csv
import json
import datetime
import xml.etree.ElementTree as ET
import requests
import wp

PAGE = 178
DIR = os.path.join("data", "gia_vn")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
     "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"}
T = 30
VN = datetime.timezone(datetime.timedelta(hours=7))
G_OZ = 31.1034768
KG_LUONG = 37.5 / 1000
SJC_URL = "https://sjc.com.vn/GoldPrice/Services/PriceService.ashx"
PQ = "https://be.phuquy.com.vn/jewelry/product-payment-service/api"
VCB_URL = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx"
F_SJC = os.path.join(DIR, "sjc.csv")          # ngay,buy,sell (VND/luong)
F_SJC_PQ = os.path.join(DIR, "sjc_pq.csv")    # SJC theo Phu Quy, du phong
F_PQ_BAC = os.path.join(DIR, "pq_bac.csv")
F_QT_VANG = os.path.join(DIR, "qt_vang.csv")  # ngay,usd
F_QT_BAC = os.path.join(DIR, "qt_bac.csv")


# ---------------- luu tru ----------------
def rd(path):
    out = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for r in csv.reader(f):
                if r and re.match(r"^\d{4}-\d{2}-\d{2}$", r[0]):
                    out[r[0]] = [float(x) for x in r[1:]]
    return out


def wr(path, d):
    os.makedirs(DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        for k in sorted(d):
            w.writerow([k] + [round(x, 4) for x in d[k]])


def merge(path, new):
    """Ghep: giu toan bo ngay cu, ngay trung thi lay so moi. Tra (so dong cu, so dong moi)."""
    old = rd(path)
    n0 = len(old)
    old.update(new)
    wr(path, old)
    return n0, len(old)


# ---------------- nguon ----------------
def intl(sym):
    j = requests.get("https://api.gold-api.com/price/" + sym, headers=H, timeout=T).json()
    return float(j["price"])


def vcb():
    r = requests.get(VCB_URL, headers=H, timeout=T)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    for n in root.findall("Exrate"):
        if n.get("CurrencyCode") == "USD":
            f = lambda v: float(v.replace(",", ""))  # noqa: E731
            return {"buy": f(n.get("Buy")), "sell": f(n.get("Sell"))}
    raise RuntimeError("VCB khong co dong USD")


def phuquy():
    hd = dict(H, Referer="https://phuquy.com.vn/")
    j = requests.get(PQ + "/products/get-price", headers=hd, timeout=T).json()
    out = {}
    for it in j.get("data", []):
        out[it.get("id")] = (it.get("priceBuyTael"), it.get("priceSellTael"))
    kg = None
    try:
        k = requests.get(PQ + "/sync-price-history/get-sync-table-history", params={"productType": "BAC"}, headers=hd, timeout=T).json()
        for it in k.get("data", []):
            if (it.get("unitOfMeasure") or "").strip() == "Vnđ/kg":
                kg = (it.get("priceIn"), it.get("priceOut"))
                break
    except Exception:  # noqa: BLE001 - nguon phu
        pass
    if "B" not in out:
        raise RuntimeError("Phu Quy thieu bac")
    return out, kg


def pq_history(pid, key):
    today = datetime.datetime.now(VN)
    p = {"type": 1, "duration": "1Y", "fromDate": (today - datetime.timedelta(days=365)).strftime("%d/%m/%Y"), "toDate": today.strftime("%d/%m/%Y")}
    j = requests.get("%s/products/statistics-price/%d" % (PQ, pid), params=p, headers=dict(H, Referer="https://phuquy.com.vn/bang-gia/bac"), timeout=60).json()
    pts = ((j.get("data") or {}).get(key) or {}).get("pricePointInfoList") or []
    out = {}
    for x in pts:
        d = (x.get("lastUpdate") or "")[:10]
        if d and x.get("priceIn") and x.get("priceOut"):
            out[d] = [float(x["priceIn"]), float(x["priceOut"])]
    return out


def sjc_now():
    j = requests.post(SJC_URL, headers=dict(H, Referer="https://sjc.com.vn/gia-vang-online"), timeout=T).json()
    rows = [r for r in j.get("data", []) if r.get("TypeName") == "Vàng SJC 1L, 10L, 1KG"]
    if not rows:
        raise RuntimeError("SJC khong co dong vang mieng")
    r = next((x for x in rows if x.get("BranchName") == "Hồ Chí Minh"), rows[0])
    return float(r["BuyValue"]), float(r["SellValue"])


def sjc_history(days=30, chunk=10):
    """API lich su SJC chi tra mot so dong gioi han tinh tu DAU khoang (hoi 85 ngay chi nhan ~46 ngay dau),
    nen pipeline cu hut dan du lieu. O day chia doan ngan `chunk` ngay de lay du."""
    to = datetime.datetime.now(VN)
    out = {}
    cur = to - datetime.timedelta(days=days)
    while cur < to:
        end = min(cur + datetime.timedelta(days=chunk), to)
        j = requests.post(SJC_URL, headers=dict(H, Referer="https://sjc.com.vn/gia-vang-online"), timeout=60,
                          data={"method": "GetGoldPriceHistory", "goldPriceId": 1,
                                "fromDate": cur.strftime("%d/%m/%Y"), "toDate": end.strftime("%d/%m/%Y")}).json()
        for r in j.get("data", []):
            m = re.match(r"/Date\((\d+)\)/", r.get("GroupDate") or "")
            if m and r.get("BuyValue") and r.get("SellValue"):
                d = datetime.datetime.fromtimestamp(int(m.group(1)) / 1000, VN).strftime("%Y-%m-%d")
                out[d] = [float(r["BuyValue"]), float(r["SellValue"])]
        cur = end
    return out


# ---------------- tong hop ----------------
def compare(qt, dom, rate):
    """[[dd/mm/yy, gia quoc te nghin VND/kg, gia trong nuoc ban ra nghin VND/kg]] cho ngay co du 2 phia."""
    rows = []
    for d in sorted(dom):
        if d in qt:
            qt_kg = qt[d][0] / G_OZ * 1000 * rate
            rows.append(["%s/%s/%s" % (d[8:10], d[5:7], d[2:4]), round(qt_kg / 1000), round(dom[d][1] / KG_LUONG / 1000)])
    return rows[-366:]


def collect():
    """Lay du lieu, ghep lich su. Tra (obj trang 178, ghi chu, loi tung nguon)."""
    err, notes = {}, []
    now = datetime.datetime.now(VN)
    today = now.strftime("%Y-%m-%d")

    def safe(label, fn, *a):
        try:
            return fn(*a)
        except Exception as e:  # noqa: BLE001
            err[label] = str(e)[:160]
            return None
    xau, xag, rate = safe("gold-api XAU", intl, "XAU"), safe("gold-api XAG", intl, "XAG"), safe("VCB", vcb)
    pq = safe("Phu Quy", phuquy)
    sjc = safe("SJC", sjc_now)
    # lich su: ghep them, khong thay the
    h = safe("SJC lich su", sjc_history)
    if h:
        a, b = merge(F_SJC, h)
        notes.append("SJC lich su +%d ngay (%d dong)" % (b - a, b))
    for pid, key, path in ((2, "BAC", F_PQ_BAC), (1, "SJC", F_SJC_PQ)):
        hh = safe("Phu Quy lich su " + key, pq_history, pid, key)
        if hh:
            merge(path, hh)
    if sjc:
        merge(F_SJC, {today: list(sjc)})
    if pq:
        merge(F_PQ_BAC, {today: [float(pq[0]["B"][0]), float(pq[0]["B"][1])]})
        if "S" in pq[0]:
            merge(F_SJC_PQ, {today: [float(pq[0]["S"][0]), float(pq[0]["S"][1])]})
    if xau:
        merge(F_QT_VANG, {today: [xau]})
    if xag:
        merge(F_QT_BAC, {today: [xag]})
    if not (xau and xag and rate and pq):
        raise RuntimeError("Thieu nguon cot loi: %s" % json.dumps(err, ensure_ascii=False))
    # vang: uu tien SJC chinh chu, du phong SJC theo Phu Quy
    if sjc:
        gb, gs, glabel, gdom = sjc[0], sjc[1], "SJC", rd(F_SJC)
    elif "S" in pq[0]:
        gb, gs, glabel, gdom = pq[0]["S"][0], pq[0]["S"][1], "SJC (theo Phú Quý)", rd(F_SJC_PQ)
        notes.append("CANH BAO: SJC loi, dung gia SJC theo Phu Quy")
    else:
        raise RuntimeError("Khong co gia vang trong nuoc")
    kg = pq[1]
    obj = {
        "u": now.isoformat(),
        "r": round((rate["buy"] + rate["sell"]) / 2),
        "silver": {"unit": "Bạc thỏi Phú Quý 999 1Kilo", "i": round(xag, 3), "l": "Phú Quý",
                   "b": int(pq[0]["B"][0]), "s": int(pq[0]["B"][1]),
                   "bk": kg[0] if kg else None, "sk": kg[1] if kg else None,
                   "c": compare(rd(F_QT_BAC), rd(F_PQ_BAC), rate["sell"])},
        "gold": {"unit": "Vàng miếng SJC 1L/10L/1KG (999.9), quy theo lượng (37.5g)", "i": round(xau, 3), "l": glabel,
                 "b": int(gb), "s": int(gs), "bk": None, "sk": None,
                 "c": compare(rd(F_QT_VANG), gdom, rate["sell"])},
    }
    return obj, notes, err


def validate(o):
    if not (20000 < o["r"] < 40000):
        raise RuntimeError("Ty gia bat thuong: %s" % o["r"])
    if not (5 < o["silver"]["i"] < 500):
        raise RuntimeError("Gia bac quoc te bat thuong")
    if not (500 < o["gold"]["i"] < 20000):
        raise RuntimeError("Gia vang quoc te bat thuong")
    for k in ("silver", "gold"):
        if len(o[k]["c"]) < 30:
            raise RuntimeError("Lich su %s qua ngan (%d)" % (k, len(o[k]["c"])))
        if not o[k]["b"] or not o[k]["s"] or o[k]["b"] > o[k]["s"]:
            raise RuntimeError("Gia trong nuoc %s bat thuong" % k)
    # chenh lech trong nuoc / quoc te phai hop ly (vang SJC thuong +5..+25%, bac +5..+40%)
    for k, lo, hi in (("gold", -5, 40), ("silver", -5, 60)):
        last = o[k]["c"][-1]
        pct = (last[2] / last[1] - 1) * 100
        if not (lo < pct < hi):
            raise RuntimeError("Chenh lech %s %.1f%% bat thuong" % (k, pct))


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    obj, notes, err = collect()
    validate(obj)
    wp.save(PAGE, obj)
    msg = "da ghi trang 178: vang %s %s/%s, bac %s/%s, ty gia %s" % (obj["gold"]["l"], obj["gold"]["b"], obj["gold"]["s"], obj["silver"]["b"], obj["silver"]["s"], obj["r"])
    if notes:
        msg += "; " + "; ".join(notes)
    if err:
        msg += "; CANH BAO nguon loi: " + ", ".join(err)
    return msg


def run_dry():
    """Chay thu: lay du lieu + ghep lich su, khong ghi web."""
    obj, notes, err = collect()
    validate(obj)
    return "chay thu OK: vang %s %s/%s (QT %s), bac %s/%s (QT %s), ty gia %s, %d/%d diem so sanh; %s; loi: %s" % (
        obj["gold"]["l"], obj["gold"]["b"], obj["gold"]["s"], obj["gold"]["i"], obj["silver"]["b"], obj["silver"]["s"], obj["silver"]["i"],
        obj["r"], len(obj["gold"]["c"]), len(obj["silver"]["c"]), "; ".join(notes) or "-", json.dumps(err, ensure_ascii=False) if err else "khong")


if __name__ == "__main__":
    print(run_dry())
