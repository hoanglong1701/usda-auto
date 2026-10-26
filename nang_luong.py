"""Phan tich nang luong (trang 302) va trang du lieu an "du-lieu-nang-luong".

Nguon (khong can khoa API):
  - EIA International (opendata/bulk/INTL.zip): san luong dau tho, tieu thu dau, san luong/tieu thu/xuat/nhap khau khi.
  - EIA STEO (opendata/bulk/STEO.zip): can doi cung cau dau the gioi, ton kho OECD, gia Brent, Henry Hub (co du bao).
  - UN Comtrade (API xem truoc cong khai): dau tho (HS 2709) va LNG (HS 271111) theo so lieu nuoc nhap khau bao cao
    (nhieu nuoc xuat khau khong cong bo doi tac) -> top xuat khau, nhap khau va "xuat di dau".
Trang 302 duoc dung lan dau (khi chua co khoi #gdnl); cac lan sau chi cap nhat du lieu.
Nhom nang luong chua giao dich tai GDHH247: trang ghi ro dieu nay.
"""
import io
import re
import json
import time
import zipfile
import datetime
import requests
import wp

SLUG = "du-lieu-nang-luong"
PAGE = 302
UA = {"User-Agent": wp.UA}
CT = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
# EIA: ma chi tieu -> (ten, don vi chuoi, don vi hien thi)
EIA = {
    "57-1": ("Sản xuất dầu thô", "TBPD", "nghìn thùng/ngày"),
    "5-2": ("Tiêu thụ dầu", "TBPD", "nghìn thùng/ngày"),
    "26-1": ("Sản xuất khí tự nhiên", "BCM", "tỷ m³"),
    "26-2": ("Tiêu thụ khí tự nhiên", "BCM", "tỷ m³"),
    "26-4": ("Xuất khẩu khí tự nhiên", "BCM", "tỷ m³"),
    "26-3": ("Nhập khẩu khí tự nhiên", "BCM", "tỷ m³"),
}
# ten nuoc tieng Viet theo ma ISO3 (EIA) va ma M49 (Comtrade)
VN3 = {"USA": "Mỹ", "SAU": "Ả Rập Xê Út", "RUS": "Nga", "CAN": "Canada", "IRQ": "Iraq", "CHN": "Trung Quốc", "ARE": "UAE",
       "BRA": "Brazil", "IRN": "Iran", "KWT": "Kuwait", "KAZ": "Kazakhstan", "NOR": "Na Uy", "MEX": "Mexico", "QAT": "Qatar",
       "NGA": "Nigeria", "LBY": "Libya", "DZA": "Algeria", "AGO": "Angola", "OMN": "Oman", "GUY": "Guyana", "IND": "Ấn Độ",
       "JPN": "Nhật Bản", "KOR": "Hàn Quốc", "DEU": "Đức", "FRA": "Pháp", "GBR": "Anh", "ITA": "Ý", "ESP": "Tây Ban Nha",
       "IDN": "Indonesia", "SGP": "Singapore", "THA": "Thái Lan", "TUR": "Thổ Nhĩ Kỳ", "AUS": "Úc", "MYS": "Malaysia",
       "TKM": "Turkmenistan", "EGY": "Ai Cập", "PAK": "Pakistan", "ARG": "Argentina", "NLD": "Hà Lan", "UKR": "Ukraine",
       "VNM": "Việt Nam", "TWN": "Đài Loan", "BEL": "Bỉ", "POL": "Ba Lan", "UZB": "Uzbekistan", "AZE": "Azerbaijan",
       "VEN": "Venezuela", "COL": "Colombia", "ECU": "Ecuador", "TTO": "Trinidad và Tobago", "BGD": "Bangladesh",
       "PHL": "Philippines", "ZAF": "Nam Phi", "ISR": "Israel", "HUN": "Hungary", "AUT": "Áo", "CZE": "Séc", "SVK": "Slovakia",
       "GRC": "Hy Lạp", "PRT": "Bồ Đào Nha", "SWE": "Thụy Điển", "FIN": "Phần Lan", "CHL": "Chile", "PER": "Peru",
       "MAR": "Maroc", "BGR": "Bulgaria", "ROU": "Romania", "LTU": "Litva", "PNG": "Papua New Guinea", "BHR": "Bahrain"}
