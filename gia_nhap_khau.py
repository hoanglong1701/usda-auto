"""Gia nhap khau theo nuoc xuat xu (UN Comtrade, API xem truoc cong khai) -> khoa "gnk" cua trang du lieu 1791.

Moi mat hang: top 3 nuoc nhap khau (theo khoi luong nam gan nhat), moi nuoc nhap tu dau, bao nhieu, gia CIF binh quan
(gia tri nuoc nhap khai bao / khoi luong) theo tung nuoc xuat xu: ca nam va 3 thang gan nhat co so lieu.
Nuoc nhap khong khai khoi luong (vd Mexico, Han Quoc, Ai Cap) thi lay khoi luong do nuoc xuat khau bao cao (doi ung).
Thue nhap khau, VAT de tinh gia ve kho nam o khoa "lc" (tac vu Claude) va "mfn" (job wto_thue); trang 299 tu tinh.
"""
import time
import datetime
import requests
import wp

PAGE = 1791
CT = "https://comtradeapi.un.org/public/v1/preview/C/%s/HS"
SP = {"dau": ("1201", "Đậu tương"), "ngo": ("1005", "Ngô"), "mi": ("1001", "Lúa mì"), "kho": ("2304", "Khô đậu tương"),
      "dd": ("1507", "Dầu đậu tương"), "gao": ("1006", "Gạo")}
TEN = {156: "Trung Quốc", 484: "Mexico", 392: "Nhật Bản", 410: "Hàn Quốc", 704: "Việt Nam", 360: "Indonesia", 608: "Philippines",
       528: "Hà Lan", 724: "Tây Ban Nha", 276: "Đức", 380: "Ý", 250: "Pháp", 56: "Bỉ", 620: "Bồ Đào Nha", 616: "Ba Lan",
       826: "Anh", 792: "Thổ Nhĩ Kỳ", 818: "Ai Cập", 12: "Algeria", 504: "Maroc", 788: "Tunisia", 682: "Ả Rập Xê Út",
       364: "Iran", 368: "Iraq", 784: "UAE", 887: "Yemen", 50: "Bangladesh", 586: "Pakistan", 699: "Ấn Độ", 764: "Thái Lan",
       458: "Malaysia", 490: "Đài Loan", 702: "Singapore", 104: "Myanmar", 116: "Campuchia", 418: "Lào", 170: "Colombia",
       604: "Peru", 218: "Ecuador", 152: "Chile", 862: "Venezuela", 320: "Guatemala", 222: "El Salvador", 340: "Honduras",
       188: "Costa Rica", 214: "Cộng hòa Dominica", 591: "Panama", 32: "Argentina", 76: "Brazil", 600: "Paraguay",
       858: "Uruguay", 68: "Bolivia", 124: "Canada", 842: "Mỹ", 804: "Ukraine", 643: "Nga", 398: "Kazakhstan", 36: "Úc",
       554: "New Zealand", 642: "Romania", 100: "Bulgaria", 348: "Hungary", 203: "Séc", 703: "Slovakia", 191: "Croatia",
       688: "Serbia", 498: "Moldova", 440: "Litva", 428: "Latvia", 233: "Estonia", 40: "Áo", 208: "Đan Mạch", 752: "Thụy Điển",
       246: "Phần Lan", 372: "Ireland", 300: "Hy Lạp", 710: "Nam Phi", 404: "Kenya", 566: "Nigeria", 288: "Ghana",
       384: "Bờ Biển Ngà", 686: "Senegal", 834: "Tanzania", 800: "Uganda", 231: "Ethiopia", 454: "Malawi", 894: "Zambia",
       716: "Zimbabwe", 508: "Mozambique", 204: "Benin", 4: "Afghanistan", 860: "Uzbekistan", 417: "Kyrgyzstan",
       762: "Tajikistan", 795: "Turkmenistan", 31: "Azerbaijan", 268: "Gruzia", 51: "Armenia", 112: "Belarus", 400: "Jordan",
       422: "Liban", 760: "Syria", 376: "Israel", 512: "Oman", 414: "Kuwait", 634: "Qatar", 48: "Bahrain", 144: "Sri Lanka",
       524: "Nepal", 496: "Mông Cổ", 344: "Hồng Kông", 446: "Ma Cao", 740: "Suriname", 328: "Guyana", 756: "Thụy Sĩ",
       578: "Na Uy", 705: "Slovenia", 196: "Síp", 470: "Malta", 442: "Luxembourg", 70: "Bosnia", 807: "Bắc Macedonia",
       8: "Albania", 434: "Libya", 729: "Sudan", 24: "Angola", 120: "Cameroon", 466: "Mali", 854: "Burkina Faso",
       562: "Niger", 148: "Chad", 646: "Rwanda", 108: "Burundi", 450: "Madagascar", 480: "Mauritius", 132: "Cabo Verde",
       388: "Jamaica", 780: "Trinidad và Tobago", 332: "Haiti", 192: "Cuba", 558: "Nicaragua",
       84: "Belize", 242: "Fiji", 598: "Papua New Guinea", 96: "Brunei", 626: "Đông Timor", 251: "Pháp", 381: "Ý",
       757: "Thụy Sĩ", 579: "Na Uy", 711: "Nam Phi"}
