"""Chay mot lan (23/10/2026):
  1. Trang 111: khoi so sanh gia (#pmG) va o quy doi (#gdCv) dung ty gia Vietcombank (truong r cua
     trang du lieu 178) thay cho muc co dinh 26.200 d/USD.
  2. Trang 31 (Gia the gioi truc tuyen): thay khung giu cho bang 2 khoi tren (doc du lieu that tu trang 178).
Sao luu noi dung cu vao data/backup/ truoc khi ghi. Chuoi can sua phai xuat hien dung 1 lan, neu khong thi dung.
"""
import os
import re
import datetime
import wp

LABEL = "' đ/USD (Vietcombank, trung bình mua/bán)'"
EDITS_111 = [
    ("RATE=26200,", "RATE=D.r||26200,"),
    ("'Tỷ giá quy đổi áp dụng: '+RATE.toLocaleString('vi-VN')+' đ/USD (cố định)'",
     "'Tỷ giá quy đổi: '+RATE.toLocaleString('vi-VN')+" + LABEL),
    ("D=n;build();",
     "D=n;if(n.r){RATE=n.r}build();document.getElementById('pmR').textContent='Tỷ giá quy đổi: '+RATE.toLocaleString('vi-VN')+" + LABEL + ";"),
    ("def.dom={silver:n.silver.s,gold:n.gold.s};", "def.dom={silver:n.silver.s,gold:n.gold.s};if(n.r){def.rate=n.r}"),
]
INTRO_31 = """<!-- wp:paragraph -->
<p>So sánh giá vàng, bạc quốc tế (quy đổi VNĐ theo tỷ giá Vietcombank) với giá vật chất trong nước: bạc thỏi Phú Quý, vàng miếng SJC. Số liệu tự cập nhật lúc 10h và 16h các ngày thứ Hai đến thứ Bảy. Xem thêm phân tích tại trang <a href="https://giaodichhanghoa247.vn/index.php/kim-loai-quy/">Vàng bạc vật chất</a>.</p>
<!-- /wp:paragraph -->

"""
OUTRO_31 = """

<!-- wp:paragraph {"fontSize":"small"} -->
<p class="has-small-font-size"><em>Giá quốc tế quy đổi chưa gồm thuế, phí nhập khẩu và gia công nên luôn thấp hơn giá vật chất trong nước. Nội dung tham khảo, không phải khuyến nghị mua bán.</em></p>
<!-- /wp:paragraph -->"""


def backup(name, text):
    os.makedirs(os.path.join("data", "backup"), exist_ok=True)
    p = os.path.join("data", "backup", "%s_%s.html" % (name, datetime.date.today().isoformat()))
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def block_with(raw, marker):
    """Tat ca khoi wp:html co nhac toi marker (HTML, CSS, script co the nam o cac khoi rieng), giu thu tu."""
    blocks = re.findall(r"<!-- wp:html -->[\s\S]*?<!-- /wp:html -->", raw)
    hit = [b for b in blocks if marker in b]
    if not hit or not any("id=\"%s\"" % marker in b for b in hit) or not any("pages/178" in b for b in hit):
        raise RuntimeError("Khong tach duoc khoi %s (%d khoi)" % (marker, len(hit)))
    return "\n\n".join(hit)


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    raw = wp.get_raw(111)
    new = raw
    for a, b in EDITS_111:
        n = new.count(a)
        if n != 1:
            raise RuntimeError("Trang 111: chuoi '%s...' xuat hien %d lan (can 1)" % (a[:40], n))
        new = new.replace(a, b)
    old31 = wp.get_raw(31)
    page31 = INTRO_31 + block_with(new, "pmG") + "\n\n" + block_with(new, "gdCv") + OUTRO_31
    backup("trang111", raw)
    backup("trang31", old31)
    back = wp.set_raw(111, new)
    if "RATE=D.r||26200" not in back:
        raise RuntimeError("Doc lai trang 111 khong thay ban sua")
    back31 = wp.set_raw(31, page31)
    if "id=\"pmG\"" not in back31:
        raise RuntimeError("Doc lai trang 31 khong thay khoi gia")
    return "da sua trang 111 (%d -> %d ky tu) va trang 31 (%d -> %d ky tu); ban cu luu data/backup" % (
        len(raw), len(new), len(old31), len(page31))
