"""Anh dai dien cho Ban tin hang ngay (chuyen muc ban-tin), ve tren may chu GitHub roi gan vao bai.
Bai nhap/da dang trong chuyen muc ban-tin co the chua thong so anh dang chu thich HTML:
  <!-- bt-anh {"nhom":"Bản tin nông sản","ngay":"23/11/2026","tieu_de":"...","o":[["Ngô 12/26","434,50",-1.03],...],"ghi_chu":"..."} -->
Job tim cac bai chua co anh rieng (featured_media = 0 hoac anh chuyen muc mac dinh), ve anh 1200x630 (font DejaVu),
tai len thu vien voi ten ban-tin-<slug bai>, gan lam anh dai dien. Bai da co anh rieng thi bo qua.
"""
import io
import re
import json
import glob
import requests
import wp
from PIL import Image, ImageDraw, ImageFont

OG = "https://giaodichhanghoa247.vn/wp-content/uploads/2026/10/gdhh247-og-mac-dinh.jpg"
DO, XANH, DEN, XAM = (192, 0, 0), (10, 122, 61), (24, 24, 24), (110, 110, 110)
W, H = 1200, 630
ANH_MAC_DINH = {0, 1449, 1593, 1594, 1595, 1596, 1597}
SPEC = re.compile(r"<!--\s*bt-anh\s+(\{.*?\})\s*-->", re.S)


def font(bold, size):
    pat = "*DejaVuSans-Bold.ttf" if bold else "*DejaVuSans.ttf"
    f = glob.glob("/usr/share/fonts/**/" + pat, recursive=True)
    if not f:
        raise RuntimeError("Khong tim thay font DejaVu")
    return ImageFont.truetype(f[0], size)


def wrap(d, text, ft, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=ft) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def so(v):
    return ("%+.2f" % v).replace(".", ",").replace("-", "−") + "%"


def ve(logo, cfg):
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 14, H), fill=DO)
    d.rectangle((0, H - 70, W, H), fill=DO)
    im.paste(logo, (60, 34))
    fn = font(True, 24)
    nhan = cfg["nhom"].upper() + "  ·  " + cfg["ngay"]
    tw = d.textlength(nhan, font=fn)
    d.rounded_rectangle((W - 60 - tw - 32, 52, W - 60, 100), radius=24, fill=(253, 236, 236))
    d.text((W - 60 - tw - 16, 62), nhan, font=fn, fill=DO)
    for size in (50, 46, 42, 38, 34):
        ft = font(True, size)
        lines = wrap(d, cfg["tieu_de"], ft, W - 120)
        if len(lines) <= 3:
            break
    y = 152
    for ln in lines[:3]:
        d.text((60, y), ln, font=ft, fill=DEN)
        y += int(size * 1.28)
    o = cfg.get("o", [])[:5]
    if o:
        n, gap = len(o), 14
        ow = (W - 120 - gap * (n - 1)) / n
        top, bot = 398, 524
        fl, fp, fc = font(False, 20), font(True, 30), font(True, 22)
        for i, (ten, gia, pct) in enumerate(o):
            x0 = 60 + i * (ow + gap)
            pct = float(pct)
            mau = XANH if pct > 0 else (DO if pct < 0 else XAM)
            nen = (234, 246, 238) if pct > 0 else ((253, 236, 236) if pct < 0 else (244, 244, 244))
            d.rounded_rectangle((x0, top, x0 + ow, bot), radius=14, fill=nen)
            d.text((x0 + 16, top + 14), ten, font=fl, fill=XAM)
            d.text((x0 + 16, top + 44), gia, font=fp, fill=DEN)
            d.text((x0 + 16, top + 88), ("▲ " if pct > 0 else ("▼ " if pct < 0 else "")) + so(pct), font=fc, fill=mau)
    if cfg.get("ghi_chu"):
        d.text((60, 532), cfg["ghi_chu"], font=font(False, 16), fill=XAM)
    fd = font(True, 28)
    t = "giaodichhanghoa247.vn"
    d.text(((W - d.textlength(t, font=fd)) / 2, H - 52), t, font=fd, fill="white")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=86, optimize=True, progressive=True)
    return buf.getvalue()


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    base = wp._cfg()[0] + "/index.php/wp-json/wp/v2"
    s = wp._sess()
    r = s.get(base + "/categories", params={"slug": "ban-tin", "_fields": "id"}, timeout=60)
    r.raise_for_status()
    if not r.json():
        return "chua co chuyen muc ban-tin"
    cat = r.json()[0]["id"]
    r = s.get(base + "/posts", params={"categories": cat, "status": "draft,pending,future,publish", "per_page": 20,
                                       "context": "edit", "_fields": "id,slug,featured_media,content,title"}, timeout=60)
    r.raise_for_status()
    logo = None
    out = []
    for p in r.json():
        if p.get("featured_media") not in ANH_MAC_DINH:
            continue
        m = SPEC.search(p["content"]["raw"])
        if not m:
            out.append("%d khong co bt-anh" % p["id"])
            continue
        cfg = json.loads(m.group(1))
        if logo is None:
            og = Image.open(io.BytesIO(requests.get(OG, headers={"User-Agent": wp.UA}, timeout=60).content)).convert("RGB")
            logo = og.crop((78, 68, 584, 222))
            logo = logo.resize((int(logo.width * 0.62), int(logo.height * 0.62)), Image.LANCZOS)
        ten = "ban-tin-" + (p.get("slug") or str(p["id"]))[:80]
        mr = s.post(base + "/media", data=ve(logo, cfg), timeout=120,
                    headers={"Content-Type": "image/jpeg", "Content-Disposition": 'attachment; filename="%s.jpg"' % ten})
        if mr.status_code >= 400:
            raise RuntimeError("Tai anh bai %d loi %d: %s" % (p["id"], mr.status_code, mr.text[:200]))
        mid = mr.json()["id"]
        s.post("%s/media/%d" % (base, mid), json={"alt_text": cfg["tieu_de"][:200], "title": cfg["tieu_de"][:200]}, timeout=60)
        u = s.post("%s/posts/%d" % (base, p["id"]), json={"featured_media": mid}, timeout=60)
        if u.status_code >= 400:
            raise RuntimeError("Gan anh bai %d loi %d" % (p["id"], u.status_code))
        out.append("%d -> anh %d" % (p["id"], mid))
    return "; ".join(out) if out else "khong co bai can anh"