# cac nuoc nhap khau lon co the vao top 3 (ma M49 Comtrade)
CAND = [156, 484, 392, 410, 704, 360, 608, 528, 724, 276, 380, 250, 56, 620, 616, 826, 792, 818, 12, 504, 788, 682, 364,
        368, 784, 50, 586, 699, 764, 458, 490, 702, 170, 604, 218, 152, 320, 222, 340, 188, 214, 32, 76, 124, 842, 643, 710,
        404, 566, 384, 686, 887, 144, 344, 400, 376]
UA = {"User-Agent": wp.UA}
KL_MIN = 0.01  # nuoc xuat xu duoi 1% khoi luong thi gop vao "Khác"


def ten(c):
    return TEN.get(c, "Mã %s" % c)


def ct(freq, **params):
    for k in range(5):
        r = requests.get(CT % freq, params=params, headers=UA, timeout=90)
        if r.status_code == 429:
            time.sleep(8 * (k + 1))
            continue
        r.raise_for_status()
        time.sleep(1.5)
        return [x for x in r.json().get("data", []) if not x.get("partner2Code") and x.get("customsCode") in (None, "C00")
                and x.get("motCode") in (None, 0)]
    raise RuntimeError("Comtrade qua tai")


def kg(x, uoc=True):
    """Khoi luong kg; uoc=False thi bo khoi luong do Comtrade uoc (vd Ai Cap: cung mot don gia cho moi nguon)."""
    if not uoc and (x.get("isNetWgtEstimated") or x.get("isQtyEstimated")):
        return 0.0
    if x.get("netWgt"):
        return float(x["netWgt"])
    if x.get("qtyUnitCode") == 8 and x.get("qty"):
        return float(x["qty"])
    return 0.0


def gt(x):
    return float(x.get("cifvalue") or x.get("primaryValue") or 0)


def thang_lui(ym, n):
    y, m = divmod(int(ym[:4]) * 12 + int(ym[4:]) - 1 - n, 12)
    return "%d%02d" % (y, m + 1)


