"""Cap nhat doan SO LIEU cua khoi "Cac yeu to co ban" tren trang 111 (Vang bac vat chat).

Chi thay phan nam giua 2 marker trong noi dung trang:
    <!-- gd:so-lieu-vang:start --> ... <!-- gd:so-lieu-vang:end -->
Phan nhan dinh (Fed, dia chinh tri, kich ban) KHONG do job nay viet: tac vu Claude soan hang tuan,
anh Long duyet roi dang (marker gd:nhan-dinh-vang va gd:boi-canh-vang).

Nguon (deu chay duoc tu GitHub Actions):
 - Yahoo chart: GC=F, SI=F (10 nam, nen ngay) - gia, thay doi 1 thang, dinh ky luc, ty le vang/bac
 - FRED API (FRED_API_KEY): DGS10, DFII10, DTWEXBGS, DFEDTARL/DFEDTARU
Ghi them data/yeu_to.json de tac vu Claude doc lai khi soan nhan dinh.
Khong co WP_* (chay thu tren may) thi chi in HTML, khong ghi web.
"""
import os
import re
import json
import datetime
import urllib.request

import requests

import wp

PAGE_ID = 111
START = "<!-- gd:so-lieu-vang:start -->"
END = "<!-- gd:so-lieu-vang:end -->"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
FRED_API = "https://api.stlouisfed.org/fred/series/observations"
UTC = datetime.timezone.utc
VN = datetime.timezone(datetime.timedelta(hours=7))


def _now():
    return datetime.datetime.now(UTC)


# ---------------------------------------------------------------- dinh dang so kieu Viet Nam

def vn(x, d=0):
    s = "{:,.{d}f}".format(x, d=d)
    return s.replace(",", "#").replace(".", ",").replace("#", ".")


def dmy(d):
    return d.strftime("%d/%m/%Y")


def dm(d):
    return d.strftime("%d/%m")


def pct_phrase(cur, old):
    """'giảm 6,5%' / 'tăng 1,2%' / 'gần như không đổi'."""
    p = (cur / old - 1) * 100
    if abs(p) < 0.05:
        return "gần như không đổi"
    return "%s %s%%" % ("tăng" if p > 0 else "giảm", vn(abs(p), 1))


def pt_phrase(cur, old):
    """Thay doi tinh bang diem phan tram (cho loi suat)."""
    p = cur - old
    if abs(p) < 0.005:
        return "gần như không đổi"
    return "%s %s điểm %%" % ("tăng" if p > 0 else "giảm", vn(abs(p), 2))


# ---------------------------------------------------------------- Yahoo

def yahoo_daily(symbol):
    """Tra ve list (date, close, high) chi gom cac nen DA DONG CUA.
    Nen ngay D (gan moc 00:00 New York) chi chot sau 17:00 New York = toi da 22:00 UTC ngay D."""
    r = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/%s" % symbol,
        params={"range": "10y", "interval": "1d"},
        headers={"User-Agent": UA}, timeout=60,
    )
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    cutoff = _now() - datetime.timedelta(hours=22)
    out = []
    for t, c, h in zip(res["timestamp"], q["close"], q["high"]):
        if c is None:
            continue
        d = datetime.datetime.fromtimestamp(t, UTC).date()
        if d > cutoff.date():
            continue
        out.append((d, float(c), float(h) if h is not None else float(c)))
    if not out:
        raise RuntimeError("Yahoo %s: khong co nen da dong cua" % symbol)
    return out


def month_ago(series, last_date):
    """Gia tri cua diem gan nhat <= last_date - 30 ngay (series: list tuple, phan tu 0 la date)."""
    target = last_date - datetime.timedelta(days=30)
    cand = [p for p in series if p[0] <= target]
    return cand[-1] if cand else None


# ---------------------------------------------------------------- FRED

