"""Lich kinh te tuan (trang du lieu 176).

1. Dau tuan (sang thu Hai gio VN): neu trang 176 con la tuan cu, dung khung lich tuan moi tu ForexFactory
   (tin quan trong cua My, Trung Quoc, khu vuc euro, Anh, Nhat) + cac bao cao co dinh cua USDA, EIA.
   Tac vu Claude thu Hai 12h van viet lai phan dien giai tieng Viet; khung nay la ban du phong.
2. Moi ngay: tu dien so thuc te vao cac dong da qua gio cong bo, doc tu FRED (so lieu My) va EIA
   (ton kho dau tho, khi tu nhien). Khop theo ten in dam trong mo ta, nen dung duoc ca voi dong do Claude viet.

Dong du lieu: [ngay dd/mm, thu, gio VN, nhom, mo ta HTML, quan trong 0/1]
"""
import os
import re
import csv
import io
import json
import datetime
import requests
import wp

PAGE = 176
VN = datetime.timezone(datetime.timedelta(hours=7))
UA = {"User-Agent": wp.UA}
FF = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
FRED = "https://api.stlouisfed.org/fred/series"
THU = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
NUOC = {"USD": "Mỹ", "CNY": "Trung Quốc", "EUR": "khu vực euro", "GBP": "Anh", "JPY": "Nhật"}
# ten tin ForexFactory -> tieng Viet
TEN = [
    (r"^Core CPI m/m$", "CPI lõi (tháng/tháng)"), (r"^CPI m/m$", "CPI (tháng/tháng)"), (r"^CPI y/y$", "CPI (năm/năm)"),
    (r"^Core PPI m/m$", "PPI lõi (tháng/tháng)"), (r"^PPI m/m$", "PPI (tháng/tháng)"),
    (r"^Non-Farm Employment Change$", "Bảng lương phi nông nghiệp"), (r"^Unemployment Rate$", "Tỷ lệ thất nghiệp"),
    (r"^Unemployment Claims$", "Đơn xin trợ cấp thất nghiệp lần đầu"),
    (r"^Average Hourly Earnings m/m$", "Thu nhập bình quân theo giờ (tháng/tháng)"),
    (r"GDP q/q$", "GDP (quý/quý)"), (r"^GDP y/y$", "GDP (năm/năm)"),
    (r"^Core Retail Sales m/m$", "Doanh số bán lẻ lõi (tháng/tháng)"), (r"^Retail Sales m/m$", "Doanh số bán lẻ (tháng/tháng)"),
    (r"^Retail Sales y/y$", "Doanh số bán lẻ (năm/năm)"),
    (r"^Core PCE Price Index m/m$", "Chỉ số giá PCE lõi (tháng/tháng)"),
    (r"^Federal Funds Rate$", "Quyết định lãi suất của Fed"), (r"^FOMC Statement$", "Tuyên bố chính sách FOMC"),
    (r"^FOMC Press Conference$", "Họp báo của Chủ tịch Fed"), (r"^FOMC Meeting Minutes$", "Biên bản họp FOMC"),
    (r"^Fed Chair .* Speaks$", "Chủ tịch Fed phát biểu"),
    (r"^ISM Manufacturing PMI$", "PMI sản xuất ISM"), (r"^ISM Services PMI$", "PMI dịch vụ ISM"),
    (r"^Flash Manufacturing PMI$", "PMI sản xuất sơ bộ"), (r"^Flash Services PMI$", "PMI dịch vụ sơ bộ"),
    (r"^Manufacturing PMI$", "PMI sản xuất"), (r"^Non-Manufacturing PMI$", "PMI phi sản xuất"),
    (r"^Prelim UoM Consumer Sentiment$", "Niềm tin tiêu dùng ĐH Michigan (sơ bộ)"),
    (r"UoM Consumer Sentiment$", "Niềm tin tiêu dùng ĐH Michigan"),
    (r"UoM Inflation Expectations$", "Kỳ vọng lạm phát ĐH Michigan"),
    (r"^JOLTS Job Openings$", "Số việc làm trống JOLTS"), (r"^Durable Goods Orders m/m$", "Đơn hàng lâu bền (tháng/tháng)"),
    (r"^Industrial Production y/y$", "Sản xuất công nghiệp (năm/năm)"), (r"^Trade Balance$", "Cán cân thương mại"),
    (r"^Main Refinancing Rate$", "Quyết định lãi suất ECB"), (r"^ECB Press Conference$", "Họp báo ECB"),
    (r"^Official Bank Rate$", "Quyết định lãi suất BoE"), (r"^BOJ Policy Rate$", "Quyết định lãi suất BoJ"),
    (r"^Monetary Policy Statement$", "Tuyên bố chính sách tiền tệ"),
]
# tin USD muc Medium van dua vao lich
USD_MEDIUM = re.compile(r"Claims|PMI|PPI|Retail Sales|Durable|Consumer Sentiment|JOLTS|GDP|PCE", re.I)
# ForexFactory co cac tin nay nhung lich dung dong co dinh ben duoi
FF_BO = re.compile(r"Crude Oil Inventories|Natural Gas Storage", re.I)