def xep_hang(hs):
    """Top 3 nuoc nhap khau cua ma hs: (nam, [(trieu tan, ma nuoc, uoc?)])."""
    nam = datetime.date.today().year
    for y in (nam - 1, nam - 2):
        rows = [x for x in ct("A", reporterCode=",".join(map(str, CAND)), partnerCode=0, period=y, cmdCode=hs, flowCode="M")
                if x.get("partnerCode") == 0]
        if len(rows) < 25:
            continue
        p = sorted(gt(x) / kg(x) for x in rows if kg(x) and gt(x))
        gia = p[len(p) // 2] if p else None
        ds = []
        for x in rows:
            q = kg(x)
            if q:
                ds.append((q / 1e9, x["reporterCode"], not kg(x, False)))
            elif gia and gt(x):
                ds.append((gt(x) / gia / 1e9, x["reporterCode"], True))
        ds.sort(reverse=True)
        return y, ds[:3]
    raise RuntimeError("Comtrade chua co du lieu nhap khau %s" % hs)


def theo_xuat_xu(rows, nhap, hs, period, freq):
    """rows cua nuoc nhap theo doi tac -> {doi tac: [gia tri USD, kg, doi_ung?, kg uoc, gia tri ung voi kg]}; bu khoi
    luong bang so lieu nuoc xuat. kg uoc (Comtrade tu uoc) chi dung cho ty trong, khong tinh don gia."""
    d = {}
    for x in rows:
        c = x.get("partnerCode")
        if not c or str(x.get("cmdCode")) != hs:
            continue
        v = d.setdefault(c, [0.0, 0.0, False, 0.0, 0.0])
        v[0] += gt(x)
        v[3] += kg(x)
        if kg(x, False):
            v[1] += kg(x, False)
            v[4] += gt(x)
    tong = sum(v[0] for v in d.values())
    thieu = [c for c, v in d.items() if not v[1] and v[0] > tong * 0.01]
    if thieu:
        for x in ct(freq, reporterCode=",".join(map(str, thieu)), partnerCode=nhap, period=period, cmdCode=hs, flowCode="X"):
            c = x.get("reporterCode")
            if c in d and kg(x, False):
                d[c][1] += kg(x, False)
                d[c][2] = True
                d[c][4] = d[c][0]
    return d


def bang(d):
    """[[nuoc, nghin tan, % khoi luong, USD/tan CIF, doi_ung]] xep theo khoi luong, them dong Khac.
    Nguon chi co khoi luong uoc: van tinh ty trong nhung khong co don gia."""
    kl = {c: max(v[1], v[3]) for c, v in d.items()}
    tq = sum(kl.values())
    if tq <= 0:
        return []
    out, kv, kq, kk = [], 0.0, 0.0, 0.0
    for c in sorted(d, key=lambda c_: -kl[c_]):
        _, q, du, _, v = d[c]
        k = kl[c]
        if not k:
            continue
        if k / tq < KL_MIN or len(out) >= 6:
            kk += k
            if q:
                kv += v
                kq += q
            continue
        g = v / q * 1000 if q else None
        if g is not None and not 50 <= g <= 6000:
            g = None
        out.append([ten(c), round(k / 1e6, 1), round(k / tq * 100, 1), round(g) if g else None, 1 if du else 0])
    if kk > 0:
        g = kv / kq * 1000 if kq else 0
        out.append(["Khác", round(kk / 1e6, 1), round(kk / tq * 100, 1), round(g) if 50 <= g <= 6000 else None, 0])
    return out


def thang_moi(nhap_list, cmds):
    """{nuoc: thang moi nhat (YYYYMM) co so lieu nhap cac ma cmds}."""
    t = datetime.date.today()
    ym = "%d%02d" % (t.year, t.month)
    out = {}
    for n in range(2, 18):
        m = thang_lui(ym, n)
        for x in ct("M", reporterCode=",".join(map(str, nhap_list)), partnerCode=0, period=m, cmdCode=",".join(cmds),
                    flowCode="M"):
            out.setdefault(x["reporterCode"], m)
        if len(out) == len(nhap_list):
            break
    # vai nuoc (vd Trung Quoc) chi bao theo doi tac, khong co dong tong the gioi
    for c in nhap_list:
        if c in out:
            continue
        for n in range(2, 18):
            m = thang_lui(ym, n)
            if any(x.get("partnerCode") for x in ct("M", reporterCode=c, period=m, cmdCode=",".join(cmds), flowCode="M")):
                out[c] = m
                break
    return out


def lay():
    res, tops = {}, {}
    for sp, (hs, tsp) in SP.items():
        y, top = xep_hang(hs)
        tops[sp] = (y, top)
    nhap_all = sorted({c for _, top in tops.values() for _, c, _ in top})
    moi = thang_moi(nhap_all, [hs for hs, _ in SP.values()])
    thang = {}  # (nuoc, thang) -> rows theo doi tac, moi nuoc goi chung cac ma
    for sp, (y, top) in tops.items():
        hs, tsp = SP[sp]
        ds = []
        for tr, c, uoc in top:
            rows = ct("A", reporterCode=c, period=y, cmdCode=hs, flowCode="M")
            nam = bang(theo_xuat_xu(rows, c, hs, y, "A"))
            m3 = None
            if c in moi:
                gop = {}
                for n in range(3):
                    m = thang_lui(moi[c], n)
                    if (c, m) not in thang:
                        thang[(c, m)] = ct("M", reporterCode=c, period=m, cmdCode=",".join(h for h, _ in SP.values()),
                                           flowCode="M")
                    for k, v in theo_xuat_xu(thang[(c, m)], c, hs, m, "M").items():
                        g = gop.setdefault(k, [0.0, 0.0, False, 0.0, 0.0])
                        g[0] += v[0]
                        g[1] += v[1]
                        g[2] = g[2] or v[2]
                        g[3] += max(v[1], v[3])
                        g[4] += v[4]
                rows3 = bang(gop)
                if rows3:
                    m3 = {"tu": thang_lui(moi[c], 2), "den": moi[c], "rows": rows3}
            if uoc and nam:  # tong theo nguon (co khoi luong doi ung) sat hon uoc theo don gia trung vi
                tr = sum(r[1] for r in nam) / 1000
            ds.append({"nuoc": ten(c), "ma": c, "kl": round(tr, 2), "uoc": 1 if uoc else 0, "nam": nam, "m3": m3})
        res[sp] = {"ten": tsp, "hs": hs, "y": y, "top": ds}
    return res


def run():
    gnk = lay()
    du = sum(1 for v in gnk.values() for t in v["top"] if t["nam"])
    if du < 12:
        raise RuntimeError("Chi co so lieu xuat xu cho %d/18 cap nuoc-mat hang" % du)
    obj = wp.load(PAGE) or {}
    gnk = {"asof": datetime.date.today().isoformat(), "sp": gnk}
    old = obj.get("gnk") or {}
    if old.get("sp") == gnk["sp"]:
        return "Gia nhap khau Comtrade khong doi"
    obj["gnk"] = gnk
    wp.save(PAGE, obj)
    return "da ghi gia nhap khau theo xuat xu: %s" % "; ".join(
        "%s %s (%s)" % (v["ten"], v["y"], ", ".join(t["nuoc"] for t in v["top"])) for v in gnk["sp"].values())


def thu():
    gnk = lay()
    for sp, v in gnk.items():
        print("==", v["ten"], v["y"])
        for t in v["top"]:
            print("  ", t["nuoc"], t["kl"], "tr tan", "(uoc)" if t["uoc"] else "")
            for r in t["nam"]:
                print("      nam", r)
            if t["m3"]:
                print("      3 thang", t["m3"]["tu"], "-", t["m3"]["den"])
                for r in t["m3"]["rows"]:
                    print("        ", r)
    return "chay thu, khong ghi"
