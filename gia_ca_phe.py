"""Gia ca phe noi dia theo vung + Robusta London, Arabica New York, lay tu ban tin
"Gia ca phe hom nay" hang ngay cua Bao Van Hoa (baovanhoa.vn), ghi vao trang du lieu an
"du-lieu-gia-ca-phe" de trang "Gia ca phe" hien thi.

Tim bai moi nhat qua RSS trang chu, doc 2 bang trong bai: bang gia theo vung (co dong Dak Lak)
va bang gia the gioi (co dong Robusta/Arabica). Giu lich su gia trung binh 4 vung 180 ngay.
Khong co bai moi hon thi giu nguyen du lieu cu.
"""
import re
import datetime
from html.parser import HTMLParser
import requests
import wp

SLUG = "du-lieu-gia-ca-phe"
RSS = "https://baovanhoa.vn/rss/home.rss"
UA = {"User-Agent": wp.UA}
LINK = re.compile(r"https://baovanhoa\.vn/[\w/-]*gia-ca-phe-hom-nay-(\d{5,8})[\w-]*\.html")


def ngay_tu_so(g):
    """'28102026' -> 28/10/2026, '2872026' -> 28/7/2026 (thu moi cach tach ngay, thang; lay ngay hop le gan nhat)."""
    if len(g) < 5:
        return None
    nam, dm = int(g[-4:]), g[:-4]
    hop_le = []
    for i in (1, 2):
        d, m = dm[:i], dm[i:]
        if 1 <= len(m) <= 2:
            try:
                hop_le.append(datetime.date(nam, int(m), int(d)))
            except ValueError:
                pass
    hom_nay = datetime.date.today()
    hop_le = [x for x in hop_le if x <= hom_nay + datetime.timedelta(days=1)]
    return max(hop_le) if hop_le else None


class Bang(HTMLParser):
    """Lay moi bang trong trang thanh danh sach dong, moi dong la danh sach chu cua tung o."""

    def __init__(self):
        super().__init__()
        self.bang, self.dong, self.o = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.bang.append([])
        elif tag == "tr" and self.bang:
            self.dong = []
        elif tag in ("td", "th") and self.dong is not None:
            self.o = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.o is not None:
            self.dong.append(" ".join("".join(self.o).split()))
            self.o = None
        elif tag == "tr" and self.dong is not None:
            if self.dong:
                self.bang[-1].append(self.dong)
            self.dong = None

    def handle_data(self, data):
        if self.o is not None:
            self.o.append(data)


def so(t):
    """'88.800' -> 88800; '−700' -> -700; khong doc duoc -> None."""
    t = t.replace("−", "-").replace("–", "-").replace(".", "").replace(" ", "")
    m = re.match(r"^([+-]?\d+)", t)
    return int(m.group(1)) if m else None


def bai_moi_nhat():
    r = requests.get(RSS, headers=UA, timeout=60)
    r.raise_for_status()
    ds = {}
    for m in LINK.finditer(r.text):
        d = ngay_tu_so(m.group(1))
        if d:
            ds[m.group(0)] = d
    if not ds:
        return None, None
    url = max(ds, key=lambda u: ds[u])
    return url, ds[url]


def doc_bai(url):
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    p = Bang()
    p.feed(r.text)
    vung, tg, ngay_gia = [], [], ""
    for b in p.bang:
        chu = " ".join(" ".join(d) for d in b)
        if "Đắk Lắk" in chu and not vung:
            m = re.search(r"Giá ngày (\d{1,2}[./]\d{1,2})", " ".join(b[0]))
            ngay_gia = m.group(1).replace(".", "/") if m else ""
            for d in b[1:]:
                if len(d) >= 2 and so(d[1]):
                    vung.append([d[0], so(d[1]), so(d[2]) if len(d) > 2 else None])
        elif ("Robusta" in chu or "Arabica" in chu) and not tg:
            for d in b[1:]:
                if len(d) >= 3 and ("Robusta" in d[0] or "Arabica" in d[0]):
                    tg.append(d[:4])
    return vung, tg, ngay_gia


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    s = wp._sess()
    base = wp._cfg()[0] + "/index.php/wp-json/wp/v2/pages"
    r = s.get(base, params={"slug": SLUG, "context": "edit", "_fields": "id"}, timeout=60)
    r.raise_for_status()
    if not r.json():
        raise RuntimeError("Chua co trang du lieu %s" % SLUG)
    pid = r.json()[0]["id"]
    obj = wp.load(pid) or {}

    url, ngay_bai = bai_moi_nhat()
    if not url:
        return "RSS khong co bai gia ca phe, giu du lieu %s" % obj.get("bai", "-")
    if obj.get("url") == url:
        return "Chua co bai moi (%s)" % ngay_bai.isoformat()
    vung, tg, ngay_gia = doc_bai(url)
    if len(vung) < 3:
        raise RuntimeError("Bai %s: chi doc duoc %d vung" % (url, len(vung)))

    tb = round(sum(v[1] for v in vung) / len(vung))
    ls = [x for x in obj.get("ls", []) if x[0] != ngay_bai.isoformat()]
    ls.append([ngay_bai.isoformat(), tb, max(v[1] for v in vung)])
    ls = sorted(ls)[-180:]
    obj.update({
        "asof": datetime.date.today().isoformat(),
        "bai": ngay_bai.isoformat(),
        "ngay_gia": ngay_gia,
        "url": url,
        "nguon": "Báo Văn Hóa",
        "vung": vung,
        "tg": tg,
        "tb": tb,
        "ls": ls,
    })
    wp.save(pid, obj)
    return "Gia ca phe %s: %d vung, TB %s d/kg, %d dong the gioi" % (ngay_bai.isoformat(), len(vung), format(tb, ","), len(tg))
