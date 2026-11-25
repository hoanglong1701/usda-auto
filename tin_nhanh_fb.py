"""Tin nhanh Facebook sau giờ Mỹ công bố dữ liệu (CPI, NFP, PCE, GDP, Fed).

Chạy trên GitHub Actions (máy anh Long tắt vẫn chạy). Anh Long cho phép tự đăng tin nhanh từ 25/11/2026.

- Lịch: data/lich_du_lieu_my.csv (bản sao của MKT/bai_viet/lich_du_lieu_my.csv), giờ Việt Nam.
- Số liệu: FRED API (secret FRED_API_KEY) cho CPI/NFP/PCE/GDP; thông cáo Fed (RSS federalreserve.gov) cho lãi suất.
  Chỉ dùng số khi bản quan sát mới nhất có realtime_start = ngày công bố (đã cập nhật đúng đợt), không đoán.
- Giá vàng bạc: Yahoo Finance chart API (GC=F, SI=F).
- Đăng: Meta Graph API POST /{page-id}/feed với secret FB_PAGE_TOKEN.
  Chỉ đăng thật khi biến FB_TU_DANG=1 VÀ có token VÀ qua kiểm tra tuân thủ; nếu không thì lưu nháp
  data/tin_nhanh_nhap/*.md và in ra Job summary.
- Trạng thái: data/tin_nhanh_trang_thai.json (mỗi sự kiện chỉ đăng 1 lần).

Chạy thử (không đăng, bỏ kiểm tra giờ và kiểm tra "đã cập nhật"):
  python tin_nhanh_fb.py --thu 2026-11-25
"""
import csv
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import urllib.error

GOC = os.path.dirname(os.path.abspath(__file__))
LICH = os.path.join(GOC, "data", "lich_du_lieu_my.csv")
TRANG_THAI = os.path.join(GOC, "data", "tin_nhanh_trang_thai.json")
THU_MUC_NHAP = os.path.join(GOC, "data", "tin_nhanh_nhap")
VN = dt.timezone(dt.timedelta(hours=7))
UA = {"User-Agent": "Mozilla/5.0 (gdhh247 tin-nhanh)"}
TEN_PAGE = "Đầu tư hàng hóa 24/7"
GRAPH = "https://graph.facebook.com/v21.0"
CUA_SO_PHUT = 150          # chỉ đăng trong 2,5 giờ sau giờ công bố
GIO_CHOT = 23              # tối: quá 23h thì thôi; bài Fed buổi sáng: quá 10h thì thôi
RAO = chr(96) * 3          # rào khối code markdown cho Job summary

CHU_KY = """------------------------
Hoàng Long - Chuyên viên tư vấn cao cấp về hàng hóa CTCP Saigon Futures
Nhóm đi lệnh (no chat): https://zalo.me/g/kyqzog937
Cộng đồng GDHH247: https://zalo.me/g/ljowni188
Cộng đồng tư vấn vàng bạc vật chất: https://zalo.me/g/f6gdflp8jljt70qwkeon
Trang web về vàng bạc vật chất: https://giaodichhanghoa247.vn/kim-loai-quy/"""
DISCLAIMER = ("Nội dung chỉ nhằm cung cấp thông tin và giải thích thị trường, không phải lời mời mua bán "
              "hay cam kết lợi nhuận. Giao dịch hàng hóa có rủi ro, đặc biệt khi dùng ký quỹ/đòn bẩy.")
TU_CAM = ["vùng giá", "cắt lỗ", "chốt lời", "điểm vào", "nên mua", "nên bán", "cơ hội mua", "cơ hội bán",
          "chắc chắn tăng", "chắc chắn giảm", "cam kết lãi", "mình ", "tôi "]


# ---------------- tiện ích ----------------
def lay(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def so(x, nd=1):
    """Định dạng số kiểu Việt Nam: 3.660,1"""
    s = f"{x:,.{nd}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def dau(x, nd=1):
    return ("+" if x > 0 else "") + so(x, nd)


def ghi(msg):
    print(msg, flush=True)


# ---------------- FRED ----------------
def fred(series, n=16):
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise RuntimeError("Thiếu FRED_API_KEY")
    url = ("https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s&file_type=json"
           "&sort_order=desc&limit=%d" % (series, key, n))
    d = json.loads(lay(url))
    out = []
    for o in d.get("observations", []):
        v = None if o["value"] in (".", "") else float(o["value"])
        out.append({"ngay": o["date"], "gt": v, "rt": o.get("realtime_start")})
    return out  # mới nhất trước


def thang_truoc(ngay, k=1):
    y, m = int(ngay[:4]), int(ngay[5:7])
    m -= k
    while m <= 0:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}-01"


