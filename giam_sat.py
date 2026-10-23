"""Giam sat web moi 30 phut (giam-sat.yml): DNS, cac trang chinh, do moi du lieu, sitemap.
Co loi thi thoat ma 1 (job do, GitHub gui email). Ket qua ghi data/health.json, chi ghi lai khi danh sach loi thay doi.
"""
import os
import re
import sys
import json
import html
import datetime
import requests
import wp

BASE = "https://giaodichhanghoa247.vn"
DOMAIN = "giaodichhanghoa247.vn"
H = {"User-Agent": wp.UA}
TRANG = [
    "/", "/index.php/tin-tuc-nhanh/", "/index.php/dashboard-tong-hop/", "/index.php/gia-the-gioi-truc-tuyen/",
    "/index.php/phan-tich-chuyen-sau/", "/index.php/khuyen-nghi/", "/index.php/ket-qua-khuyen-nghi/",
    "/index.php/kim-loai-quy/", "/index.php/kien-thuc-dau-tu/", "/index.php/phan-tich-nong-san/",
    "/index.php/phan-tich-kim-loai/", "/index.php/phan-tich-nguyen-lieu-cong-nghiep/",
    "/index.php/tong-quat-kinh-te-the-gioi/", "/index.php/category/kim-loai/", "/index.php/category/tin-tuc-vi-mo/",
]
# trang du lieu: (id, truong thoi gian, so gio toi da; so am = chi canh bao, khong bao loi).
# "modified" = gio sua trang tren WordPress
DU_LIEU = [
    (176, "modified", 9 * 24),
    (177, "upd", 10 * 24),
    (178, "u", 48),
    # 227 chi canh bao: so lieu dung khi chua nhap lenh moi vao Log khuyen nghi (viec cua anh Long)
    (227, "updated_at", -10 * 24),
    (478, "asof", 9 * 24),
    (801, "asof", 8 * 24),
    (847, "asof", 10 * 24),
    (1519, "asof", 4 * 24),
    (1526, "asof", 4 * 24),
]
PATH = os.path.join("data", "health.json")


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def parse_time(v):
    v = str(v).strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", v)
    if m:
        v = "%s-%s-%s" % (m.group(3), m.group(2), m.group(1))
    if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        # ngay khong co gio: tinh cuoi ngay gio VN
        return datetime.datetime.fromisoformat(v + "T23:59:00+07:00")
    t = datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.timezone.utc)
    return t


def kiem_dns():
    loi = []
    for ten, url, extra in (("Google", "https://dns.google/resolve", {}),
                            ("Cloudflare", "https://cloudflare-dns.com/dns-query", {"accept": "application/dns-json"})):
        try:
            j = requests.get(url, params={"name": DOMAIN, "type": "A"}, headers=extra, timeout=20).json()
            ips = [a["data"] for a in j.get("Answer", []) if a.get("type") == 1]
            if j.get("Status") != 0 or not ips:
                loi.append("DNS %s khong tra dia chi (Status %s)" % (ten, j.get("Status")))
        except Exception as e:  # noqa
            loi.append("DNS %s loi: %s" % (ten, e))
    return loi


def kiem_trang():
    loi, cham = [], []
    for p in TRANG:
        try:
            r = requests.get(BASE + p, headers=H, timeout=45)
            if r.status_code != 200:
                loi.append("Trang %s tra %d" % (p, r.status_code))
            elif "</html>" not in r.text[-2000:]:
                loi.append("Trang %s thieu noi dung (khong ket thuc </html>)" % p)
            elif r.elapsed.total_seconds() > 8:
                cham.append("%s mat %.1f s" % (p, r.elapsed.total_seconds()))
        except Exception as e:  # noqa
            loi.append("Trang %s khong mo duoc: %s" % (p, type(e).__name__))
    return loi, cham


