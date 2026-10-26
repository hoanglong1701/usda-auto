"""Chay mot lan (26/10/2026): sap lai menu va cac trang tong hop.

Menu:
  - Phan tich thi truong: Tong hop cac bao cao, Tong quat ve kinh te the gioi, Khuyen nghi (chuyen tu Phan tich chuyen sau).
  - Phan tich chuyen sau: Nong san, Kim loai, Nguyen lieu cong nghiep, Nang luong.
  - Kien thuc dau tu: them 3 muc con (Phan tich ky thuat, co ban, lien thi truong).
  - "Tin tuc nhanh" (trang 28, tin cu 24/9): an khoi menu (status draft), khong xoa.
Trang:
  - 106: bo khoi Tin tuc nhanh, them the cac muc con kem "Doc them".
  - 107: them the 4 nhom kem "Doc them", them muc Nang luong.
  - 112: them id cho 3 tieu de de menu tro toi.
Sao luu menu va noi dung cu vao data/backup/ truoc khi ghi.
"""
import os
import re
import json
import datetime
import wp

BASE = "https://giaodichhanghoa247.vn/index.php"
TODAY = datetime.date.today().isoformat()


def backup(name, text):
    os.makedirs(os.path.join("data", "backup"), exist_ok=True)
    with open(os.path.join("data", "backup", "%s_%s.%s" % (name, TODAY, "json" if name.startswith("menu") else "html")), "w",
              encoding="utf-8") as f:
        f.write(text)


def the_hub(cards, cot=220):
    """Khoi the muc con: [(tieu de, mo ta, link)]."""
    css = ("<style>.gd-hub{display:grid;grid-template-columns:repeat(auto-fill,minmax(%dpx,1fr));gap:12px;margin:8px 0 24px}"
           ".gd-hub a.gd-hub-c{display:flex;flex-direction:column;gap:6px;border:1px solid #e6dede;border-radius:10px;padding:14px;"
           "background:#fff;color:#222;text-decoration:none!important;box-shadow:0 2px 10px rgba(200,0,0,.06)}"
           ".gd-hub a.gd-hub-c:hover{border-color:#c00000}.gd-hub b{font-size:16px;color:#111}"
           ".gd-hub span{font-size:14px;line-height:1.5;color:#555}.gd-hub em{font-style:normal;font-weight:600;color:#c00000;font-size:14px;margin-top:auto}"
           "</style>" % cot)
    body = "".join('<a class="gd-hub-c" href="%s"><b>%s</b><span>%s</span><em>Đọc thêm →</em></a>' % (l, t, m) for t, m, l in cards)
    return "<!-- wp:html -->\n%s<div class=\"gd-hub\">%s</div>\n<!-- /wp:html -->\n\n" % (css, body)


HUB_106 = the_hub([
    ("Tổng hợp các báo cáo", "Dự báo tăng trưởng của IMF, World Bank, OECD, WTO, chỉ số giá lương thực FAO, lịch sự kiện và lịch báo cáo sắp tới.",
     BASE + "/phan-tich-thi-truong/#tong-hop-cac-bao-cao"),
    ("Tổng quát về kinh tế thế giới", "Bản đồ và bảng số liệu tăng trưởng, lạm phát của các nền kinh tế lớn theo IMF.",
     BASE + "/tong-quat-kinh-te-the-gioi/"),
    ("Khuyến nghị", "Khuyến nghị giao dịch mới nhất của GDHH247 và kết quả các lệnh đã đóng: tỷ lệ thắng, lãi lỗ, NAV.",
     BASE + "/khuyen-nghi-ket-qua-khuyen-nghi/"),
])
HUB_107 = the_hub([
    ("Nông sản", "Lịch mùa vụ, báo cáo USDA, top 10 quốc gia, dòng chảy thương mại, COT, El Niño và La Niña.", BASE + "/phan-tich-nong-san/"),
    ("Kim loại", "Giá và tồn kho LME, báo cáo cung cầu đồng, nhôm, kẽm, niken, thiếc, top 10 nước sản xuất, COT.", BASE + "/phan-tich-kim-loai/"),
    ("Nguyên liệu công nghiệp", "Cung cầu cà phê, đường, bông, ca cao, cao su; các nước xuất khẩu đi đâu; tuyến vận chuyển và cảng; COT.",
     BASE + "/phan-tich-nguyen-lieu-cong-nghiep/"),
    ("Năng lượng", "Cung cầu dầu thô, khí tự nhiên; top 10 quốc gia; xuất khẩu đi đâu; các tuyến vận chuyển quan trọng.",
     BASE + "/phan-tich-nang-luong/"),
])
NANG_LUONG_107 = (
    '<!-- wp:heading -->\n<h2 class="wp-block-heading"><a href="%s/phan-tich-nang-luong/">Năng lượng</a></h2>\n<!-- /wp:heading -->\n\n'
    '<!-- wp:paragraph -->\n<p>Cung cầu dầu thô và khí tự nhiên thế giới: top 10 quốc gia sản xuất, tiêu thụ, xuất nhập khẩu; '
    'các báo cáo của OPEC, IEA, EIA; dầu thô xuất đi đâu và các tuyến vận chuyển quan trọng. Nhóm năng lượng hiện chưa được giao dịch tại GDHH247.</p>\n'
    '<!-- /wp:paragraph -->\n\n'
    '<!-- wp:paragraph -->\n<p><a href="%s/phan-tich-nang-luong/">Đọc thêm phân tích năng lượng →</a></p>\n<!-- /wp:paragraph -->\n\n' % (BASE, BASE))


