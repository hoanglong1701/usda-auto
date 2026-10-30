"""So lieu ca phe tu Coffee Market Report cong khai cua I & M Smith (iandmsmith.com), da duoc ho dong y cho dung (30/10/2026).

thu(): lay vai bao cao moi nam, in cac doan chua so COT robusta va ton kho de viet bo doc.
"""
import re
import time
import html
import requests
import wp

UA = {"User-Agent": wp.UA}
SITEMAP = "https://www.iandmsmith.com/post-sitemap%s.xml"
CHO = 2  # giay giua 2 lan goi, de khong lam phien may chu cua ho


def ds_bao_cao():
    """[(ngay yyyy-mm-dd, url)] tu sitemap, cu nhat truoc."""
    out = []
    for n in ("", "2", "3", "4"):
        r = requests.get(SITEMAP % n, headers=UA, timeout=60)
        time.sleep(CHO)
        if r.status_code != 200:
            continue
        for u, d in re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>(\d{4}-\d{2}-\d{2})", r.text):
            if "coffee-market-report" in u:
                out.append((d, u))
    return sorted(out)


def chu(u):
    r = requests.get(u, headers=UA, timeout=60)
    r.raise_for_status()
    time.sleep(CHO)
    t = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", r.text)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", t)).split())


def thu():
    ds = ds_bao_cao()
    print("so bao cao:", len(ds), ds[0] if ds else None, ds[-1] if ds else None)
    theo_nam = {}
    for d, u in ds:
        # bao cao thu Hai thuong co COT
        import datetime
        if datetime.date.fromisoformat(d).weekday() == 0:
            theo_nam.setdefault(d[:4], []).append((d, u))
    for y in sorted(theo_nam):
        if y not in ("2015", "2018", "2021", "2024", "2026"):
            continue
        d, u = theo_nam[y][len(theo_nam[y]) // 2]
        t = chu(u)
        print("=====", d, u, len(t))
        for pat in (r".{0,60}Commitment of Traders report from the London.{0,380}", r".{0,160}[Rr]obusta[^.]{0,80}stocks.{0,200}",
                    r".{0,60}[Cc]ertified washed.{0,200}", r".{0,120}\blots\b[^.]{0,40}[Rr]obusta.{0,120}"):
            for m in list(re.finditer(pat, t))[:2]:
                print(">", m.group(0))
    return "chay thu, khong ghi"