# ---------------------------------------------------------------- khung tuan
def monday(d):
    return d - datetime.timedelta(days=d.weekday())


def nhan_tuan(mon):
    fri = mon + datetime.timedelta(days=4)
    return "Tuần %s – %s" % (mon.strftime("%d/%m"), fri.strftime("%d/%m/%Y"))


def et_to_vn(d, h, m):
    """Gio mien Dong nuoc My (tu tinh gio mua he) -> datetime VN."""
    y = d.year
    # DST: Chu nhat thu 2 thang 3 den Chu nhat dau thang 11
    s = datetime.date(y, 3, 8) + datetime.timedelta(days=(6 - datetime.date(y, 3, 8).weekday()) % 7)
    e = datetime.date(y, 11, 1) + datetime.timedelta(days=(6 - datetime.date(y, 11, 1).weekday()) % 7)
    off = -4 if s <= d < e else -5
    t = datetime.datetime(d.year, d.month, d.day, h, m, tzinfo=datetime.timezone(datetime.timedelta(hours=off)))
    return t.astimezone(VN)


def dong(t, nhom, mo_ta, qt):
    return [t.strftime("%d/%m"), THU[t.weekday()], t.strftime("%Hh%M"), nhom, mo_ta, qt]


def co_dinh(mon):
    """Bao cao hang tuan cua USDA, EIA (gio ET)."""
    out = []
    d = lambda k: mon + datetime.timedelta(days=k)  # noqa
    out.append(dong(et_to_vn(d(0), 11, 0), "Nông sản", "<b>Thanh tra xuất khẩu nông sản Mỹ</b> – Báo cáo hằng tuần về khối lượng ngũ cốc, đậu tương thực xuất.", 0))
    if 4 <= d(0).month <= 11:
        out.append(dong(et_to_vn(d(0), 16, 0), "Nông sản", "<b>Tiến độ mùa vụ của USDA</b> – Tiến độ gieo trồng, thu hoạch và chất lượng cây trồng Mỹ so với trung bình 5 năm.", 0))
    out.append(dong(et_to_vn(d(2), 10, 30), "Dầu thô, ngô", "<b>Tồn kho dầu thô (EIA)</b> – Báo cáo năng lượng hằng tuần của Mỹ, tác động tới giá dầu và cầu ngô (ethanol).", 1))
    out.append(dong(et_to_vn(d(3), 8, 30), "Nông sản", "<b>Doanh số xuất khẩu hàng tuần của USDA</b> – Doanh số bán nông sản Mỹ ra thế giới, nhất là đơn từ Trung Quốc.", 0))
    out.append(dong(et_to_vn(d(3), 10, 30), "Dầu thô, ngô", "<b>Tồn kho khí tự nhiên (EIA)</b> – Lượng khí tự nhiên lưu kho hằng tuần của Mỹ.", 0))
    return out