M49 = {156: "CHN", 699: "IND", 842: "USA", 410: "KOR", 392: "JPN", 276: "DEU", 528: "NLD", 380: "ITA", 724: "ESP", 250: "FRA",
       764: "THA", 702: "SGP", 826: "GBR", 616: "POL", 300: "GRC", 792: "TUR", 124: "CAN", 56: "BEL", 752: "SWE", 246: "FIN",
       620: "PRT", 458: "MYS", 36: "AUS", 710: "ZAF", 360: "IDN", 704: "VNM", 586: "PAK", 440: "LTU", 642: "ROU", 100: "BGR",
       203: "CZE", 703: "SVK", 348: "HUN", 40: "AUT", 376: "ISR", 818: "EGY", 76: "BRA", 152: "CHL", 604: "PER", 504: "MAR",
       490: "TWN", 50: "BGD", 608: "PHL", 682: "SAU", 643: "RUS", 368: "IRQ", 784: "ARE", 579: "NOR", 398: "KAZ", 414: "KWT",
       566: "NGA", 484: "MEX", 24: "AGO", 434: "LBY", 512: "OMN", 364: "IRN", 328: "GUY", 170: "COL", 31: "AZE", 634: "QAT",
       12: "DZA", 598: "PNG", 218: "ECU", 862: "VEN", 32: "ARG", 48: "BHR", 780: "TTO"}
NHAP = [156, 699, 842, 410, 392, 276, 528, 380, 724, 250, 764, 702, 826, 616, 300, 792, 124, 56, 752, 246, 620, 458, 36, 710,
        360, 704, 586, 440, 642, 100, 203, 703, 348, 40, 376, 818, 76, 152, 604, 504, 490, 50, 608]
XUAT_DAU = [682, 643, 368, 842, 124, 784, 579, 398, 414, 76, 566, 484, 24, 434, 512, 364, 826, 328, 170, 31, 12, 458, 218]
XUAT_LNG = [842, 634, 36, 643, 458, 566, 360, 12, 512, 598]
# tuyen van chuyen quan trong (EIA World Oil Transit Chokepoints, so lieu lam tron)
TUYEN = [
    ["Eo biển Hormuz", "Vịnh Ba Tư ra biển Ả Rập", "Khoảng 20 triệu thùng/ngày dầu (khoảng 1/5 tiêu thụ thế giới) và khoảng 1/5 LNG thế giới (Qatar, UAE)",
     "Dầu của Ả Rập Xê Út, Iraq, UAE, Kuwait, Iran sang châu Á. Gián đoạn ở đây là rủi ro lớn nhất với giá dầu."],
    ["Eo biển Malacca", "Ấn Độ Dương sang Biển Đông", "Trên 20 triệu thùng/ngày, tuyến dầu lớn nhất theo khối lượng",
     "Dầu từ Trung Đông, châu Phi tới Trung Quốc, Nhật Bản, Hàn Quốc, Đông Nam Á."],
    ["Kênh đào Suez và đường ống SUMED", "Biển Đỏ sang Địa Trung Hải", "Khoảng 8–9 triệu thùng/ngày trước năm 2024, giảm mạnh khi tàu tránh Biển Đỏ",
     "Dầu, sản phẩm dầu và LNG giữa vùng Vịnh, châu Âu và châu Á."],
    ["Eo biển Bab el-Mandeb", "Biển Đỏ ra vịnh Aden", "Khoảng 8–9 triệu thùng/ngày trước năm 2024, giảm mạnh do rủi ro an ninh",
     "Nối Suez với Ấn Độ Dương; tàu chuyển hướng vòng qua mũi Hảo Vọng làm tăng cước và thời gian."],
    ["Mũi Hảo Vọng (Nam Phi)", "Đại Tây Dương sang Ấn Độ Dương", "Tăng mạnh từ 2024 khi tàu tránh Biển Đỏ",
     "Tuyến thay thế Suez; dầu Tây Phi sang châu Á, dầu vùng Vịnh sang châu Âu, Mỹ."],
    ["Eo biển Đan Mạch", "Biển Baltic ra Biển Bắc", "Khoảng 4–5 triệu thùng/ngày", "Chủ yếu dầu của Nga xuất từ các cảng Baltic."],
    ["Eo biển Thổ Nhĩ Kỳ (Bosporus)", "Biển Đen ra Địa Trung Hải", "Khoảng 3–4 triệu thùng/ngày",
     "Dầu của Nga và Kazakhstan (CPC) qua cảng Novorossiysk; cũng là tuyến ngũ cốc Biển Đen."],
    ["Kênh đào Panama", "Đại Tây Dương sang Thái Bình Dương", "Khoảng 2 triệu thùng/ngày dầu và sản phẩm, một phần LNG của Mỹ",
     "Hạn chế khi mực nước hồ Gatun thấp (mùa khô, El Niño)."],
]


