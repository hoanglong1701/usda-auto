"""Tom tat bang chu cho cac trang du lieu (truong "tt" trong #gd-data).

Trang hien thi ve bieu do bang JS nen Google va cac cong cu AI khong doc duoc so lieu. mu-plugin GDHH247
(1.6.0+) in doan "tt" thanh HTML ngay tren trang hien thi. Job nay chay sau moi job du lieu (data.yml),
chi ghi lai trang nao co tom tat thay doi.

"tt" la danh sach doan van, hoac dict {id trang hien thi: [doan van]} khi mot trang du lieu phuc vu nhieu trang.
"""
import datetime
import wp

MUA = ["12–2", "1–3", "2–4", "3–5", "4–6", "5–7", "6–8", "7–9", "8–10", "9–11", "10–12", "11–1"]


def n0(x):
    return "{:,.0f}".format(x).replace(",", ".")


def n1(x, nd=1):
    return ("{:,.%df}" % nd).format(x).replace(",", "#").replace(".", ",").replace("#", ".")


def pc(x):
    return ("+" if x > 0 else "") + n1(x) + "%"


def dmy(iso):
    iso = str(iso)
    if len(iso) >= 10:
        return "%s/%s/%s" % (iso[8:10], iso[5:7], iso[:4])
    return "%s/%s" % (iso[5:7], iso[:4]) if len(iso) >= 7 else iso


# ---------------------------------------------------------------- 178 vang bac
def tt_178(d):
    t = datetime.datetime.fromisoformat(d["u"])
    r = d["r"]
    out = []
    for k, ten in (("gold", "Vàng"), ("silver", "Bạc")):
        x = d[k]
        qd = x["i"] * r * 37.5 / 31.1035
        ch = x["s"] - qd
        s = ("%s %s: mua vào %s đồng/lượng, bán ra %s đồng/lượng. Giá thế giới %s USD/oz, quy đổi theo tỷ giá "
             "Vietcombank %s đồng/USD được khoảng %s đồng/lượng; giá bán trong nước cao hơn %s đồng (%s)."
             % (ten, x["l"] if k == "gold" else "(%s)" % x["unit"], n0(x["b"]), n0(x["s"]), n1(x["i"]),
                n0(r), n0(qd), n0(ch), pc(ch / qd * 100)))
        c = x.get("c") or []
        if len(c) > 25:
            a, b = c[-23][2], c[-1][2]
            if a:
                s += " So với khoảng một tháng trước (%s), giá trong nước %s." % (c[-23][0], pc((b / a - 1) * 100))
        out.append(s)
    out[0] = "Cập nhật lúc %s ngày %s. " % (t.strftime("%Hh%M"), t.strftime("%d/%m/%Y")) + out[0]
    return out


# ---------------------------------------------------------------- 1519 kim loai, ca phe, duong
def tt_1519(d):
    kl = []
    ngay = ""
    for k, m in d["lme"].items():
        last = m.get("last")
        if not last:
            continue
        ngay = last[0]
        p = m["p"]
        s = "%s %s USD/tấn" % (m["n"], n0(last[1]))
        if len(p) > 1 and p[-2]:
            s += " (%s so với phiên trước)" % pc((p[-1] / p[-2] - 1) * 100)
        if last[2]:
            s += ", tồn kho %s tấn" % n0(last[2])
        kl.append(s)
    p_lme = "Giá kim loại cơ bản trên sàn LME ngày %s: %s." % (dmy(ngay), "; ".join(kl)) if kl else ""
    bc = sorted(d.get("bc", {}).get("ds", []), key=lambda x: x.get("ngay", ""), reverse=True)
    XU = {"du": "dư cung", "thieu": "thiếu cung", "can": "cân bằng"}

    def bao_cao(lst):
        return ["%s (%s) – %s%s: %s" % (x["org"], dmy(x["ngay"]), x["ten"],
                                         (", xu hướng " + XU[x["xu_huong"]]) if x.get("xu_huong") in XU else "", x.get("y", ""))
                for x in lst[:3]]
    kim_loai = [x for x in bc if x.get("nhom") == "kl"]
    nlcn = [x for x in bc if x.get("nhom") != "kl"]
    psd = []
    for k, ten, dv, he in (("cf", "cà phê", "triệu bao 60 kg", 1000), ("su", "đường", "triệu tấn", 1000)):
        z = d.get("psd", {}).get(k)
        if not z:
            continue
        y = z["y"][-1]
        psd.append("niên vụ %d/%s, %s thế giới: sản xuất %s %s, tiêu thụ %s, xuất khẩu %s, tồn kho cuối kỳ %s"
                   % (y, str(y + 1)[2:], ten, n1(z["sx"][-1] / he), dv, n1(z["tt"][-1] / he), n1(z["xk"][-1] / he),
                      n1(z["dk"][-1] / he)))
    p_psd = ("Theo USDA (PSD), " + "; ".join(psd) + ".") if psd else ""
    kl_page = [x for x in [p_lme] + bao_cao(kim_loai) if x]
    nl_page = [x for x in [p_psd] + bao_cao(nlcn) if x]
    return {"300": kl_page, "301": nl_page, "107": [x for x in [p_lme, p_psd] if x] + bao_cao(bc)[:3]}