def tra(obs, ngay):
    for o in obs:
        if o["ngay"] == ngay:
            return o["gt"]
    return None


def kiem_moi(obs, ngay_cong_bo_my, thu):
    """Bản mới nhất phải được FRED cập nhật đúng ngày công bố (giờ Mỹ)."""
    if thu:
        return True
    return bool(obs) and obs[0]["rt"] == ngay_cong_bo_my


def pct(a, b):
    if a is None or b is None or b == 0:
        return None
    return (a / b - 1) * 100


# ---------------- giá vàng bạc ----------------
def gia_yahoo(ma):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%s?interval=1d&range=5d" % urllib.parse.quote(ma)
    d = json.loads(lay(url))["chart"]["result"][0]["meta"]
    p, pc = d.get("regularMarketPrice"), d.get("chartPreviousClose") or d.get("previousClose")
    return p, pct(p, pc)


def dong_gia():
    try:
        g, gp = gia_yahoo("GC=F")
        s, sp = gia_yahoo("SI=F")
        luc = dt.datetime.now(VN).strftime("%H:%M")
        return (f"• Vàng COMEX quanh {so(g, 1)} USD/oz ({dau(gp, 1)}% trong ngày), "
                f"bạc quanh {so(s, 2)} USD/oz ({dau(sp, 1)}%) lúc {luc}."), luc
    except Exception as e:  # noqa
        ghi("Không lấy được giá vàng bạc: %s" % e)
        return None, None


# ---------------- từng loại sự kiện ----------------
def y_nghia_lam_phat(cao_hon):
    if cao_hon is None:
        return None
    if cao_hon > 0:
        return ("Lạm phát tăng nhanh hơn kỳ trước, củng cố khả năng Fed giữ lãi suất cao lâu hơn, "
                "thường bất lợi cho vàng bạc.")
    if cao_hon < 0:
        return ("Lạm phát hạ nhiệt so với kỳ trước, có thể làm giảm áp lực tăng lãi suất của Fed, "
                "thường hỗ trợ vàng bạc.")
    return "Lạm phát đi ngang so với kỳ trước, chưa làm thay đổi nhiều kỳ vọng về lãi suất Fed."


def so_sanh_chu(a, b):
    if a is None or b is None:
        return None
    a, b = round(a, 1), round(b, 1)
    return 1 if a > b else (-1 if a < b else 0)


def chu_ss(c):
    return {1: "cao hơn", -1: "thấp hơn", 0: "bằng"}.get(c, "")


def ky_tu_su_kien(su_kien, ngay_vn):
    m = re.search(r"tháng (\d{1,2})", su_kien)
    if not m:
        return None
    th = int(m.group(1))
    y = ngay_vn.year if th <= ngay_vn.month else ngay_vn.year - 1
    return f"{y:04d}-{th:02d}-01"


def bai_cpi(ky, ngay_my, thu):
    a, c = fred("CPIAUCSL"), fred("CPILFESL")
    if not (kiem_moi(a, ngay_my, thu) and kiem_moi(c, ngay_my, thu)):
        return None, "FRED chưa cập nhật CPI"
    ky = ky or a[0]["ngay"]
    k1, k2, k12, k13 = thang_truoc(ky), thang_truoc(ky, 2), thang_truoc(ky, 12), thang_truoc(ky, 13)
    mm, mm_t = pct(tra(a, ky), tra(a, k1)), pct(tra(a, k1), tra(a, k2))
    cm, cm_t = pct(tra(c, ky), tra(c, k1)), pct(tra(c, k1), tra(c, k2))
    a12, c12 = fred("CPIAUCSL", 30), fred("CPILFESL", 30)
    yy, cy = pct(tra(a12, ky), tra(a12, k12)), pct(tra(c12, ky), tra(c12, k12))
    if mm is None or cm is None:
        return None, "Thiếu số CPI kỳ %s" % ky
    th = int(ky[5:7])
    ss = so_sanh_chu(cm, cm_t)
    tieu = f"⚡ Tin nhanh: CPI Mỹ tháng {th} tăng {so(mm)}%, CPI lõi {so(cm)}%"
    dong = [f"• CPI tháng {th} tăng {so(mm)}% so với tháng trước (tháng trước {so(mm_t)}%)"
            + (f", tăng {so(yy)}% so với cùng kỳ." if yy is not None else "."),
            f"• CPI lõi (bỏ thực phẩm, năng lượng) tăng {so(cm)}%, {chu_ss(ss)} mức {so(cm_t)}% của tháng trước"
            + (f"; so với cùng kỳ tăng {so(cy)}%." if cy is not None else ".")]
    return {"tieu": tieu, "dong": dong, "y": y_nghia_lam_phat(ss), "nguon": "BLS (số liệu qua FRED)"}, None