def fred(series_id, key, limit=45):
    url = (FRED_API + "?series_id=%s&api_key=%s&file_type=json&sort_order=desc&limit=%d"
           % (series_id, key, limit))
    req = urllib.request.Request(url, headers={"User-Agent": "gdhh247-yeuto/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        obs = json.loads(r.read().decode("utf-8")).get("observations", [])
    pts = [(datetime.date.fromisoformat(o["date"]), float(o["value"]))
           for o in obs if o.get("value") not in (None, "", ".")]
    if not pts:
        raise RuntimeError("FRED %s: khong co du lieu" % series_id)
    return sorted(pts)


# ---------------------------------------------------------------- thu thap + dung HTML

def collect():
    gold = yahoo_daily("GC=F")
    silver = yahoo_daily("SI=F")
    # Yahoo doi khi bo trong 1 nen (vd. vang 20/10) - lay ngay gan nhat ca hai cung co de ty le dung phien
    common = sorted(set(p[0] for p in gold) & set(p[0] for p in silver))
    if not common:
        raise RuntimeError("Yahoo: vang va bac khong co phien chung")
    gold = [p for p in gold if p[0] <= common[-1]]
    silver = [p for p in silver if p[0] <= common[-1]]
    g_d, g_c, _ = gold[-1]
    s_d, s_c, _ = silver[-1]
    if not (500 < g_c < 20000) or not (5 < s_c < 500):
        raise RuntimeError("Gia Yahoo bat thuong: vang %s, bac %s" % (g_c, s_c))
    if (_now().date() - g_d).days > 6:
        raise RuntimeError("Gia vang Yahoo cu: nen cuoi %s" % g_d)
    g_max = max(gold, key=lambda p: p[1])
    g_hi = max(gold, key=lambda p: p[2])
    data = {
        "asof": _now().astimezone(VN).date().isoformat(),
        "gold": {"date": g_d.isoformat(), "close": g_c,
                 "month_ago": None, "record_close": [g_max[0].isoformat(), g_max[1]],
                 "record_high": [g_hi[0].isoformat(), g_hi[2]]},
        "silver": {"date": s_d.isoformat(), "close": s_c, "month_ago": None},
        "ratio": g_c / s_c,
        "fred": {}, "fred_errors": {},
    }
    ga = month_ago(gold, g_d)
    sa = month_ago(silver, s_d)
    if ga:
        data["gold"]["month_ago"] = [ga[0].isoformat(), ga[1]]
    if sa:
        data["silver"]["month_ago"] = [sa[0].isoformat(), sa[1]]

    key = os.environ.get("FRED_API_KEY")
    for sid in ("DGS10", "DFII10", "DTWEXBGS", "DFEDTARL", "DFEDTARU"):
        if not key:
            data["fred_errors"][sid] = "thieu FRED_API_KEY"
            continue
        try:
            pts = fred(sid, key)
            last = pts[-1]
            ago = month_ago(pts, last[0])
            data["fred"][sid] = {"date": last[0].isoformat(), "value": last[1],
                                 "month_ago": [ago[0].isoformat(), ago[1]] if ago else None}
        except Exception as e:  # noqa
            data["fred_errors"][sid] = "%s: %s" % (type(e).__name__, e)
    return data


def build_html(data):
    D = datetime.date.fromisoformat
    g, s, f = data["gold"], data["silver"], data["fred"]
    rec_d, rec_v = D(g["record_close"][0]), g["record_close"][1]

    p1 = ("<strong>Cập nhật ngày %s</strong> (số liệu tự động, giá đóng cửa phiên %s). "
          "Giá vàng thế giới (hợp đồng tương lai COMEX) quanh %s USD/oz"
          % (dmy(D(data["asof"])), dm(D(g["date"])), vn(g["close"])))
    if g["month_ago"]:
        p1 += ", %s so với một tháng trước" % pct_phrase(g["close"], g["month_ago"][1])
    if g["close"] < rec_v:
        p1 += (" và thấp hơn %s%% so với mức đóng cửa cao kỷ lục %s USD/oz (%s)"
               % (vn((1 - g["close"] / rec_v) * 100, 1), vn(rec_v), dmy(rec_d)))
    else:
        p1 += ", đang ở vùng cao kỷ lục"
    p1 += ". Bạc quanh %s USD/oz" % vn(s["close"], 2)
    if s["month_ago"]:
        p1 += " (%s trong một tháng)" % pct_phrase(s["close"], s["month_ago"][1])
    p1 += ", tỷ lệ vàng/bạc khoảng %s lần." % vn(data["ratio"])

    parts = []
    if "DGS10" in f:
        x = f["DGS10"]
        t = "Lợi suất trái phiếu Mỹ kỳ hạn 10 năm %s%% (%s" % (vn(x["value"], 2), dm(D(x["date"])))
        if x["month_ago"]:
            t += "; %s so với một tháng trước" % pt_phrase(x["value"], x["month_ago"][1])
        parts.append(t + ")")
    if "DFII10" in f:
        parts.append("lợi suất thực 10 năm %s%%" % vn(f["DFII10"]["value"], 2))
    if "DTWEXBGS" in f:
        x = f["DTWEXBGS"]
        t = "chỉ số USD rộng của Fed %s (%s" % (vn(x["value"], 1), dm(D(x["date"])))
        if x["month_ago"]:
            t += "; %s trong một tháng" % pct_phrase(x["value"], x["month_ago"][1])
        parts.append(t + ")")
    if "DFEDTARL" in f and "DFEDTARU" in f:
        parts.append("lãi suất mục tiêu của Fed %s–%s%%"
                     % (vn(f["DFEDTARL"]["value"], 2), vn(f["DFEDTARU"]["value"], 2)))
    p2 = (parts[0][0].upper() + parts[0][1:] + (", " + ", ".join(parts[1:]) if parts[1:] else "") + ".") if parts else ""

    src = ("Nguồn: Yahoo Finance (COMEX GC=F, SI=F)"
           + (", FRED (DGS10, DFII10, DTWEXBGS, DFEDTARL/DFEDTARU)" if parts else "")
           + ". Đoạn số liệu tự động cập nhật mỗi sáng thứ Ba–thứ Bảy; phần nhận định bên dưới do GDHH247 biên soạn hằng tuần.")

    html = START + "\n<p class=\"wp-block-paragraph\">" + p1 + "</p>\n"
    if p2:
        html += "<p class=\"wp-block-paragraph\">" + p2 + "</p>\n"
    html += "<p class=\"has-small-font-size wp-block-paragraph\"><em>" + src + "</em></p>\n" + END
    return html


def run():
    data = collect()
    html = build_html(data)
    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", "yeu_to.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(data, html=html), fh, ensure_ascii=False, indent=1)

    warn = ("; CANH BAO FRED: %s" % data["fred_errors"]) if data["fred_errors"] else ""
    if not wp.enabled():
        print(html)
        return "chay thu (khong co WP_*), vang %s ngay %s%s" % (data["gold"]["close"], data["gold"]["date"], warn)

    raw = wp.get_raw(PAGE_ID)
    pat = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if len(pat.findall(raw)) != 1:
        raise RuntimeError("Trang %d khong co dung 1 cap marker %s ... %s (co the tac vu khac da ghi de trang)"
                           % (PAGE_ID, START, END))
    new = pat.sub(lambda m: html, raw)
    if new == raw:
        return "khong doi%s" % warn
    back = wp.set_raw(PAGE_ID, new)
    if re.sub(r"\s+", "", html) not in re.sub(r"\s+", "", back):
        raise RuntimeError("Doc lai trang %d khong thay doan so lieu vua ghi" % PAGE_ID)
    return "da cap nhat trang %d: vang %s (%s)%s" % (PAGE_ID, vn(data["gold"]["close"]), data["gold"]["date"], warn)
