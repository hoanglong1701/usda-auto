"""COT robusta va ton kho ca phe tu Coffee Market Report cong khai cua I & M Smith (iandmsmith.com).

I & M Smith da dong y cho dung so lieu trong bao cao cong khai (thu cua Michael, 30/10/2026): chi lay con so, ghi nguon
va dan link, khong chep van ban bao cao. Ghi khoa "im" cua trang du lieu 1884:
  cot [[thu Ba chot so, net lo (am la ban rong), "mm" Managed Money / "nc" Non-Commercial]]
  ara [[ngay, bao]] ton kho arabica New York, rob [[ngay, bao]] ton kho robusta London
Moi lan chay doc bao cao moi, roi lay tiep lich su cu trong gioi han thoi gian (chi bao cao thu Hai, moi tuan 1 bai).
"""
import re
import time
import html
import datetime
import requests
import wp

UA = {"User-Agent": wp.UA}
PAGE = 1884
SITEMAP = "https://www.iandmsmith.com/post-sitemap%s.xml"
CHO = 2  # giay giua 2 lan goi, de khong lam phien may chu cua ho
GIOI_HAN = 20 * 60  # giay cho moi lan chay
THANG = {m: i + 1 for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July", "August",
                                         "September", "October", "November", "December"))}


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


def ngay_chu(d, m, y, goc):
    """'19', 'October', '2026' -> date; thieu nam thi lay nam gan ngay bao cao nhat."""
    if m not in THANG:
        return None
    nam = int(y) if y else goc.year
    try:
        x = datetime.date(nam, THANG[m], int(d))
    except ValueError:
        return None
    if not y and x > goc + datetime.timedelta(days=7):
        x = x.replace(year=nam - 1)
    return x


def thu_ba(x):
    """Ngay ghi trong bao cao doi khi lech 1 ngay (vd 'Tuesday 19th October 2026'): dua ve thu Ba gan nhat."""
    return min((x + datetime.timedelta(days=k) for k in range(-3, 4)), key=lambda z: (z.weekday() != 1, abs((z - x).days)))


def doc(t, ngay):
    """Chu bao cao -> {"cot": [...], "ara": [...], "rob": [...]} (khoa nao khong co thi thieu)."""
    goc = datetime.date.fromisoformat(ngay)
    out = {}
    i = re.search(r"Commitment of Traders report from the London [Rr]obusta", t)
    if i:
        s = t[i.start():i.start() + 560]
        v = re.search(r"net[ -](long|short)(?: sold)? position of ([\d,]+)\s*[Ll]ots", s)
        d = re.search(r"Tuesday,?\s+(\d{1,2})\s*(?:st|nd|rd|th)?\.?\s+(?:of\s+)?([A-Z][a-z]+)\.?(?:\s+(20\d\d))?", s)
        if v and d:
            x = ngay_chu(d.group(1), d.group(2), d.group(3), goc)
            n = int(v.group(2).replace(",", ""))
            if x and n <= 100000:
                out["cot"] = [thu_ba(x).isoformat(), -n if v.group(1) == "short" else n, "mm" if "Managed Money" in s else "nc"]
    a = re.search(r"[Cc]ertified washed [Aa]rabica coffee stocks.{0,160}?to register these stocks at ([\d,]+) bags", t)
    if a:
        n = int(a.group(1).replace(",", ""))
        if 100000 <= n <= 4000000:
            lui = 3 if goc.weekday() == 0 else 1  # bao cao thu Hai ghi so cua thu Sau
            out["ara"] = [(goc - datetime.timedelta(days=lui)).isoformat(), n]
    r = re.search(r"London Robusta stocks[^.]{0,90}?([\d,]{7,}) bags[^.]{0,20}?as of the (\d{1,2})\s*(?:st|nd|rd|th)?\s+([A-Z][a-z]+)\s+(20\d\d)", t)
    if r:
        x = ngay_chu(r.group(2), r.group(3), r.group(4), goc)
        n = int(r.group(1).replace(",", ""))
        if x and 50000 <= n <= 8000000:
            out["rob"] = [x.isoformat(), n]
    return out


def chon(ds):
    """Moi tuan 1 bao cao: thu Hai, tuan khong co thi lay bai dau tuan co."""
    tuan = {}
    for d, u in ds:
        y, w, _ = datetime.date.fromisoformat(d).isocalendar()
        if (y, w) not in tuan or d < tuan[(y, w)][0]:
            tuan[(y, w)] = (d, u)
    return sorted(tuan.values())


def run():
    bat_dau = time.time()
    obj = wp.load(PAGE) or {}
    im = obj.get("im") or {}
    bang = {k: {x[0]: x for x in im.get(k, [])} for k in ("cot", "ara", "rob")}
    moi, cu = im.get("moi", ""), im.get("cu", "")
    ds = chon(ds_bao_cao())
    viec = [x for x in ds if x[0] > moi][::-1] + [x for x in ds if cu and x[0] < cu][::-1]
    xong, loi = 0, 0
    for d, u in viec:
        if time.time() - bat_dau > GIOI_HAN:
            break
        try:
            r = doc(chu(u), d)
        except Exception as e:  # noqa  mot bai loi thi bo qua, lan sau khong doc lai
            print("Loi", u, str(e)[:100])
            loi += 1
            r = {}
        for k, v in r.items():
            bang[k][v[0]] = v
        moi = max(moi, d)
        cu = min(cu, d) if cu else d
        xong += 1
    if bang["cot"] and len(bang["cot"]) < 3:
        raise RuntimeError("Qua it diem COT: %s" % list(bang["cot"].values()))
    im = {"nguon": "I & M Smith", "moi": moi, "cu": cu, "cot": sorted(bang["cot"].values()),
          "ara": sorted(bang["ara"].values()), "rob": sorted(bang["rob"].values())}
    obj = wp.load(PAGE) or {}  # doc lai ngay truoc khi ghi
    obj["im"] = im
    obj["asof"] = datetime.date.today().isoformat()
    wp.save(PAGE, obj)
    con = sum(1 for x in ds if x[0] < cu)
    return "I&M Smith: doc %d bao cao (loi %d), COT %d diem, arabica %d, robusta %d; tu %s den %s; con %d bai cu" % (
        xong, loi, len(im["cot"]), len(im["ara"]), len(im["rob"]), cu, moi, con)