def bai_pce(ky, ngay_my, thu):
    a, c = fred("PCEPI", 30), fred("PCEPILFE", 30)
    if not (kiem_moi(a, ngay_my, thu) and kiem_moi(c, ngay_my, thu)):
        return None, "FRED chưa cập nhật PCE"
    ky = ky or c[0]["ngay"]
    k1, k12, k13 = thang_truoc(ky), thang_truoc(ky, 12), thang_truoc(ky, 13)
    cy, cy_t = pct(tra(c, ky), tra(c, k12)), pct(tra(c, k1), tra(c, k13))
    ay = pct(tra(a, ky), tra(a, k12))
    cm = pct(tra(c, ky), tra(c, k1))
    if cy is None or cm is None:
        return None, "Thiếu số PCE kỳ %s" % ky
    th = int(ky[5:7])
    ss = so_sanh_chu(cy, cy_t)
    tieu = f"⚡ Tin nhanh: PCE lõi tháng {th} tăng {so(cy)}% so với cùng kỳ, {chu_ss(ss)} tháng trước"
    dong = [f"• PCE lõi (thước đo lạm phát Fed theo dõi sát nhất) tăng {so(cy)}% so với cùng kỳ, "
            f"tháng trước {so(cy_t)}%; tăng {so(cm)}% so với tháng trước."]
    if ay is not None:
        dong.append(f"• PCE chung tăng {so(ay)}% so với cùng kỳ.")
    return {"tieu": tieu, "dong": dong, "y": y_nghia_lam_phat(ss), "nguon": "BEA (số liệu qua FRED)"}, None


def bai_gdp(ngay_my, thu):
    g = fred("A191RL1Q225SBEA", 4)
    if not kiem_moi(g, ngay_my, thu):
        return None, "FRED chưa cập nhật GDP"
    q = (int(g[0]["ngay"][5:7]) - 1) // 3 + 1
    return {"dong": [f"• GDP quý {q} tăng {so(g[0]['gt'])}% (năm hóa), quý trước {so(g[1]['gt'])}%."],
            "nguon": "BEA (số liệu qua FRED)"}, None


def bai_nfp(ky, ngay_my, thu):
    p, u = fred("PAYEMS"), fred("UNRATE")
    if not (kiem_moi(p, ngay_my, thu) and kiem_moi(u, ngay_my, thu)):
        return None, "FRED chưa cập nhật báo cáo việc làm"
    ky = ky or p[0]["ngay"]
    k1, k2 = thang_truoc(ky), thang_truoc(ky, 2)
    if None in (tra(p, ky), tra(p, k1), tra(p, k2), tra(u, ky)):
        return None, "Thiếu số việc làm kỳ %s" % ky
    d, d_t = tra(p, ky) - tra(p, k1), tra(p, k1) - tra(p, k2)
    ur, ur_t = tra(u, ky), tra(u, k1)
    th = int(ky[5:7])
    manh = (d > d_t) and (ur_t is None or ur <= ur_t)
    yeu = (d < d_t) and (ur_t is None or ur >= ur_t)
    tieu = f"⚡ Tin nhanh: Mỹ {'thêm' if d >= 0 else 'mất'} {so(abs(d), 0)} nghìn việc làm tháng {th}"
    dong = [f"• Việc làm phi nông nghiệp {dau(d, 0)} nghìn, tháng trước {dau(d_t, 0)} nghìn.",
            f"• Tỷ lệ thất nghiệp {so(ur)}%" + (f", tháng trước {so(ur_t)}%." if ur_t is not None else ".")]
    if manh:
        y = "Thị trường lao động mạnh hơn tháng trước, Fed có thêm lý do giữ lãi suất cao, thường bất lợi cho vàng bạc."
    elif yeu:
        y = "Thị trường lao động yếu đi, có thể làm giảm kỳ vọng Fed tăng lãi suất, thường hỗ trợ vàng bạc."
    else:
        y = "Số liệu việc làm trái chiều, chưa làm thay đổi nhiều kỳ vọng về lãi suất Fed."
    return {"tieu": tieu, "dong": dong, "y": y, "nguon": "BLS (số liệu qua FRED)"}, None