def sua_menu():
    s = wp._sess()
    api = wp._cfg()[0] + "/index.php/wp-json/wp/v2/menu-items"
    r = s.get(api, params={"per_page": 100, "context": "edit"}, timeout=60)
    r.raise_for_status()
    items = r.json()
    backup("menu", json.dumps(items, ensure_ascii=False, indent=1))
    by = {it["id"]: it for it in items}
    if 116 not in by or 117 not in by:
        raise RuntimeError("Khong thay menu chinh (116, 117)")
    menu = by[116]["menus"]
    ten = lambda it: re.sub("<[^>]+>", "", (it["title"].get("raw") or it["title"].get("rendered") or "")).strip()  # noqa
    # muc con cua Kien thuc dau tu (tao neu chua co)
    KT = [("Phân tích kỹ thuật", "phan-tich-ky-thuat"), ("Phân tích cơ bản", "phan-tich-co-ban"),
          ("Phân tích liên thị trường", "phan-tich-lien-thi-truong")]
    kt_ids = []
    for t, a in KT:
        ex = [it for it in items if it.get("parent") == 125 and ten(it) == t]
        if ex:
            kt_ids.append(ex[0]["id"])
            continue
        c = s.post(api, json={"title": t, "url": "%s/kien-thuc-dau-tu/#%s" % (BASE, a), "type": "custom", "status": "publish",
                              "menus": menu, "parent": 125, "menu_order": 90}, timeout=60)
        if c.status_code >= 400:
            raise RuntimeError("Tao muc menu %s loi %d: %s" % (t, c.status_code, c.text[:200]))
        kt_ids.append(c.json()["id"])
    # thu tu va cha moi: (id, cha)
    order = [(116, 0), (117, 0), (119, 117), (1200, 117), (306, 117),
             (121, 0), (122, 121), (123, 121), (304, 121), (305, 121),
             (124, 0), (125, 0)] + [(i, 125) for i in kt_ids] + [(126, 0), (127, 126), (128, 126), (129, 126), (130, 126)]
    known = {i for i, _ in order}
    rest = [it["id"] for it in items if it["id"] not in known and it["id"] != 237 and it.get("menus") == menu]
    for n, (iid, par) in enumerate(order + [(i, by[i]["parent"]) for i in rest], start=1):
        it = by.get(iid)
        body = {"menu_order": n, "parent": par}
        if it and it.get("menu_order") == n and it.get("parent") == par:
            continue
        u = s.post("%s/%d" % (api, iid), json=body, timeout=60)
        if u.status_code >= 400:
            raise RuntimeError("Sua muc menu %d loi %d: %s" % (iid, u.status_code, u.text[:200]))
    if 237 in by and by[237].get("status") != "draft":
        u = s.post("%s/237" % api, json={"status": "draft", "menu_order": 99}, timeout=60)
        if u.status_code >= 400:
            raise RuntimeError("An muc Tin tuc nhanh loi %d: %s" % (u.status_code, u.text[:200]))
    return "menu: %d muc, them %s muc Kien thuc dau tu" % (len(order), len(kt_ids))


