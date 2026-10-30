"""Gia ca phe noi dia theo vung + Robusta London, Arabica New York, ghi vao trang du lieu an
"du-lieu-gia-ca-phe" de trang "Gia ca phe" hien thi.

Nguon chinh: trang cong cu gia ca phe cua Bao Ha Tinh (co gia trong ngay, lich su 30 ngay, bang ky han).
Du phong: ban tin "Gia ca phe hom nay" cua Bao Van Hoa (baovanhoa.vn): tim bai moi nhat qua RSS trang chu,
doc bang gia theo vung (co dong Dak Lak) va bang gia the gioi (co dong Robusta/Arabica).
Giu lich su gia trung binh 4 vung 180 ngay. Khong co so moi hon thi giu nguyen du lieu cu.
"""
import re
import datetime
from html.parser import HTMLParser
import requests
import wp

SLUG = "du-lieu-gia-ca-phe"
RSS = "https://baovanhoa.vn/rss/home.rss"
BHT = "https://baohatinh.vn/cong-cu/gia-ca-phe-hom-nay"
UA = {"User-Agent": wp.UA}
PHIEN = 2  # tang khi doi cach doc bai de doc lai bai hien tai
LINK = re.compile(r"https://baovanhoa\.vn/[\w/-]*gia-ca-phe-hom-nay-(\d{2,8})[\w-]*\.html")


def ngay_tu_so(g):
    """'28102026' -> 28/10/2026, '2872026' -> 28/7/2026, '2910' -> 29/10 nam nay (tu 29/10/2026 bao bo nam khoi
    dia chi). Thu moi cach tach ngay, thang; lay ngay hop le gan nhat, khong qua ngay mai."""
    hom_nay = datetime.date.today()
    if len(g) >= 5:
        cap = [(int(g[-4:]), g[:-4])]
    else:
        cap = [(hom_nay.year, g), (hom_nay.year - 1, g)]
    hop_le = []
    for nam, dm in cap:
        for i in (1, 2):
            d, m = dm[:i], dm[i:]
            if 1 <= len(m) <= 2:
                try:
                    hop_le.append(datetime.date(nam, int(m), int(d)))
                except ValueError:
                    pass
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
            # tu 29/10/2026 bang co them cot gia hom truoc: tim cot "Thay doi" theo dong tieu de
            ci = next((i for i, x in enumerate(b[0]) if "Thay đổi" in x), 2)
            for d in b[1:]:
                if len(d) >= 2 and so(d[1]):
                    vung.append([d[0], so(d[1]), so(d[ci]) if len(d) > ci else None])
        elif ("Robusta" in chu or "Arabica" in chu) and not tg:
            for d in b[1:]:
                if len(d) >= 3 and ("Robusta" in d[0] or "Arabica" in d[0]):
                    tg.append(d[:4])
    return vung, tg, ngay_gia


def vn(x, nd=0):
    return ("{:,.%df}" % nd).format(x).replace(",", "#").replace(".", ",").replace("#", ".")


def doi(t):
    """'▼ 1.000' -> -1000, '▲ 200' -> 200, '—' -> 0."""
    m = re.search(r"\d[\d.]*", t)
    v = int(m.group(0).replace(".", "")) if m else 0
    return -v if "▼" in t else v


def hop_dong(b, ten, dv, nd):
    """Bang ky han -> 2 ky han gan nhat chua dao han: [san, 'Thang 11.2026', gia, thay doi] nhu bang Bao Van Hoa."""
    t = datetime.date.today()
    out = []
    for d in b[1:]:
        m = re.match(r"(\d{2})/(\d{2})$", d[1]) if len(d) >= 5 else None
        if not m or (2000 + int(m.group(2)), int(m.group(1))) < (t.year, t.month):
            continue
        gia = float(d[2].replace(",", ""))
        tang = float(re.sub(r"[^\d.]", "", d[3]) or 0)
        pt = float(re.sub(r"[^\d.]", "", d[4]) or 0)
        dau = "−" if "▼" in d[3] else ("+" if tang else "")
        out.append([ten, "Tháng %s.20%s" % (m.group(1), m.group(2)), "%s %s" % (vn(gia, nd), dv),
                    "%s%s %s; %s%s%%" % (dau, vn(tang, nd), dv.split("/")[0], dau, vn(pt, 2))])
        if len(out) == 2:
            break
    return out