# ---------------------------------------------------------------- 1526 nong san va ENSO
def tt_1526(d):
    om, ov = d["oni_last"]
    st = "El Niño" if ov >= 0.5 else ("La Niña" if ov <= -0.5 else "trung tính")
    dang = [e for e in d.get("dot", []) if e.get("dd")]
    s1 = "Chỉ số ONI (NOAA) kỳ tháng %s/%s là %s, ENSO đang ở trạng thái %s" % (MUA[int(om[5:7]) - 1], om[:4], ("+" if ov > 0 else "") + n1(ov, 2), st)
    if dang:
        e = dang[-1]
        s1 += " %s, đợt bắt đầu từ tháng %s/%s" % (e["muc"], e["start"][5:7], e["start"][:4])
    s1 += "."
    ten = {s[0]: s[1] for s in d["sp"]}

    def phan(keys):
        fut = {k: v for k, v in (d.get("fut") or {}).items() if k in keys}
        f = ["%s %s %s (1 tháng %s, 1 năm %s)" % (ten[k], n1(v["gia"], 2), v["dv"], pc(v["m1"]) if v.get("m1") is not None else "–",
                                                  pc(v["y1"]) if v.get("y1") is not None else "–") for k, v in fut.items()]
        s2 = ("Giá futures gần nhất (%s): %s." % (dmy(next(iter(fut.values()))["ngay"]), "; ".join(f))) if f else ""
        tb = {k: v for k, v in d.get("tb", {}).items() if k in keys}
        el = ["%s %s" % (ten[k], pc(v["el"])) for k, v in tb.items() if v.get("el") is not None]
        la = ["%s %s" % (ten[k], pc(v["la"])) for k, v in tb.items() if v.get("la") is not None]
        s3 = ("Từ năm 1970, trung bình 12 tháng sau khi đợt El Niño bắt đầu, giá thay đổi: %s. Sau đợt La Niña: %s."
              % (", ".join(el), ", ".join(la))) if el else ""
        return [x for x in (s1, s2, s3) if x]
    # trang 299 (nong san) va 301 (ca phe, duong) moi trang mot phan, tu 30/10/2026
    return {"299": phan(("dau_tuong", "ngo", "lua_mi", "gao")), "301": phan(("arabica", "robusta", "duong"))}


