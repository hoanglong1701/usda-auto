"""Anh dai dien cho Ban tin hang ngay (chuyen muc ban-tin), ve tren may chu GitHub roi gan vao bai.

Bai trong chuyen muc ban-tin chua thong so anh dang chu thich HTML o dau noi dung:
  <!-- bt-anh {"nhom_key":"nong-san","sp":"ngo","nhom":"Nông sản","ngay":"23/11/2026",
              "nhan":"Thị trường nông sản ngày 23/11:","tieu_de":"...","o":[["Ngô",-1.03],["Đậu tương",1.10]]} -->
  - nhom_key: nong-san | nguyen-lieu-cn | kim-loai-quy | kim-loai-cn | nang-luong
  - sp: san pham chinh cua tin de chon anh nen (vd ngo, dau-tuong, lua-mi, kho-dau, dau-dau, ca-phe, duong, bong,
        vang, bac, dong, nhom, kim-loai-khac, dau-tho, khi); khong co thi lay anh chung cua nhom
  - o: toi da 5 o % thay doi [ten, %] (dang cu [ten, gia, %] van doc duoc)
  - pa (tuy chon): ep phuong an 1..4; mac dinh xoay vong theo ngay va nhom (anh Long 23/11/2026: linh dong 1-4)
Anh nen: danh sach anh Pexels da duyet trong data/anh_nen.json (tai tu images.pexels.com khi ve; giay phep Pexels).
Phuong an: 1 nen mo + khung trang; 2 chia doi khoi do sam + anh cat cheo; 3 anh toan khung toi dan, chu trang;
4 kieu tap chi anh tren chu duoi. Anh tai len ten bt2-<slug>; bai da co anh bt2- thi bo qua.
"""
import io
import os
import re
import json
import glob
import random
import datetime
import requests
import wp
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OG = "https://giaodichhanghoa247.vn/wp-content/uploads/2026/10/gdhh247-og-mac-dinh.jpg"
PEXELS = "https://images.pexels.com/photos/{0}/pexels-photo-{0}.jpeg?auto=compress&cs=tinysrgb&w=1600"
DO, DO_SAM, CAM, XANH, NAVY, XAM = (192, 0, 0), (120, 8, 16), (214, 96, 22), (10, 122, 61), (20, 33, 61), (110, 110, 110)
W, H = 1200, 630
SPEC = re.compile(r"<!--\s*bt-anh\s+(\{.*?\})\s*-->", re.S)
ANH_MAC_DINH = {1449, 1593, 1594, 1595, 1596, 1597}
NHOM_THU_TU = ["nong-san", "nguyen-lieu-cn", "kim-loai-quy", "kim-loai-cn", "nang-luong"]
_FONT = {}


def font(bold, size):
    k = (bold, size)
    if k not in _FONT:
        pats = ["/usr/share/fonts/**/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/**/DejaVuSans.ttf",
                r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"]
        path = None
        for p in pats:
            g = glob.glob(p, recursive=True)
            if g:
                path = g[0]
                break
        if not path:
            raise RuntimeError("Khong tim thay font")
        _FONT[k] = ImageFont.truetype(path, size)
    return _FONT[k]


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


def fit(d, text, maxw, maxl, sizes):
    for s in sizes:
        ft = font(True, s)
        ls = wrap(d, text, ft, maxw)
        if len(ls) <= maxl:
            return ft, s, ls
    return ft, s, ls[:maxl]


def cover(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    l, t = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((l, t, l + w, t + h))


def pct_txt(p):
    return ("%+.1f" % p).replace(".", ",").replace("-", "\u2212") + "%"


def norm_o(o):
    out = []
    for it in (o or [])[:5]:
        if len(it) >= 3:
            out.append((it[0], float(it[2])))
        elif len(it) == 2:
            out.append((it[0], float(it[1])))
    return out


def chips(d, o, x, y, maxw, center=False, dark=False):
    if not o:
        return
    for cs in (21, 19, 17, 15, 13):
        fc = font(True, cs)
        items = []
        for ten, p in o:
            t = "%s %s %s" % (ten, "\u25b2" if p > 0 else ("\u25bc" if p < 0 else "\u2022"), pct_txt(p))
            items.append((t, p, d.textlength(t, font=fc) + 24))
        tot = sum(i[2] for i in items) + 10 * (len(items) - 1)
        if tot <= maxw:
            break
    if center:
        x = x + (maxw - tot) / 2
    for t, p, cw in items:
        fg = XANH if p > 0 else (DO if p < 0 else XAM)
        if dark:
            bg = (255, 255, 255, 235)
        else:
            bg = (234, 246, 238) if p > 0 else ((253, 236, 236) if p < 0 else (240, 240, 240))
        d.rounded_rectangle((x, y, x + cw, y + 36), radius=18, fill=bg)
        d.text((x + 12, y + 6), t, font=fc, fill=fg)
        x += cw + 10


def dan_logo(img, d, lg, x, y, alpha=245):
    d.rounded_rectangle((x - 12, y - 8, x + lg.width + 12, y + lg.height + 8), radius=12, fill=(255, 255, 255, alpha))
    img.paste(lg, (x, y))


def pa1(c, nen, lg):
    img = cover(nen, W, H).filter(ImageFilter.GaussianBlur(7))
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(max(0, (y - H * 0.35)) / (H * 0.65) * 110))
    img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, grad.resize((W, H)))
    d = ImageDraw.Draw(img, "RGBA")
    l2 = lg.resize((int(lg.width * 0.42 / 0.62), int(lg.height * 0.42 / 0.62)), Image.LANCZOS)
    dan_logo(img, d, l2, W - l2.width - 46, 30)
    bx0, bx1 = 110, W - 110
    ft, s, ls = fit(d, c["tieu_de"].upper(), bx1 - bx0 - 70, 3, (44, 40, 37, 34, 31))
    lh = int(s * 1.22)
    o = norm_o(c.get("o"))
    by0 = H - (34 + 40 + len(ls) * lh + (58 if o else 0) + 26) - 8
    d.rounded_rectangle((bx0, by0, bx1, H + 30), radius=26, fill=(255, 255, 255, 250))
    y = by0 + 28
    fl = font(True, 25)
    tw = d.textlength(c["nhan"].upper(), font=fl)
    d.text(((W - tw) / 2, y), c["nhan"].upper(), font=fl, fill=CAM)
    y += 46
    for ln in ls:
        d.text(((W - d.textlength(ln, font=ft)) / 2, y), ln, font=ft, fill=NAVY)
        y += lh
    chips(d, o, bx0 + 20, y + 10, bx1 - bx0 - 40, center=True)
    return img