def them_id_tieu_de(raw, chu, aid):
    pat = re.compile(r'<h([2-4]) class="wp-block-heading"[^>]*>(\s*%s\s*)</h\1>' % re.escape(chu))
    if 'id="%s"' % aid in raw:
        return raw
    m = list(pat.finditer(raw))
    if len(m) != 1:
        raise RuntimeError("Tieu de '%s' xuat hien %d lan" % (chu, len(m)))
    return pat.sub(lambda x: '<h%s class="wp-block-heading" id="%s">%s</h%s>' % (x.group(1), aid, x.group(2), x.group(1)), raw)


def sua_106():
    raw = wp.get_raw(106)
    backup("trang106", raw)
    new = raw
    if 'class="gd-nl"' in new:
        h = re.findall(r'<!-- wp:heading[^>]*-->\s*<h2[^>]*>Tin tức nhanh</h2>\s*<!-- /wp:heading -->\s*', new)
        b = re.findall(r'<!-- wp:html -->(?:(?!<!-- /wp:html -->)[\s\S])*?class="gd-nl"[\s\S]*?<!-- /wp:html -->\s*', new)
        if len(h) != 1 or len(b) != 1:
            raise RuntimeError("Trang 106: khong tach duoc khoi Tin tuc nhanh (%d tieu de, %d khoi)" % (len(h), len(b)))
        new = new.replace(h[0], "").replace(b[0], "")
    new = new.replace("tin tức nhanh, lịch sự kiện trong tuần và các báo cáo tổng hợp",
                      "lịch sự kiện trong tuần, các báo cáo tổng hợp, bức tranh kinh tế thế giới và khuyến nghị giao dịch")
    new = them_id_tieu_de(new, "Tổng hợp các báo cáo", "tong-hop-cac-bao-cao")
    if 'class="gd-hub"' not in new:
        p = re.search(r"<!-- wp:paragraph -->\s*<p[^>]*>[^<]*Tổng hợp thông tin thị trường hằng ngày[\s\S]*?<!-- /wp:paragraph -->\s*", new)
        if not p:
            raise RuntimeError("Trang 106: khong thay doan mo dau")
        new = new[:p.end()] + HUB_106 + new[p.end():]
    back = wp.set_raw(106, new)
    if 'class="gd-hub"' not in back or 'class="gd-nl"' in back:
        raise RuntimeError("Doc lai trang 106 khong dung")
    return "106: %d -> %d ky tu" % (len(raw), len(new))


def sua_107():
    raw = wp.get_raw(107)
    backup("trang107", raw)
    new = raw
    if 'class="gd-hub"' not in new:
        p = re.search(r"<!-- wp:paragraph -->\s*<p[^>]*>Bài phân tích chuyên sâu theo từng nhóm sản phẩm[\s\S]*?<!-- /wp:paragraph -->\s*", new)
        if not p:
            raise RuntimeError("Trang 107: khong thay doan mo dau")
        new = new[:p.end()] + HUB_107 + new[p.end():]
    if "/phan-tich-nang-luong/\">Năng lượng</a></h2>" not in new:
        new = new.rstrip() + "\n\n" + NANG_LUONG_107
    back = wp.set_raw(107, new)
    if 'class="gd-hub"' not in back:
        raise RuntimeError("Doc lai trang 107 khong dung")
    return "107: %d -> %d ky tu" % (len(raw), len(new))


def sua_112():
    raw = wp.get_raw(112)
    backup("trang112", raw)
    new = raw
    for chu, aid in (("Phân tích kỹ thuật", "phan-tich-ky-thuat"), ("Phân tích cơ bản", "phan-tich-co-ban"),
                     ("Phân tích liên thị trường", "phan-tich-lien-thi-truong")):
        new = them_id_tieu_de(new, chu, aid)
    if new != raw:
        wp.set_raw(112, new)
    return "112: them id tieu de"


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    return " | ".join([sua_106(), sua_107(), sua_112(), sua_menu()])