def phan_so(s):
    s = s.strip()
    m = re.match(r"(\d+)(?:-(\d+)/(\d+))?$", s)
    if not m:
        return None
    v = float(m.group(1))
    if m.group(2):
        v += float(m.group(2)) / float(m.group(3))
    return v


def bai_fed(ngay_my, thu):
    rss = lay("https://www.federalreserve.gov/feeds/press_monetary.xml")
    rss = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", rss, flags=re.S)
    items = re.findall(r"<item>(.*?)</item>", rss, re.S)
    for it in items:
        tieu = re.search(r"<title>(.*?)</title>", it, re.S).group(1)
        link = re.search(r"<link>(.*?)</link>", it, re.S).group(1).strip()
        if "FOMC statement" not in tieu:
            continue
        html = lay(link)
        mngay = re.search(r"(\w+ \d{1,2}, \d{4})", html)
        if not thu and mngay:
            d = dt.datetime.strptime(mngay.group(1), "%B %d, %Y").date().isoformat()
            if d != ngay_my:
                return None, "Thông cáo Fed mới nhất chưa phải hôm nay"
        txt = re.sub(r"<[^>]+>", " ", html)
        m = re.search(r"(raise|lower|maintain)\s+the\s+target\s+range\s+for\s+the\s+federal\s+funds\s+rate\s+"
                      r"(?:at|to)\s+([\d\-/]+)\s+to\s+([\d\-/]+)\s+percent", txt)
        if not m:
            return None, "Không đọc được mức lãi suất trong thông cáo Fed"
        lo, hi = phan_so(m.group(2)), phan_so(m.group(3))
        hd = {"raise": "tăng", "lower": "giảm", "maintain": "giữ nguyên"}[m.group(1)]
        muc = f"{so(lo, 2)}–{so(hi, 2)}%"
        tieu_bai = f"⚡ Tin nhanh: Fed {hd} lãi suất" + (f", về {muc}" if hd != "giữ nguyên" else f" ở {muc}")
        if hd == "tăng":
            y = "Lãi suất cao hơn làm việc giữ vàng bạc kém hấp dẫn và thường hỗ trợ USD, thường bất lợi cho vàng bạc."
        elif hd == "giảm":
            y = "Lãi suất thấp hơn làm giảm chi phí cơ hội khi giữ vàng bạc, thường hỗ trợ giá."
        else:
            y = "Fed giữ nguyên lãi suất; thị trường sẽ chú ý tín hiệu về các cuộc họp tới trong thông cáo và họp báo."
        return {"tieu": tieu_bai, "dong": [f"• Biên độ lãi suất mục tiêu {'mới' if hd != 'giữ nguyên' else 'hiện tại'}: {muc}."], "y": y,
                "nguon": "Cục Dự trữ Liên bang Mỹ (thông cáo FOMC)"}, None
    return None, "Không thấy thông cáo FOMC trong RSS"


# ---------------- ráp bài, kiểm tra, đăng ----------------
def rap_bai(phan, gia, luc, ngay_vn):
    dong = list(phan["dong"])
    if gia:
        dong.append(gia)
    body = phan["tieu"] + "\n\n" + "\n".join(dong)
    if phan.get("y"):
        body += "\n\n👉 Ý nghĩa: " + phan["y"]
    nguon = f"Nguồn: {phan['nguon']}, công bố ngày {ngay_vn.strftime('%d/%m/%Y')} (giờ Việt Nam)"
    if gia:
        nguon += f"; giá vàng bạc COMEX (Yahoo Finance) lúc {luc}"
    body += "\n\n" + CHU_KY + "\n\n" + nguon + ". " + DISCLAIMER + "\n\n#GDHH247 #tinnhanh #giavang #giabac"
    return body


def kiem_tra(bai):
    loi = []
    thap = bai.lower()
    for t in TU_CAM:
        if t in thap:
            loi.append("có từ cấm: " + t.strip())
    if "[" in bai or re.search(r"\b(nan|none|null)\b", thap):
        loi.append("còn chỗ trống hoặc số lỗi")
    if DISCLAIMER not in bai:
        loi.append("thiếu disclaimer")
    if "Nguồn:" not in bai:
        loi.append("thiếu nguồn")
    for dong in bai.split("\n"):
        if len(dong) > 12 and dong.upper() == dong and any(ch.isalpha() for ch in dong) and "http" not in dong:
            loi.append("dòng IN HOA: " + dong[:30])
    return loi