def doc_bht():
    """Trang Bao Ha Tinh -> (vung, tg, ls moi nhat truoc): vung [[ten, gia, thay doi]], ls [[ngay, trung binh, cao nhat]]."""
    r = requests.get(BHT, headers=UA, timeout=60)
    r.raise_for_status()
    p = Bang()
    p.feed(r.text)
    vung, tg, ls = [], [], []
    for b in p.bang:
        dau = b[0][0] if b and b[0] else ""
        if dau == "Vùng":
            for d in b[1:]:
                if len(d) >= 4 and "Trung bình" not in d[0] and so(d[2]):
                    vung.append([d[0], so(d[2]), doi(d[3])])
        elif dau == "Ngày":
            for d in b[1:]:
                m = re.match(r"(\d{2})/(\d{2})/(\d{4})$", d[0])
                gia = [so(x) for x in d[2:6]]
                if m and len(gia) == 4 and all(gia):
                    ls.append(["%s-%s-%s" % (m.group(3), m.group(2), m.group(1)), round(sum(gia) / 4), max(gia)])
        elif dau == "Hợp đồng" and len(b) > 1 and len(b[1]) > 1:
            if b[1][0].startswith("RM"):
                tg += hop_dong(b, "Robusta London", "USD/tấn", 0)
            elif b[1][0].startswith("KC"):
                tg += hop_dong(b, "Arabica New York", "cent/lb", 2)
    return vung, tg, sorted(ls, reverse=True)


def ghi_bht(pid, obj):
    """Tra ve thong bao neu dung duoc nguon Bao Ha Tinh, None neu nguon nay khong dung duoc (chuyen sang du phong)."""
    try:
        vung, tg, ls = doc_bht()
    except Exception as e:  # noqa  loi nguon chinh thi chuyen du phong
        print("Bao Ha Tinh loi:", str(e)[:120])
        return None
    hom_nay = datetime.date.today()
    if len(vung) < 3 or not ls or ls[0][0] < (hom_nay - datetime.timedelta(days=3)).isoformat():
        print("Bao Ha Tinh thieu so:", len(vung), ls[:1])
        return None
    if not all(70000 <= v[1] <= 200000 for v in vung):
        raise RuntimeError("Gia Bao Ha Tinh bat thuong: %s" % vung)
    ngay = ls[0][0]
    if obj.get("bai", "") > ngay:
        return None
    tg = tg or obj.get("tg", [])
    if obj.get("url") == BHT and obj.get("bai") == ngay and obj.get("vung") == vung and obj.get("tg") == tg:
        return "Gia ca phe khong doi (%s)" % ngay
    gop = {x[0]: x for x in obj.get("ls", [])}
    gop.update({x[0]: x for x in ls})
    obj.update({
        "asof": hom_nay.isoformat(),
        "bai": ngay,
        "ngay_gia": "%s/%s" % (ngay[8:10], ngay[5:7]),
        "url": BHT,
        "nguon": "Báo Hà Tĩnh",
        "phien": PHIEN,
        "vung": vung,
        "tg": tg,
        "tb": round(sum(v[1] for v in vung) / len(vung)),
        "ls": sorted(gop.values())[-180:],
    })
    wp.save(pid, obj)
    return "Gia ca phe %s (Bao Ha Tinh): %d vung, TB %s d/kg, %d dong the gioi" % (ngay, len(vung), format(obj["tb"], ","), len(tg))


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

    msg = ghi_bht(pid, obj)
    if msg:
        return msg

    url, ngay_bai = bai_moi_nhat()
    if not url:
        return "RSS khong co bai gia ca phe, giu du lieu %s" % obj.get("bai", "-")
    if obj.get("url") == url and obj.get("phien") == PHIEN:
        return "Chua co bai moi (%s)" % ngay_bai.isoformat()
    if obj.get("bai", "") >= ngay_bai.isoformat():  # du lieu dang co moi hon bai nay
        return "Bai %s khong moi hon du lieu %s" % (ngay_bai.isoformat(), obj.get("bai"))
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
        "phien": PHIEN,
        "vung": vung,
        "tg": tg,
        "tb": tb,
        "ls": ls,
    })
    wp.save(pid, obj)
    return "Gia ca phe %s: %d vung, TB %s d/kg, %d dong the gioi" % (ngay_bai.isoformat(), len(vung), format(tb, ","), len(tg))
