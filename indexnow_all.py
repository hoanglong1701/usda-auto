"""Gui toan bo URL trong sitemap toi IndexNow (Bing, Yandex, Seznam, Naver) mot lan, vd sau khi doi dia chi trang.
Bai moi hang ngay do mu-plugin GDHH247 tu gui khi dang.
"""
import re
import requests
import wp

BASE = "https://giaodichhanghoa247.vn"
KEY = "a7f3c1e9d4b2486f9e0c5d7a1b3f8e62"


def run():
    h = {"User-Agent": wp.UA}
    k = requests.get("%s/%s.txt" % (BASE, KEY), headers=h, timeout=60)
    if k.status_code != 200 or k.text.strip() != KEY:
        raise RuntimeError("Tep khoa IndexNow chua dung (%d)" % k.status_code)
    idx = requests.get(BASE + "/sitemap_index.xml", headers=h, timeout=60).text
    urls = []
    for sm in re.findall(r"<loc>(.*?)</loc>", idx):
        urls += re.findall(r"<loc>(.*?)</loc>", requests.get(sm, headers=h, timeout=60).text)
    urls = sorted(set(u for u in urls if u.startswith(BASE) and "/index.php/" not in u))
    if not urls:
        raise RuntimeError("Sitemap khong co URL")
    r = requests.post("https://api.indexnow.org/indexnow", timeout=60, headers={"Content-Type": "application/json; charset=utf-8"},
                      json={"host": "giaodichhanghoa247.vn", "key": KEY, "keyLocation": "%s/%s.txt" % (BASE, KEY), "urlList": urls[:10000]})
    if r.status_code not in (200, 202):
        raise RuntimeError("IndexNow tra %d: %s" % (r.status_code, r.text[:200]))
    return "da gui %d URL toi IndexNow (%d)" % (len(urls), r.status_code)