def ten(iso):
    return VN3.get(iso, iso)


# ---------------------------------------------------------------- EIA
def eia_intl():
    b = requests.get("https://www.eia.gov/opendata/bulk/INTL.zip", headers=UA, timeout=600).content
    data = {k: {} for k in EIA}
    with zipfile.ZipFile(io.BytesIO(b)).open("INTL.txt") as f:
        for ln in f:
            try:
                j = json.loads(ln)
            except ValueError:
                continue
            m = re.match(r"INTL\.(\d+-\d+)-([A-Z0-9]+)-([A-Z]+)\.A$", j.get("series_id", ""))
            if not m or m.group(1) not in EIA or EIA[m.group(1)][1] != m.group(3):
                continue
            data[m.group(1)][m.group(2)] = {int(p): v for p, v in j.get("data", []) if isinstance(v, (int, float))}
    out = {}
    for k, (tn, _, dv) in EIA.items():
        d = data[k]
        w = d.get("WORL", {})
        nuoc = {c: s for c, s in d.items() if len(c) == 3}
        if not w or not nuoc:
            raise RuntimeError("EIA thieu chi tieu %s" % k)
        # nam moi nhat co du lieu cua phan lon cac nuoc lon
        y = max(yy for yy in w if sum(1 for s in nuoc.values() if s.get(yy)) >= 40)
        ys = [yy for yy in range(y - 9, y + 1)]
        top = sorted(((s.get(y) or 0, c) for c, s in nuoc.items()), reverse=True)[:10]
        out[k] = {"t": tn, "dv": dv, "y": y, "ys": ys, "w": round(w.get(y, 0), 1),
                  "wl": [round(w.get(yy, 0), 1) for yy in ys],
                  "top": [[ten(c), round(v, 1), round(v / w[y] * 100, 1) if w.get(y) else None,
                           [round(nuoc[c].get(yy) or 0, 1) for yy in ys]] for v, c in top]}
    return out


def eia_steo():
    man = requests.get("https://www.eia.gov/opendata/bulk/manifest.txt", headers=UA, timeout=60).json()
    upd = man["dataset"]["STEO"]["last_updated"][:10]
    b = requests.get("https://www.eia.gov/opendata/bulk/STEO.zip", headers=UA, timeout=300).content
    want = {"PAPR_WORLD": "sx", "PATC_WORLD": "tt", "T3_STCHANGE_WORLD": "tk", "PASC_OECD_T3": "oecd", "BREPUUS": "brent",
            "NGHHUUS": "hh", "PAPR_OPEC": "opec", "PAPR_NONOPEC": "ngoai_opec"}
    s = {}
    with zipfile.ZipFile(io.BytesIO(b)).open("STEO.txt") as f:
        for ln in f:
            try:
                j = json.loads(ln)
            except ValueError:
                continue
            sid = j.get("series_id", "")
            core = sid.replace("STEO.", "").rsplit(".", 1)[0]
            if core in want and sid.endswith(".A"):
                s[want[core]] = {int(p): v for p, v in j["data"] if isinstance(v, (int, float))}
    if len(s) < 6:
        raise RuntimeError("STEO thieu chuoi (%d)" % len(s))
    nam = datetime.date.today().year
    rows = [[y] + [round(s.get(k, {}).get(y), 2) if s.get(k, {}).get(y) is not None else None
                   for k in ("sx", "tt", "tk", "oecd", "brent", "hh", "opec", "ngoai_opec")] for y in range(nam - 2, nam + 2)]
    return {"upd": upd, "rows": rows}