def pa2(c, nen, lg):
    img = Image.new("RGB", (W, H), DO_SAM)
    ph = cover(nen, 620, H)
    m = Image.new("L", (620, H), 0)
    ImageDraw.Draw(m).polygon([(120, 0), (620, 0), (620, H), (0, H)], fill=255)
    img.paste(ph, (W - 620, 0), m)
    d = ImageDraw.Draw(img, "RGBA")
    d.polygon([(W - 500, 0), (W - 488, 0), (W - 608, H), (W - 620, H)], fill=(255, 255, 255, 255))
    l2 = lg.resize((int(lg.width * 0.36 / 0.62), int(lg.height * 0.36 / 0.62)), Image.LANCZOS)
    dan_logo(img, d, l2, 56, 42, 255)
    y = 42 + l2.height + 40
    d.text((56, y), c["nhan"].upper(), font=font(True, 21), fill=(255, 196, 160))
    y += 40
    ft, s, ls = fit(d, c["tieu_de"].upper(), 590, 5, (38, 35, 32, 29, 26))
    for ln in ls:
        d.text((56, y), ln, font=ft, fill="white")
        y += int(s * 1.22)
    chips(d, norm_o(c.get("o"))[:4], 56, H - 74, 590, dark=True)
    return img


def pa3(c, nen, lg):
    img = cover(nen, W, H)
    grad = Image.new("L", (W, 1))
    for x in range(W):
        grad.putpixel((x, 0), int(235 * max(0.0, 1 - x / (W * 0.78)) ** 0.9))
    img = Image.composite(Image.new("RGB", (W, H), (12, 16, 28)), img, grad.resize((W, H)))
    d = ImageDraw.Draw(img, "RGBA")
    l2 = lg.resize((int(lg.width * 0.38 / 0.62), int(lg.height * 0.38 / 0.62)), Image.LANCZOS)
    dan_logo(img, d, l2, 64, 44)
    y = 190
    d.rectangle((64, y, 72, y + 34), fill=DO)
    d.text((86, y), c["nhan"].upper(), font=font(True, 23), fill=(255, 205, 170))
    y += 54
    ft, s, ls = fit(d, c["tieu_de"].upper(), 720, 4, (42, 38, 35, 32, 29))
    for ln in ls:
        d.text((64, y), ln, font=ft, fill="white")
        y += int(s * 1.22)
    chips(d, norm_o(c.get("o")), 64, H - 76, 1060, dark=True)
    return img