# ---------------------------------------------------------------- 801 USDA hang tuan
def tt_801(d):
    out = []
    w = d.get("wasde")
    if w:
        TEN = {"ngo": "ngô", "dau_tuong": "đậu tương", "lua_mi": "lúa mì"}
        parts = []
        for k, ten in TEN.items():
            x = w.get(k)
            if not x:
                continue
            parts.append("%s: sản lượng %s triệu giạ (tháng trước %s), năng suất %s giạ/mẫu, tồn kho cuối kỳ %s triệu giạ"
                         % (ten, n0(x["prod"][1]), n0(x["prod"][0]), n1(x["yield"][1]), n0(x["end"][1])))
        if parts:
            out.append("Báo cáo WASDE tháng %s/%s của USDA, niên vụ %s của Mỹ – %s." % (w["mon"][5:7], w["mon"][:4], w["my"], "; ".join(parts)))
    i = d.get("insp")
    if i and i.get("sum"):
        T = {"CORN": "ngô", "SOYBEANS": "đậu tương", "WHEAT": "lúa mì"}
        parts = ["%s %s tấn" % (v, n0(i["sum"][k][0])) for k, v in T.items() if k in i["sum"]]
        out.append("Thanh tra xuất khẩu ngũ cốc của Mỹ tuần kết thúc %s: %s." % (dmy(i["wk"]), ", ".join(parts)))
    e = d.get("esr")
    if e:
        T = {"ngo": "ngô", "dau_tuong": "đậu tương", "lua_mi": "lúa mì"}
        parts = []
        wk = ""
        for k, v in T.items():
            c = (e.get(k) or {}).get("cur")
            if c:
                wk = c["wk"]
                parts.append("%s đã xuất %s nghìn tấn, còn %s nghìn tấn đã bán chưa giao" % (v, n0(c["acc"]), n0(c["out"])))
        if parts:
            out.append("Doanh số xuất khẩu của Mỹ niên vụ hiện tại tính đến tuần %s: %s." % (dmy(wk), "; ".join(parts)))
    return out


# ---------------------------------------------------------------- 847 to chuc quoc te
def tt_847(d):
    out = []
    for k in ("imf", "wb", "oecd", "wto", "fao"):
        r = (d.get("rep") or {}).get(k)
        if r and r.get("hl"):
            out.append("%s: %s" % (r["n"].split(" – ")[0], r["hl"][0]))
    return out


# ---------------------------------------------------------------- 176 lich kinh te
def tt_176(d):
    rows = d.get("D") or []
    qt = [r for r in rows if r[5]]
    import re
    ten = lambda r: re.sub("<[^>]+>", "", re.search(r"<b>(.*?)</b>", r[4]).group(1)) if "<b>" in r[4] else re.sub("<[^>]+>", "", r[4])[:80]  # noqa
    s = "Lịch kinh tế %s có %d sự kiện, trong đó %d tin quan trọng: %s." % (
        d.get("w", "").replace("Tuần", "tuần"), len(rows), len(qt),
        "; ".join("%s %s %s" % (r[1], r[0], ten(r)) for r in qt[:10]))
    tt = []
    for r in rows:
        if "Thực tế:" in r[4]:
            import re as _re
            m = _re.search(r"Thực tế: ([^<]+?)\.?</b>", r[4])
            if m:
                tt.append("%s %s: %s" % (ten(r), r[0], m.group(1)))
    out = [s]
    if tt:
        out.append("Số liệu đã công bố: " + "; ".join(tt) + ".")
    return out


# ---------------------------------------------------------------- 227 ket qua khuyen nghi
def tt_227(d):
    k = d.get("kpi") or {}
    if not k:
        return []
    s = ("Kết quả khuyến nghị GDHH247 từ %s đến %s: %d lệnh, %d lệnh có lãi (tỷ lệ thắng %s), tổng lãi/lỗ %s USD, NAV hiện tại %s USD."
         % (dmy(k["first_date"]), dmy(k["last_date"]), k["total_trades"], k["wins"], pc(k["win_rate"] * 100).lstrip("+"),
            n1(k["total_pl"]), n1(k["current_nav"])))
    g = ["%s %d lệnh, thắng %s" % (x["name"], x["trades"], pc(x["win_rate"] * 100).lstrip("+"))
         for x in d.get("groups", []) if x.get("trades") and x.get("win_rate") is not None]
    return [s] + (["Theo nhóm hàng: " + "; ".join(g) + "."] if g else [])


# ---------------------------------------------------------------- 1791 gia ve theo xuat xu (trang 299)
SPN = {"dau": "Đậu tương", "ngo": "Ngô", "mi": "Lúa mì", "kho": "Khô đậu tương"}


def _thue(d, nuoc, sp, xx):
    """Giong khoi #gdlc tren trang 299: lc -> nk (hang My, da kiem tra) -> MFN WTO (bo neu > 30%, ngoai han ngach)."""
    lc = ((d.get("lc") or {}).get(nuoc) or {}).get(sp) or {}
    if xx in lc:
        return lc[xx]
    r = (((d.get("nk") or {}).get("t") or {}).get(nuoc) or {}).get(sp) or {}
    if xx == "Mỹ":
        if r.get("my") is not None:
            return r["my"]
        if r.get("kt") and isinstance(r.get("mfn"), (int, float)):
            return r["mfn"] + (r.get("bs") or 0)
    if "*" in lc:
        return lc["*"]
    w = ((d.get("mfn") or {}).get(nuoc) or {}).get(sp)
    if w:
        return w[0] if w[0] <= 30 else None
    return r.get("mfn") if isinstance(r.get("mfn"), (int, float)) else None