def lay_token():
    """Lấy token từ secret, bỏ ngoặc kép, dấu cách, xuống dòng, chữ thừa phía trước (vd "access_token": )."""
    tho = os.environ.get("FB_PAGE_TOKEN") or ""
    m = re.search(r"EAA[A-Za-z0-9]+", tho)
    return (m.group(0) if m else tho.strip().strip('"').strip("'")), tho


def chan_doan_token(tho):
    """Mô tả chuỗi trong secret mà không lộ token."""
    return ("dài %d ký tự; bắt đầu bằng EAA: %s; có ngoặc kép: %s; có dấu cách/xuống dòng: %s"
            % (len(tho), "có" if tho.strip().strip('"').startswith("EAA") else "không",
               "có" if '"' in tho or "'" in tho else "không",
               "có" if re.search(r"\s", tho) else "không"))


def kiem_token():
    """Chỉ đọc: token có quản lý đúng Page không. Không đăng gì."""
    tok, tho = lay_token()
    if not tho:
        return "chưa có FB_PAGE_TOKEN"
    ghi("Chẩn đoán secret: " + chan_doan_token(tho))
    try:
        me = json.loads(lay(GRAPH + "/me?fields=id,name&access_token=" + urllib.parse.quote(tok)))
        if TEN_PAGE in me.get("name", ""):
            return "OK, token của Page %s" % me["name"]
        acc = json.loads(lay(GRAPH + "/me/accounts?fields=name&limit=100&access_token=" + urllib.parse.quote(tok)))
        ten = [p.get("name", "") for p in acc.get("data", [])]
        if any(TEN_PAGE in t for t in ten):
            return "OK, token người dùng %s quản lý Page %s" % (me.get("name"), TEN_PAGE)
        return "LỖI: token không quản lý Page %s (thấy: %s)" % (TEN_PAGE, ", ".join(ten) or me.get("name"))
    except urllib.error.HTTPError as e:
        return "LỖI token: HTTP %s %s (secret %s)" % (e.code, e.read()[:200].decode("utf-8", "ignore"),
                                                        chan_doan_token(tho))
    except Exception as e:  # noqa
        return "LỖI token: %s" % e


def dang_fb(bai):
    tok, _ = lay_token()
    me = json.loads(lay(GRAPH + "/me?fields=id,name&access_token=" + urllib.parse.quote(tok)))
    if TEN_PAGE not in me.get("name", ""):
        # Token của người dùng hệ thống: đổi sang token của Page qua /me/accounts
        acc = json.loads(lay(GRAPH + "/me/accounts?fields=id,name,access_token&limit=100&access_token="
                             + urllib.parse.quote(tok)))
        trang = [p for p in acc.get("data", []) if TEN_PAGE in p.get("name", "")]
        if not trang:
            raise RuntimeError("Token không quản lý Page %s (token của: %s)" % (TEN_PAGE, me.get("name")))
        me, tok = {"id": trang[0]["id"], "name": trang[0]["name"]}, trang[0]["access_token"]
    data = urllib.parse.urlencode({"message": bai, "access_token": tok}).encode()
    req = urllib.request.Request(GRAPH + "/%s/feed" % me["id"], data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read().decode())
    pid = res.get("id", "")
    return pid, "https://www.facebook.com/" + pid.replace("_", "/posts/") if pid else ""


def tom_tat_job(txt):
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as f:
            f.write(txt + "\n")


