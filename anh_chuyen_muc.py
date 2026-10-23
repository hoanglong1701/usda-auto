"""Anh dai dien mac dinh theo chuyen muc (1200x630, cung phong cach anh OG mac dinh cua web).
Ve anh ngay tren may chu (logo cat tu anh OG mac dinh, font DejaVu), tai len thu vien WordPress neu chua co.
mu-plugin GDHH247 (1.5.0+) tim anh theo ten (slug) gdhh247-chuyen-muc-* de gan cho bai chua co anh.
"""
import io
import glob
import requests
import wp
from PIL import Image, ImageDraw, ImageFont

OG = "https://giaodichhanghoa247.vn/wp-content/uploads/2026/10/gdhh247-og-mac-dinh.jpg"
RED = (192, 0, 0)
CM = [
    ("kim-loai", "Tin nhanh thị trường kim loại", "Vàng  ·  Bạc  ·  Đồng  ·  Bạch kim  ·  Nhôm"),
    ("nong-san", "Tin nhanh thị trường nông sản", "Đậu tương  ·  Ngô  ·  Lúa mì  ·  Cà phê  ·  Đường"),
    ("nang-luong", "Tin nhanh thị trường năng lượng", "Dầu WTI  ·  Dầu Brent  ·  Khí tự nhiên  ·  Tồn kho EIA"),
    ("vi-mo", "Tin vĩ mô tác động hàng hóa", "Fed  ·  Lãi suất  ·  Đồng USD  ·  Lạm phát  ·  Trung Quốc"),
    ("khuyen-nghi", "Khuyến nghị giao dịch hàng hóa", "Vùng vào lệnh  ·  Chốt lời  ·  Cắt lỗ  ·  Phân tích kỹ thuật"),
]


def font(bold, size):
    pat = "*DejaVuSans-Bold.ttf" if bold else "*DejaVuSans.ttf"
    f = glob.glob("/usr/share/fonts/**/" + pat, recursive=True)
    if not f:
        raise RuntimeError("Khong tim thay font DejaVu")
    return ImageFont.truetype(f[0], size)


def ve(logo, h1, sub):
    im = Image.new("RGB", (1200, 630), "white")
    im.paste(logo, (70, 60))
    d = ImageDraw.Draw(im)
    b, r, f = font(True, 54), font(False, 28), font(True, 30)
    d.rectangle((0, 0, 14, 630), fill=RED)
    d.text((80, 272), h1, font=b, fill=(17, 17, 17))
    d.rectangle((80, 360, 200, 366), fill=RED)
    d.text((80, 395), sub, font=r, fill=(90, 90, 90))
    d.rectangle((0, 535, 1200, 630), fill=RED)
    w = d.textlength("giaodichhanghoa247.vn", font=f)
    d.text(((1200 - w) / 2, 562), "giaodichhanghoa247.vn", font=f, fill="white")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85, optimize=True, progressive=True)
    return buf.getvalue()


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    base = wp._cfg()[0] + "/index.php/wp-json/wp/v2/media"
    s = wp._sess()
    og = Image.open(io.BytesIO(requests.get(OG, headers={"User-Agent": wp.UA}, timeout=60).content)).convert("RGB")
    logo = og.crop((70, 60, 600, 215))
    out = []
    for key, h1, sub in CM:
        slug = "gdhh247-chuyen-muc-" + key
        r = s.get(base, params={"slug": slug, "_fields": "id"}, timeout=60)
        r.raise_for_status()
        if r.json():
            out.append("%s da co (%d)" % (slug, r.json()[0]["id"]))
            continue
        r = s.post(base, data=ve(logo, h1, sub), timeout=120,
                   headers={"Content-Type": "image/jpeg", "Content-Disposition": 'attachment; filename="%s.jpg"' % slug})
        if r.status_code >= 400:
            raise RuntimeError("Tai %s loi %d: %s" % (slug, r.status_code, r.text[:200]))
        mid = r.json()["id"]
        s.post("%s/%d" % (base, mid), json={"alt_text": h1 + " – GDHH247", "title": h1}, timeout=60)
        out.append("%s -> %d" % (slug, mid))
    return "; ".join(out)
