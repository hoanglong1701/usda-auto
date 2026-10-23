"""Chay mot lan (23/10/2026): thay khoi ENSO (#gden) tren trang nong san 299 bang ban moi trong khoi/enso-299.html
(don vi gia theo san; khung truoc/sau 3, 6, 12 thang). Sao luu noi dung cu vao data/backup/ truoc khi ghi.
"""
import os
import re
import datetime
import wp

PAGE = 299
FILE = os.path.join("khoi", "enso-299.html")
PAT = r"<!-- wp:html -->(?:(?!<!-- /wp:html -->)[\s\S])*?<div id=\"gden\">[\s\S]*?<!-- /wp:html -->"


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    blk = re.findall(PAT, open(FILE, encoding="utf-8").read())
    if len(blk) != 1 or "&" in blk[0]:
        raise RuntimeError("File khoi moi khong hop le")
    raw = wp.get_raw(PAGE)
    cur = re.findall(PAT, raw)
    if len(cur) != 1:
        raise RuntimeError("Trang %d: tim thay %d khoi #gden (can 1)" % (PAGE, len(cur)))
    os.makedirs(os.path.join("data", "backup"), exist_ok=True)
    with open(os.path.join("data", "backup", "trang%d_%s.html" % (PAGE, datetime.date.today().isoformat())), "w",
              encoding="utf-8") as f:
        f.write(raw)
    new = raw.replace(cur[0], blk[0])
    back = wp.set_raw(PAGE, new)
    if 'id="gden-wb"' not in back:
        raise RuntimeError("Doc lai trang %d khong thay ban sua" % PAGE)
    return "da thay khoi ENSO trang %d (%d -> %d ky tu); ban cu luu data/backup" % (PAGE, len(raw), len(new))