def doc_lich():
    with open(LICH, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def chon_su_kien(lich, bay_gio, thu_ngay):
    for r in lich:
        if r.get("muc_do") != "cao":
            continue
        if thu_ngay:
            if r["ngay_vn"] == thu_ngay:
                return r
            continue
        if r["ngay_vn"] != bay_gio.strftime("%Y-%m-%d"):
            continue
        h, m = map(int, r["gio_vn"].split(":"))
        bd = bay_gio.replace(hour=h, minute=m, second=0, microsecond=0)
        het = min(bd + dt.timedelta(minutes=CUA_SO_PHUT),
                  bay_gio.replace(hour=GIO_CHOT if h >= 12 else 10, minute=0, second=0, microsecond=0))
        if bd <= bay_gio <= het:
            return r
    return None


def main():
    thu_ngay = None
    if "--thu" in sys.argv:
        thu_ngay = sys.argv[sys.argv.index("--thu") + 1]
    thu_ngay = thu_ngay or os.environ.get("TIN_NHANH_THU") or None
    bay_gio = dt.datetime.now(VN)
    if thu_ngay:
        kt = kiem_token()
        ghi("Kiểm tra token: " + kt)
        tom_tat_job("**Kiểm tra token Facebook (chỉ đọc, không đăng):** " + kt + "\n")
    ev = chon_su_kien(doc_lich(), bay_gio, thu_ngay)
    if not ev:
        ghi("Không có sự kiện trong khung giờ này, dừng.")
        return 0
    khoa = ev["ngay_vn"] + "_" + ev["gio_vn"].replace(":", "")
    tt = {}
    if os.path.exists(TRANG_THAI):
        with open(TRANG_THAI, encoding="utf-8") as f:
            tt = json.load(f)
    if not thu_ngay and tt.get(khoa, {}).get("trang_thai") == "da_dang":
        ghi("Sự kiện %s đã đăng rồi, dừng." % khoa)
        return 0
    ngay_vn = dt.date.fromisoformat(ev["ngay_vn"])
    # Mỹ công bố 8:30 ET = tối cùng ngày ở VN; Fed 14:00 ET = sáng hôm sau ở VN
    ngay_my = (ngay_vn - dt.timedelta(days=1)).isoformat() if ev["gio_vn"] < "12:00" else ngay_vn.isoformat()
    sk = ev["su_kien"]
    ky = ky_tu_su_kien(sk, ngay_vn)
    thu = bool(thu_ngay)
    phan, ly_do = None, None
    try:
        if "Fed" in sk and "lãi suất" in sk:
            phan, ly_do = bai_fed(ngay_my, thu)
        elif "PCE" in sk:
            phan, ly_do = bai_pce(ky_tu_su_kien(sk.split("PCE", 1)[1], ngay_vn), ngay_my, thu)
            if phan and "GDP" in sk:
                g, _ = bai_gdp(ngay_my, thu)
                if g:
                    phan["dong"] += g["dong"]
        elif "CPI" in sk:
            phan, ly_do = bai_cpi(ky, ngay_my, thu)
        elif "việc làm" in sk or "NFP" in sk:
            phan, ly_do = bai_nfp(ky, ngay_my, thu)
        elif "GDP" in sk:
            g, ly_do = bai_gdp(ngay_my, thu)
            if g:
                phan = {"tieu": "⚡ Tin nhanh: " + g["dong"][0][2:].rstrip("."), "dong": [], "y": None,
                        "nguon": g["nguon"]}
        else:
            ly_do = "Chưa hỗ trợ loại sự kiện: " + sk
    except Exception as e:  # noqa
        ly_do = "Lỗi lấy số liệu: %s" % e
    if not phan:
        ghi("Chưa soạn được (%s). Lần chạy sau sẽ thử lại." % ly_do)
        tom_tat_job("**Tin nhanh %s chưa soạn được:** %s" % (sk, ly_do))
        return 0
    gia, luc = dong_gia()
    bai = rap_bai(phan, gia, luc, ngay_vn)
    loi = kiem_tra(bai)
    tu_dang = os.environ.get("FB_TU_DANG") == "1" and bool(os.environ.get("FB_PAGE_TOKEN")) and not thu
    ket = {"su_kien": sk, "luc": bay_gio.isoformat(timespec="minutes")}
    if tu_dang and not loi:
        pid, link = dang_fb(bai)
        ket.update({"trang_thai": "da_dang", "id": pid, "link": link})
        ghi("ĐÃ ĐĂNG: " + link)
        tom_tat_job("**Đã đăng tin nhanh %s:** %s\n\n%s\n%s\n%s" % (sk, link, RAO, bai, RAO))
    else:
        os.makedirs(THU_MUC_NHAP, exist_ok=True)
        ten = os.path.join(THU_MUC_NHAP, khoa + ".md")
        with open(ten, "w", encoding="utf-8") as f:
            f.write(bai + "\n")
        ly = "; ".join(loi) if loi else ("chạy thử" if thu else "chế độ nháp (chưa bật FB_TU_DANG hoặc chưa có token)")
        ket.update({"trang_thai": "nhap", "ly_do": ly})
        ghi("NHÁP (%s):\n%s" % (ly, bai))
        tom_tat_job("**Tin nhanh %s – nháp (%s):**\n\n%s\n%s\n%s" % (sk, ly, RAO, bai, RAO))
    if not thu:
        tt[khoa] = ket
        with open(TRANG_THAI, "w", encoding="utf-8") as f:
            json.dump(tt, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