def pa4(c, nen, lg):
    img = Image.new("RGB", (W, H), "white")
    ph_h = 330
    img.paste(cover(nen, W, ph_h), (0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    l2 = lg.resize((int(lg.width * 0.36 / 0.62), int(lg.height * 0.36 / 0.62)), Image.LANCZOS)
    dan_logo(img, d, l2, W - l2.width - 52, 32)
    tag = (c.get("nhom", "") + "  \u00b7  " + c.get("ngay", "")).upper()
    ftg = font(True, 23)
    tw = d.textlength(tag, font=ftg)
    d.rectangle((0, ph_h - 26, tw + 80, ph_h + 26), fill=DO)
    d.text((48, ph_h - 15), tag, font=ftg, fill="white")
    ft, s, ls = fit(d, c["tieu_de"], W - 120, 3, (40, 37, 34, 31, 28))
    y = ph_h + 50
    for ln in ls:
        d.text((60, y), ln, font=ft, fill=NAVY)
        y += int(s * 1.24)
    chips(d, norm_o(c.get("o")), 60, H - 58, W - 120)
    d.rectangle((0, H - 8, W, H), fill=DO)
    return img


PA = {1: pa1, 2: pa2, 3: pa3, 4: pa4}


def chon_phuong_an(c):
    if c.get("pa") in (1, 2, 3, 4):
        return c["pa"]
    try:
        ng = datetime.datetime.strptime(c.get("ngay", ""), "%d/%m/%Y").date()
    except ValueError:
        ng = datetime.date.today()
    k = NHOM_THU_TU.index(c["nhom_key"]) if c.get("nhom_key") in NHOM_THU_TU else 0
    return (ng.toordinal() + k) % 4 + 1


def chon_nen(c, ds, pid):
    nhom = ds.get(c.get("nhom_key", ""), {})
    pool = nhom.get(c.get("sp", ""), []) or nhom.get("chung", []) or [i for v in nhom.values() for i in v]
    if not pool:
        raise RuntimeError("Khong co anh nen cho %s/%s" % (c.get("nhom_key"), c.get("sp")))
    rnd = random.Random("%s-%s" % (pid, c.get("ngay", "")))
    ids = pool[:]
    rnd.shuffle(ids)
    for i in ids[:4]:
        r = requests.get(PEXELS.format(i), headers={"User-Agent": wp.UA}, timeout=60)
        if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
            return Image.open(io.BytesIO(r.content)).convert("RGB"), i
    raise RuntimeError("Khong tai duoc anh nen Pexels")


def ve(c, nen, lg):
    pa = chon_phuong_an(c)
    buf = io.BytesIO()
    PA[pa](c, nen, lg).save(buf, "JPEG", quality=86, optimize=True, progressive=True)
    return buf.getvalue(), pa


def lay_logo():
    og = Image.open(io.BytesIO(requests.get(OG, headers={"User-Agent": wp.UA}, timeout=60).content)).convert("RGB")
    lg = og.crop((78, 68, 584, 222))
    return lg.resize((int(lg.width * 0.62), int(lg.height * 0.62)), Image.LANCZOS)


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    ds = json.load(open(os.path.join("data", "anh_nen.json"), encoding="utf-8"))
    base = wp._cfg()[0] + "/index.php/wp-json/wp/v2"
    s = wp._sess()
    r = s.get(base + "/categories", params={"slug": "ban-tin", "_fields": "id"}, timeout=60)
    r.raise_for_status()
    if not r.json():
        return "chua co chuyen muc ban-tin"
    cat = r.json()[0]["id"]
    r = s.get(base + "/posts", params={"categories": cat, "status": "draft,pending,future,publish", "per_page": 20,
                                       "context": "edit", "_fields": "id,slug,featured_media,content"}, timeout=60)
    r.raise_for_status()
    lg, out = None, []
    for p in r.json():
        m = SPEC.search(p["content"]["raw"])
        if not m:
            continue
        fm = p.get("featured_media") or 0
        if fm and fm not in ANH_MAC_DINH:
            # chi ve lai khi bai chua co anh, dang dung anh chuyen muc, hoac anh mau cu (ban-tin-);
            # anh da ve (bt2-) hoac anh anh Long tu chon thi giu nguyen
            mr = s.get("%s/media/%d" % (base, fm), params={"_fields": "slug"}, timeout=60)
            if mr.status_code != 200 or not mr.json().get("slug", "").startswith("ban-tin-"):
                continue
        c = json.loads(m.group(1))
        if lg is None:
            lg = lay_logo()
        nen, nid = chon_nen(c, ds, p["id"])
        data, pa = ve(c, nen, lg)
        ten = "bt2-" + (p.get("slug") or str(p["id"]))[:80]
        mr = s.post(base + "/media", data=data, timeout=120,
                    headers={"Content-Type": "image/jpeg", "Content-Disposition": 'attachment; filename="%s.jpg"' % ten})
        if mr.status_code >= 400:
            raise RuntimeError("Tai anh bai %d loi %d: %s" % (p["id"], mr.status_code, mr.text[:200]))
        mid = mr.json()["id"]
        s.post("%s/media/%d" % (base, mid), json={"alt_text": c["tieu_de"][:200], "title": c["tieu_de"][:200],
                                                   "caption": "Ảnh nền: Pexels"}, timeout=60)
        u = s.post("%s/posts/%d" % (base, p["id"]), json={"featured_media": mid}, timeout=60)
        if u.status_code >= 400:
            raise RuntimeError("Gan anh bai %d loi %d" % (p["id"], u.status_code))
        out.append("%d -> anh %d (phuong an %d, nen pexels %d)" % (p["id"], mid, pa, nid))
    return "; ".join(out) if out else "khong co bai can anh"