def ten_vn(title, cur):
    for pat, vn in TEN:
        if re.search(pat, title):
            return "%s (%s)" % (vn, NUOC[cur])
    return "%s (%s)" % (title, NUOC[cur])


def ff_rows(mon):
    j = requests.get(FF, headers=UA, timeout=60).json()
    out = []
    for x in j:
        cur, imp, title = x.get("country"), x.get("impact"), x.get("title", "")
        if cur not in NUOC or FF_BO.search(title) or "Bank Holiday" in title:
            continue
        if not (imp == "High" or (cur == "USD" and imp == "Medium" and USD_MEDIUM.search(title))):
            continue
        t = datetime.datetime.fromisoformat(x["date"]).astimezone(VN)
        if not mon <= t.date() <= mon + datetime.timedelta(days=6):
            continue
        mo = "<b>%s</b>" % ten_vn(title, cur)
        # so kieu Viet: 3.4% -> 3,4%
        f, p = [re.sub(r"(\d)\.(\d)", r"\1,\2", x.get(k) or "") for k in ("forecast", "previous")]
        if f or p:
            mo += " – " + ", ".join(s for s in (("dự báo " + f) if f else "", ("kỳ trước " + p) if p else "") if s) + "."
        out.append(dong(t, "Tin tức chung", mo, 1 if imp == "High" else 0))
    return out


def khung_tuan(mon):
    rows = ff_rows(mon) + co_dinh(mon)
    rows.sort(key=lambda r: (datetime.datetime.strptime(r[0] + "/%d" % mon.year, "%d/%m/%Y"), r[2]))
    sat = et_to_vn(mon + datetime.timedelta(days=4), 15, 30)
    n = ("Chữ đỏ là tin quan trọng. Báo cáo COT (CFTC) công bố lúc %s %s %s. "
         "Nguồn: ForexFactory, USDA, EIA; số thực tế tự cập nhật từ FRED và EIA." % (sat.strftime("%Hh%M"), THU[sat.weekday()], sat.strftime("%d/%m")))
    return {"w": nhan_tuan(mon), "n": n, "D": rows}


# ---------------------------------------------------------------- so thuc te
def vn_num(x, nd=1):
    return ("%.*f" % (nd, x)).replace(".", ",")


def fred_obs(sid, key, n=3):
    r = requests.get(FRED + "/observations", params={"series_id": sid, "api_key": key, "file_type": "json",
                                                     "sort_order": "desc", "limit": n}, timeout=60)
    r.raise_for_status()
    obs = [(o["date"], float(o["value"])) for o in r.json()["observations"] if o["value"] not in (".", "")]
    info = requests.get(FRED, params={"series_id": sid, "api_key": key, "file_type": "json"}, timeout=60).json()
    upd = info["seriess"][0]["last_updated"][:10]  # "2026-10-22 07:39:02-05"
    return obs, datetime.date.fromisoformat(upd)


def pct(obs, lag=1):
    return (obs[0][1] / obs[lag][1] - 1) * 100


# (mau khop ten in dam, ham tinh -> chuoi ket qua). Ham nhan (key, ngay cong bo) va tra None neu chua co so moi.
def _fred(sid, fmt, n=3):
    def f(key, ngay):
        obs, upd = fred_obs(sid, key, n)
        if upd < ngay or len(obs) < 2:
            return None
        return fmt(obs)
    return f


def _eia_dau(key, ngay):
    t = requests.get("https://ir.eia.gov/wpsr/table1.csv", headers=UA, timeout=60).content.decode("cp1252", "replace")
    rows = list(csv.reader(io.StringIO(t)))
    wk = datetime.datetime.strptime(rows[0][1], "%m/%d/%y").date()
    if not 0 <= (ngay - wk).days <= 7:
        return None
    for r in rows:
        if r and r[0].startswith("Commercial"):
            v = float(r[3])
            return "%s%s triệu thùng" % ("+" if v > 0 else "", vn_num(v))
    return None


