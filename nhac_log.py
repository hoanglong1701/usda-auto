"""Nhac nhap Log khuyen nghi (chay sang thu Bay, workflow nhac-log.yml).
Doc ngay lenh cuoi tren trang du lieu 227; neu qua 7 ngay chua co lenh moi thi thoat ma 1
de GitHub gui email "Run failed" cho chu repo, kem noi dung nhac trong log.
"""
import re
import sys
import json
import html
import datetime
import requests
import wp

URL = "https://giaodichhanghoa247.vn/index.php/wp-json/wp/v2/pages/227"


def run():
    j = requests.get(URL, params={"_fields": "content"}, headers={"User-Agent": wp.UA}, timeout=60).json()
    d = json.loads(html.unescape(re.search(r'<pre id="gd-data"[^>]*>(.*?)</pre>', j["content"]["rendered"], re.S).group(1)))
    last = datetime.date.fromisoformat(d["kpi"]["last_date"])
    days = (datetime.date.today() - last).days
    return last, days


if __name__ == "__main__":
    last, days = run()
    if days > 7:
        print("NHAC VIEC: Log khuyen nghi chua co lenh moi tu %s (%d ngay)." % (last.strftime("%d/%m/%Y"), days))
        print("Trang Ket qua khuyen nghi (KPI, NAV) se dung o ngay nay cho toi khi anh nhap lenh moi vao Log.")
        sys.exit(1)
    print("Log khuyen nghi cap nhat %s, binh thuong." % last.isoformat())