def kiem_du_lieu():
    loi, cb, tuoi = [], [], {}
    for pid, truong, gio in DU_LIEU:
        try:
            j = requests.get(BASE + "/index.php/wp-json/wp/v2/pages/%d" % pid,
                             params={"_fields": "modified_gmt,content"}, headers=H, timeout=45).json()
            m = re.search(r'<pre id="gd-data"[^>]*>(.*?)</pre>', j["content"]["rendered"], re.S)
            if not m:
                loi.append("Trang du lieu %d khong co #gd-data" % pid)
                continue
            raw = html.unescape(m.group(1))
            if truong == "modified":
                t = parse_time(j["modified_gmt"] + "+00:00")
            elif truong == "upd":
                # trang 177 chua HTML: phai bat dau bang <p class="upd">Cap nhat ngay dd/mm/yyyy
                mm = re.search(r'<p class="upd">Cập nhật ngày (\d{2}/\d{2}/\d{4})', raw)
                if not mm or len(raw) < 5000:
                    loi.append("Trang 177 sai cau truc (thieu dong cap nhat hoac qua ngan)")
                    continue
                t = parse_time(mm.group(1))
            else:
                d = json.loads(raw)
                if truong not in d:
                    loi.append("Trang du lieu %d thieu truong %s" % (pid, truong))
                    continue
                t = parse_time(d[truong])
            h = (now() - t).total_seconds() / 3600
            tuoi[str(pid)] = round(h, 1)
            if h > abs(gio):
                (loi if gio > 0 else cb).append("Trang du lieu %d cu %.0f ngay (toi da %d)" % (pid, h / 24, abs(gio) / 24))
        except Exception as e:  # noqa
            loi.append("Trang du lieu %d loi: %s %s" % (pid, type(e).__name__, str(e)[:80]))
    return loi, cb, tuoi


def kiem_sitemap():
    loi = []
    try:
        r = requests.get(BASE + "/sitemap_index.xml", headers=H, timeout=45)
        locs = re.findall(r"<loc>(.*?)</loc>", r.text)
        if r.status_code != 200 or not locs:
            return ["sitemap_index.xml tra %d, %d link" % (r.status_code, len(locs))]
        pg = [u for u in locs if "page-sitemap" in u]
        if pg:
            t = requests.get(pg[0], headers=H, timeout=45).text
            for slug in ("du-lieu-", "/sample-page/"):
                if slug in t:
                    loi.append("page-sitemap con chua trang %s" % slug)
            if "phan-tich-kim-loai" not in t:
                loi.append("page-sitemap thieu trang phan-tich-kim-loai")
    except Exception as e:  # noqa
        loi.append("Sitemap loi: %s" % type(e).__name__)
    return loi


def run():
    loi = kiem_dns()
    if loi:
        # DNS hong thi cac kiem tra sau deu loi, khong can chay
        canh_bao, tuoi = [], {}
    else:
        l2, canh_bao = kiem_trang()
        l3, cb3, tuoi = kiem_du_lieu()
        loi += l2 + l3 + kiem_sitemap()
        canh_bao += cb3
    t = now().replace(microsecond=0).isoformat()
    try:
        old = json.load(open(PATH, encoding="utf-8"))
    except Exception:  # noqa
        old = {}
    new = {"ok": not loi, "loi": loi, "canh_bao": canh_bao, "tu": t, "tuoi_du_lieu_gio": tuoi}
    if old.get("loi") == loi and old.get("canh_bao") == canh_bao:
        new["tu"] = old.get("tu", t)
    # chi ghi khi trang thai doi (tranh commit moi 30 phut); tuoi du lieu cap nhat theo trang thai
    if old.get("loi") != loi or old.get("canh_bao") != canh_bao:
        os.makedirs("data", exist_ok=True)
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(new, f, ensure_ascii=False, indent=1)
    return new


if __name__ == "__main__":
    res = run()
    print(json.dumps(res, ensure_ascii=False, indent=1))
    sys.exit(1 if res["loi"] else 0)