def _eia_khi(key, ngay):
    j = json.loads(requests.get("https://ir.eia.gov/ngs/wngsr.json", headers=UA, timeout=60).content.decode("utf-8-sig"))
    wk = datetime.date.fromisoformat(j["current_week"])
    if not 0 <= (ngay - wk).days <= 8:
        return None
    v = j["series"][0]["calculated"]["net_change"]
    return "%s%d tỷ feet khối" % ("+" if v > 0 else "", v)


THUC_TE = [
    (r"trợ cấp thất nghiệp lần đầu", _fred("ICSA", lambda o: "%dK" % round(o[0][1] / 1000))),
    (r"cpi lõi.*mỹ|cpi.*lõi.*mỹ", _fred("CPILFESL", lambda o: vn_num(pct(o)) + "%")),
    (r"cpi.*mỹ.*năm/năm|cpi.*năm/năm.*mỹ", _fred("CPIAUCSL", lambda o: vn_num(pct(o, 12)) + "%", 14)),
    (r"cpi.*mỹ|cpi.*\(mỹ", _fred("CPIAUCSL", lambda o: vn_num(pct(o)) + "%")),
    (r"bảng lương phi nông nghiệp|việc làm phi nông nghiệp", _fred("PAYEMS", lambda o: "%+dK" % round(o[0][1] - o[1][1]))),
    (r"tỷ lệ thất nghiệp.*mỹ", _fred("UNRATE", lambda o: vn_num(o[0][1]) + "%")),
    (r"doanh số bán lẻ \(tháng/tháng\) \(mỹ|doanh số bán lẻ mỹ", _fred("RSAFS", lambda o: vn_num(pct(o)) + "%")),
    (r"pce lõi", _fred("PCEPILFE", lambda o: vn_num(pct(o)) + "%")),
    (r"ppi.*mỹ", _fred("PPIFIS", lambda o: vn_num(pct(o)) + "%")),
    (r"gdp.*mỹ", _fred("A191RL1Q225SBEA", lambda o: vn_num(o[0][1]) + "%")),
    (r"tồn kho dầu thô", _eia_dau),
    (r"tồn kho khí tự nhiên", _eia_khi),
]


def dien_thuc_te(rows, nam, key, now):
    n = 0
    for r in rows:
        mo = r[4]
        if "Thực tế" in mo or "công bố" in mo:
            continue
        m = re.search(r"<b>(.*?)</b>", mo)
        ten = (m.group(1) if m else mo).lower()
        try:
            t = datetime.datetime.strptime("%s/%d %s" % (r[0], nam, r[2].replace("h", ":")), "%d/%m/%Y %H:%M").replace(tzinfo=VN)
        except ValueError:
            continue
        if t > now:
            continue
        for pat, fn in THUC_TE:
            if re.search(pat, ten):
                if fn.__name__ == "f" and not key:
                    break
                ngay_et = (t - datetime.timedelta(hours=12)).date()  # ngay cong bo theo gio My
                try:
                    v = fn(key, ngay_et)
                except Exception:  # noqa  nguon tam loi: lan sau thu lai
                    v = None
                if v:
                    r[4] = mo.rstrip() + " <b>Thực tế: %s.</b>" % v
                    n += 1
                break
    return n


def run(dry=False):
    now = datetime.datetime.now(VN)
    mon = monday(now.date())
    key = os.environ.get("FRED_API_KEY", "")
    obj = wp.load(PAGE)
    notes, changed = [], False
    if obj.get("w") != nhan_tuan(mon) and now.weekday() <= 4:
        new = khung_tuan(mon)
        if len(new["D"]) < 5:
            raise RuntimeError("Khung lich tuan qua it dong (%d)" % len(new["D"]))
        obj.update(new)
        changed = True
        notes.append("dung khung %s (%d dong)" % (new["w"], len(new["D"])))
    k = dien_thuc_te(obj["D"], mon.year, key, now)
    if k:
        changed = True
        notes.append("dien %d so thuc te" % k)
    if changed and not dry:
        wp.save(PAGE, obj)
    return ("(thu) " if dry else "") + ("; ".join(notes) or "khong thay doi")


def run_dry():
    return run(dry=True)