# ---------------------------------------------------------------- Comtrade
def ct(reporters, partner, cmd, flow, period):
    for k in range(4):
        r = requests.get(CT, params={"reporterCode": ",".join(str(x) for x in reporters), "partnerCode": partner, "period": period,
                                     "cmdCode": cmd, "flowCode": flow}, headers=UA, timeout=90)
        if r.status_code == 429:
            time.sleep(10 * (k + 1))
            continue
        r.raise_for_status()
        time.sleep(1.5)
        return [x for x in r.json().get("data", []) if not x.get("partner2Code") and x.get("customsCode") in (None, "C00")
                and x.get("motCode") in (None, 0)]
    raise RuntimeError("Comtrade qua tai")


def comtrade(cmd, xuat, top_dest=8):
    uoc = set()

    def mt(x):
        """kg -> trieu tan; nuoc chi bao gia tri (vd Trung Quoc 2025) thi uoc theo gia trung binh."""
        if x.get("netWgt"):
            return x["netWgt"] / 1e9
        if x.get("primaryValue") and gia:
            uoc.add(M49.get(x["reporterCode"]))
            return x["primaryValue"] / gia / 1e9
        return 0

    nam = datetime.date.today().year
    y = None
    for yy in (nam - 1, nam - 2, nam - 3):
        tong = ct(NHAP, 0, cmd, "M", yy)
        # can du cac nuoc mua lon (Trung Quoc, An Do, Nhat, Han) moi dung duoc so lieu "xuat di dau"
        co = {x["reporterCode"] for x in tong}
        if len(tong) >= 20 and {156, 699, 392, 410} <= co:
            y = yy
            break
    if not y:
        raise RuntimeError("Comtrade chua co du lieu nhap khau %s" % cmd)
    p = sorted(x["primaryValue"] / x["netWgt"] for x in tong if x.get("netWgt") and x.get("primaryValue"))
    gia = p[len(p) // 2] if p else None  # USD/kg trung vi
    nk = sorted(((mt(x), M49.get(x["reporterCode"])) for x in tong if M49.get(x["reporterCode"])), reverse=True)
    xk, dest = [], {}
    for e in xuat:
        rows = [x for x in ct([c for c in NHAP if c != e], e, cmd, "M", y) if M49.get(x["reporterCode"])]
        tot = sum(mt(x) for x in rows)
        if tot <= 0.5:
            continue
        xk.append((tot, M49[e]))
        ds = sorted(((mt(x), M49[x["reporterCode"]]) for x in rows), reverse=True)
        dest[ten(M49[e])] = [[ten(c), round(v, 2), round(v / tot * 100, 1)] for v, c in ds[:top_dest]]
    xk.sort(reverse=True)
    return {"y": y, "nk": [[ten(c), round(v, 1)] for v, c in nk[:10]], "xk": [[ten(c), round(v, 1)] for v, c in xk[:10]],
            "dest": {ten(c): dest[ten(c)] for _, c in xk[:10]}, "uoc": sorted(ten(c) for c in uoc if c)}


# ---------------------------------------------------------------- trang du lieu
def tim_trang(s):
    base = wp._cfg()[0] + "/index.php/wp-json/wp/v2/pages"
    r = s.get(base, params={"slug": SLUG, "status": "publish,draft", "context": "edit", "_fields": "id"}, timeout=60)
    r.raise_for_status()
    if r.json():
        return r.json()[0]["id"]
    c = s.post(base, json={"title": "Dữ liệu năng lượng", "slug": SLUG, "status": "publish",
                           "content": '<!-- wp:html -->\n<pre id="gd-data" style="display:none">{}</pre>\n<!-- /wp:html -->'}, timeout=60)
    if c.status_code >= 400:
        raise RuntimeError("Tao trang du lieu nang luong loi %d: %s" % (c.status_code, c.text[:200]))
    return c.json()["id"]


def dung_trang():
    raw = wp.get_raw(PAGE)
    if 'id="gdnl"' in raw:
        return False
    import os
    os.makedirs(os.path.join("data", "backup"), exist_ok=True)
    with open(os.path.join("data", "backup", "trang302_%s.html" % datetime.date.today().isoformat()), "w", encoding="utf-8") as f:
        f.write(raw)
    tuyen = "".join("<tr><td><b>%s</b></td><td>%s</td><td>%s</td><td>%s</td></tr>" % tuple(t) for t in TUYEN)
    html = KHOI.replace("__TUYEN__", tuyen)
    back = wp.set_raw(PAGE, html)
    if 'id="gdnl"' not in back:
        raise RuntimeError("Doc lai trang 302 khong thay khoi nang luong")
    return True


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    notes = []
    obj = {"asof": datetime.date.today().isoformat(), "eia": eia_intl(), "steo": eia_steo()}
    notes.append("EIA %s, STEO %s" % (obj["eia"]["57-1"]["y"], obj["steo"]["upd"]))
    try:
        obj["dau"] = comtrade("2709", XUAT_DAU)
        obj["lng"] = comtrade("271111", XUAT_LNG, 6)
        notes.append("Comtrade %s" % obj["dau"]["y"])
    except Exception as e:  # noqa  Comtrade loi thi giu so lieu cu
        notes.append("CANH BAO Comtrade: %s" % str(e)[:100])
    pid = tim_trang(wp._sess())
    try:
        old = wp.load(pid)
        for k in ("dau", "lng"):
            if k not in obj and k in old:
                obj[k] = old[k]
    except RuntimeError:
        pass
    wp.save(pid, obj)
    notes.append("ghi trang %d" % pid)
    if dung_trang():
        notes.append("dung trang 302")
    return "; ".join(notes)


KHOI = r'''<!-- wp:paragraph -->
<p>Cung cầu dầu thô và khí tự nhiên thế giới: cân đối cung cầu và dự báo của EIA, top 10 quốc gia sản xuất, tiêu thụ, xuất nhập khẩu, dầu thô và LNG xuất đi đâu, các tuyến vận chuyển quan trọng và vị thế COT. Số liệu tự cập nhật hằng tháng.</p>
<!-- /wp:paragraph -->

<!-- wp:html -->
<style>
#gdnl{font-family:inherit;color:#222;margin:8px 0 24px}
#gdnl h3{font-size:18px;margin:22px 0 4px}
#gdnl .n-sub{font-size:13px;color:#666;margin:0 0 10px;line-height:1.5}
#gdnl .n-box{border:1px solid #e6dede;border-radius:10px;padding:14px;background:#fff;margin:10px 0}
#gdnl .n-warn{border-left:5px solid #c00000;background:#fff7f7;font-size:14px;line-height:1.55}
#gdnl .n-tw{overflow-x:auto}
#gdnl table{border-collapse:collapse;width:100%;font-size:14px;min-width:560px}
#gdnl th,#gdnl td{padding:6px 8px;border-bottom:1px solid #eee;text-align:right;vertical-align:top}
#gdnl th:first-child,#gdnl td:first-child{text-align:left}
#gdnl th{background:#faf7f7;font-weight:600;color:#444}
#gdnl .n-row{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 10px}
#gdnl .n-row button{border:1px solid #d9d2d2;background:#fff;color:#222;border-radius:999px;padding:6px 13px;font-size:14px;cursor:pointer;font-family:inherit}
#gdnl .n-row button.on{background:#c00000;border-color:#c00000;color:#fff;font-weight:600}
#gdnl .n-row select{padding:6px 8px;border:1px solid #cfd5dc;border-radius:6px;font-size:14px;background:#fff}
#gdnl .bar{display:grid;grid-template-columns:130px 1fr 110px;gap:8px;align-items:center;font-size:14px;margin:4px 0}
#gdnl .bar i{display:block;height:16px;background:#c00000;border-radius:3px;min-width:2px}
#gdnl .bar span:last-child{text-align:right;white-space:nowrap}
#gdnl .tuyen td{text-align:left;white-space:normal}
#gdnl .n-note{font-size:13px;color:#666;margin:8px 0 0;line-height:1.55}
@media (max-width:600px){#gdnl .bar{grid-template-columns:96px 1fr 90px;font-size:13px}}
</style>
<div id="gdnl">
<div class="n-box n-warn"><b>Lưu ý:</b> nhóm năng lượng (dầu thô, khí tự nhiên) hiện <b>chưa được giao dịch</b> tại GDHH247. Trang này cung cấp dữ liệu cung cầu để tham khảo, vì giá năng lượng tác động trực tiếp tới nông sản (ethanol, dầu sinh học, phân bón, cước vận tải) và kim loại.</div>

<h3>Cân đối cung cầu dầu thế giới (EIA STEO)</h3>
<p class="n-sub" data-r="steo-sub">Đang tải số liệu…</p>
<div class="n-box n-tw" data-r="steo"></div>

<h3>Top 10 quốc gia</h3>
<p class="n-sub">Chọn chỉ tiêu. Thanh đỏ là quy mô năm gần nhất, cột cuối là tỷ trọng trong tổng thế giới.</p>
<div class="n-box"><div class="n-row" data-r="top-btn"></div><div data-r="top"></div><p class="n-note" data-r="top-nt"></p></div>

<h3>Dầu thô và LNG xuất đi đâu</h3>
<p class="n-sub">Theo số liệu nhập khẩu do các nước mua báo cáo (UN Comtrade), vì nhiều nước xuất khẩu không công bố chi tiết đối tác. Đơn vị triệu tấn; 1 triệu tấn dầu thô/năm tương đương khoảng 20 nghìn thùng/ngày.</p>
<div class="n-box"><div class="n-row"><button type="button" class="on" data-k="dau">Dầu thô</button><button type="button" data-k="lng">LNG</button><select data-r="nuoc"></select></div><div data-r="dest"></div><p class="n-note" data-r="dest-nt"></p></div>

<h3>Các báo cáo cung cầu năng lượng</h3>
<div class="n-box" data-r="bc"><p class="n-sub">EIA STEO (khoảng tuần đầu hằng tháng), OPEC MOMR (giữa tháng), IEA Oil Market Report (giữa tháng). Tóm tắt báo cáo mới nhất được cập nhật cùng nhóm báo cáo cung cầu hằng tháng.</p></div>

<h3>Các tuyến vận chuyển năng lượng quan trọng</h3>
<p class="n-sub">Các "điểm nghẽn" trên biển mà phần lớn dầu và LNG thế giới phải đi qua. Số liệu làm tròn theo EIA (World Oil Transit Chokepoints) và các báo cáo năm 2024–2025.</p>
<div class="n-box n-tw"><table class="tuyen"><tr><th>Tuyến</th><th>Vị trí</th><th>Khối lượng</th><th>Vai trò</th></tr>__TUYEN__</table></div>
<p class="n-note" data-r="nt"></p>
</div>
<script>
(function(){
var R=document.getElementById("gdnl");if(!R){return}
function Q(k){return R.querySelector('[data-r="'+k+'"]')}
function nf(n,d){if(n===null||n===undefined){return "–"}return Number(n).toLocaleString("vi-VN",{minimumFractionDigits:d||0,maximumFractionDigits:d||0})}
function sg(n,d){if(n===null||n===undefined){return "–"}return (n>0?"+":"")+nf(n,d)}
function bars(rows,dv,nd){var mx=0;rows.forEach(function(r){if(r[1]>mx){mx=r[1]}});var o="";rows.forEach(function(r){o+='<div class="bar"><span>'+r[0]+'</span><i style="width:'+(mx?r[1]/mx*100:0).toFixed(1)+'%"></i><span>'+nf(r[1],nd)+(r[2]!==undefined?" · "+nf(r[2],1)+"%":"")+'</span></div>'});return o}
fetch("/index.php/wp-json/wp/v2/pages?slug=du-lieu-nang-luong").then(function(r){return r.json()}).then(function(a){
var doc=new DOMParser().parseFromString(a[0].content.rendered,"text/html");var D=JSON.parse(doc.getElementById("gd-data").textContent);
var S=D.steo,y0=new Date().getFullYear();
Q("steo-sub").textContent="Báo cáo Short-Term Energy Outlook của Cơ quan Thông tin Năng lượng Mỹ, bản cập nhật "+S.upd.slice(8,10)+"/"+S.upd.slice(5,7)+"/"+S.upd.slice(0,4)+". Năm "+y0+" và "+(y0+1)+" có phần dự báo.";
var h='<table><tr><th>Chỉ tiêu</th>';S.rows.forEach(function(r){h+="<th>"+r[0]+(r[0]>=y0?" (dự báo)":"")+"</th>"});h+="</tr>";
[["Sản xuất dầu và chất lỏng (triệu thùng/ngày)",1,2],["Tiêu thụ (triệu thùng/ngày)",2,2],["Rút tồn kho ròng (+) / tích trữ (−)",3,2],["Tồn kho thương mại OECD cuối kỳ (triệu thùng)",4,0],["Sản xuất OPEC",7,2],["Sản xuất ngoài OPEC",8,2],["Giá Brent (USD/thùng)",5,1],["Giá khí Henry Hub (USD/MMBtu)",6,2]].forEach(function(c){h+="<tr><td>"+c[0]+"</td>";S.rows.forEach(function(r){h+="<td>"+nf(r[c[1]],c[2])+"</td>"});h+="</tr>"});
Q("steo").innerHTML=h+'</table><p class="n-note">Sản xuất lớn hơn tiêu thụ nghĩa là thị trường dư cung, tồn kho tăng (thường gây áp lực giảm giá); ngược lại là thiếu cung.</p>';
var K=["57-1","5-2","26-1","26-2","26-4","26-3"],cur=K[0];
function tb(){var b=Q("top-btn");b.innerHTML="";K.forEach(function(k){var e=document.createElement("button");e.type="button";e.textContent=D.eia[k].t;if(k===cur){e.className="on"}e.onclick=function(){cur=k;tb()};b.appendChild(e)});
var x=D.eia[cur],rows=x.top.map(function(t){return [t[0],t[1],t[2]]});Q("top").innerHTML=bars(rows,x.dv,0);
var t=x.top[0],ch=t[3][0]?(t[3][t[3].length-1]/t[3][0]-1)*100:null;
Q("top-nt").textContent="Năm "+x.y+", đơn vị "+x.dv+". Tổng thế giới "+nf(x.w,0)+" "+x.dv+" (so với "+x.ys[0]+": "+sg(x.wl[0]?(x.w/x.wl[0]-1)*100:null,1)+"%). Đứng đầu là "+t[0]+", thay đổi "+sg(ch,1)+"% trong 10 năm. Nguồn: EIA International."}
tb();
var loai="dau";function ds(){var C=D[loai];if(!C){Q("dest").innerHTML='<p class="n-sub">Chưa có số liệu.</p>';return}var s=Q("nuoc");var keep=s.value;s.innerHTML="";Object.keys(C.dest).forEach(function(n){var o=document.createElement("option");o.value=n;o.textContent=n;s.appendChild(o)});if(C.dest[keep]){s.value=keep}
var n=s.value,rows=C.dest[n]||[];Q("dest").innerHTML=bars(rows.map(function(r){return [r[0],r[1],r[2]]}),"triệu tấn",2);
Q("dest-nt").textContent="Năm "+C.y+". Top 10 nước xuất khẩu (theo số liệu nước mua): "+C.xk.map(function(r){return r[0]+" "+nf(r[1],1)}).join(", ")+" triệu tấn. Top 10 nước nhập khẩu: "+C.nk.map(function(r){return r[0]+" "+nf(r[1],1)}).join(", ")+" triệu tấn."+((C.uoc||[]).length?" Khối lượng của "+C.uoc.join(", ")+" ước tính theo giá trị nhập khẩu và giá trung bình vì nước này chỉ công bố giá trị.":"")}
R.querySelectorAll("[data-k]").forEach(function(b){b.onclick=function(){loai=b.getAttribute("data-k");R.querySelectorAll("[data-k]").forEach(function(x){x.className=x===b?"on":""});ds()}});Q("nuoc").onchange=ds;ds();
Q("nt").textContent="Nguồn: EIA (International, STEO), UN Comtrade. Cập nhật "+D.asof.slice(8,10)+"/"+D.asof.slice(5,7)+"/"+D.asof.slice(0,4)+". Nội dung tham khảo, không phải khuyến nghị đầu tư."
}).catch(function(){Q("steo-sub").textContent="Chưa tải được số liệu, bạn vui lòng tải lại trang."});
fetch("/index.php/wp-json/wp/v2/pages/1519").then(function(r){return r.json()}).then(function(j){var doc=new DOMParser().parseFromString(j.content.rendered,"text/html");var D=JSON.parse(doc.getElementById("gd-data").textContent);
var ds=((D.bc||{}).ds||[]).filter(function(x){return x.nhom==="en"});if(!ds.length){return}
var o="";ds.forEach(function(x){o+='<div style="margin:0 0 12px"><b>'+x.org+" – "+x.ten+"</b> <span style=\"color:#666;font-size:13px\">("+(x.ngay||"")+")</span><br>"+(x.y||"")+"</div>"});Q("bc").innerHTML=o}).catch(function(){});
})();
</script>
<!-- /wp:html -->
'''