def tt_1791(d):
    f = wp.load(1728)
    tuyen = (d.get("cuoc") or {}).get("tuyen") or {}
    out = []
    for sp, tsp in SPN.items():
        nguon = []
        if sp == "mi":
            m = f.get("mi") or {}
            for x, g in m.get("gia", []):
                k = {"Mỹ": ["Mỹ (vùng Vịnh)"], "EU": ["Pháp"], "Nga": ["Nga", "Biển Đen"]}.get(x, [x])
                nguon.append(("Mỹ" if x == "Mỹ" else x, x, k, g))
        else:
            for x in (f.get("cs") or {}).get(sp, []):
                n = x[0]
                goc = "Mỹ" if n.startswith("Mỹ") else n.split(" (")[0]
                nguon.append((goc, n, ["Mỹ (vùng Vịnh)"] if goc == "Mỹ" else [goc], x[1]))
        nuoc = []
        for v in ((d.get("gnk") or {}).get("sp") or {}).get(sp, {}).get("top", []):
            nuoc.append(v["nuoc"])
        for k in tuyen:
            if k.split("|")[1] not in nuoc:
                nuoc.append(k.split("|")[1])
        for nc in nuoc:
            vat = ((d.get("lc") or {}).get(nc) or {}).get("vat") or 0
            dong = []
            for goc, ten, ks, gia in nguon:
                cb = next((tuyen[k + "|" + nc] for k in ks if k + "|" + nc in tuyen), None)
                t = _thue(d, nc, sp, goc)
                if cb is None or t is None:
                    continue
                dong.append((round((gia + cb[0]) * (1 + t / 100) * (1 + vat / 100)), ten))
            if len(dong) < 2:
                continue
            dong.sort()
            out.append("%s về %s (FOB mới nhất cộng cước biển, thuế nhập khẩu%s): %s; rẻ nhất là %s, đắt nhất %s cao hơn %s."
                       % (tsp, nc, ", VAT" if vat else "", "; ".join("%s %s USD/tấn" % (t, n0(g)) for g, t in dong),
                          dong[0][1], dong[-1][1], n1((dong[-1][0] / dong[0][0] - 1) * 100) + "%"))
    for sp, v in ((d.get("gnk") or {}).get("sp") or {}).items():
        top = v.get("top") or []
        if top:
            out.append("%s: 3 nước nhập khẩu lớn nhất năm %s theo UN Comtrade là %s." % (
                v["ten"], v["y"], ", ".join("%s (%s triệu tấn)" % (t["nuoc"], n1(t["kl"])) for t in top)))
    return out


NGUON = {178: tt_178, 1519: tt_1519, 1526: tt_1526, 801: tt_801, 847: tt_847, 176: tt_176, 227: tt_227, 1791: tt_1791}


def run(dry=False):
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    ghi, loi = [], []
    for pid, fn in NGUON.items():
        try:
            obj = wp.load(pid)
            tt = fn(obj)
            if dry:
                print(pid, tt)
            if not tt or tt == obj.get("tt"):
                continue
            obj["tt"] = tt
            if not dry:
                wp.save(pid, obj)
            ghi.append(str(pid))
        except Exception as e:  # noqa  moi trang doc lap
            loi.append("%d: %s %s" % (pid, type(e).__name__, str(e)[:80]))
    msg = ("(thu) " if dry else "") + ("ghi tom tat trang " + ", ".join(ghi) if ghi else "khong thay doi")
    if loi:
        # chay sau moi job du lieu: loi tom tat khong lam do job du lieu, chi ghi lai trong status.json
        if dry or not ghi:
            raise RuntimeError(msg + " | LOI " + " | ".join(loi))
        msg += " | LOI " + " | ".join(loi)
    return msg


def run_dry():
    return run(dry=True)
