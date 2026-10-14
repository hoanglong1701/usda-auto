"""USDA AMS - thanh tra xuat khau ngu coc hang tuan (wa_gr101.txt) -> trang 801, khoa insp."""
import re
import datetime
import requests
import wp

URL = "https://www.ams.usda.gov/mnreports/wa_gr101.txt"
PAGE = 801
MON = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}
REGIONS = ("ATLANTIC", "GULF", "PACIFIC", "INTERIOR", "LAKES", "GREAT LAKES", "ST LAWR SWY")
GRAINS = ("WHEAT", "CORN", "SOYBEANS", "SORGHUM", "BARLEY")
# thu tu co dinh cua mang tot / gia tri theo cot (8 phan tu, giu nhu trang 801 hien co)
ORDER = ["WHEAT", "YELLOW", "WHITE", "BARLEY", "SORGHUM", "SOYBEANS", "CANOLA", "TOTALS"]


def num(s):
    return int(s.replace(",", ""))


def parse(text):
    text = text.replace("\r", "")
    m = re.search(r"WEEK ENDING\s+([A-Z]{3})[A-Z]*\s+(\d{1,2}),\s*(\d{4})", text)
    if not m:
        raise RuntimeError("Khong tim thay WEEK ENDING")
    wk = datetime.date(int(m.group(3)), MON[m.group(1)], int(m.group(2))).isoformat()

    # bang tong theo loai hat: 5 so
    summ = {}
    for line in text.split("\n"):
        mm = re.match(r"^\s*(WHEAT|CORN|SOYBEANS|SORGHUM|BARLEY)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", line)
        if mm and mm.group(1) not in summ:
            summ[mm.group(1)] = [num(mm.group(i)) for i in range(2, 7)]
    for g in GRAINS:
        summ.setdefault(g, [0, 0, 0, 0, 0])

    # bang theo vung va nuoc dich
    i = text.find("BY REGION AND COUNTRY OF DESTINATION")
    if i < 0:
        raise RuntimeError("Khong thay bang nuoc dich")
    block = text[i:]
    lines = block.split("\n")
    # tieu de cot: dong chua COUNTRY
    head = None
    for ln in lines[:20]:
        if re.search(r"REGION\s+COUNTRY", ln):
            head = ln
            break
    if head is None:
        raise RuntimeError("Khong thay dong tieu de cot")
    toks = head.split()
    toks = toks[toks.index("COUNTRY") + 1:]
    cols = [t for t in toks]  # vd WHEAT YELLOW WHITE SORGHUM SOYBEANS CANOLA TOTALS
    ncol = len(cols)
    rowre = re.compile(r"^\s*(?:(?:%s)\s+)?([A-Z][A-Z .,'\-]*?)\s+((?:[\d,]+\s+){%d}[\d,]+)\s*$"
                       % ("|".join(REGIONS), ncol - 1))
    by = {}
    tot = None
    for ln in lines[1:]:
        if "NOT INCLUDED IN TOTAL" in ln:
            break
        mm = rowre.match(ln)
        if not mm:
            continue
        name = mm.group(1).strip()
        vals = [num(x) for x in mm.group(2).split()]
        full = [0] * len(ORDER)
        for c, v in zip(cols, vals):
            if c in ORDER:
                full[ORDER.index(c)] = v
        if name.startswith("SUBTOTAL"):
            continue
        if name in ("TOTAL", "TOTALS"):
            tot = full
            continue
        acc = by.setdefault(name, [0] * len(ORDER))
        for k in range(len(ORDER)):
            acc[k] += full[k]
    if tot is None:
        raise RuntimeError("Khong thay dong TOTAL")

    # doi chieu voi bang tong
    def close(a, b):
        return abs(a - b) <= max(1, 0.01 * max(a, b))
    if not close(summ["CORN"][0], tot[1] + tot[2]):
        raise RuntimeError("Lech ngo: %s vs %s" % (summ["CORN"][0], tot[1] + tot[2]))
    if not close(summ["SOYBEANS"][0], tot[5]):
        raise RuntimeError("Lech dau tuong")
    if not close(summ["WHEAT"][0], tot[0]):
        raise RuntimeError("Lech lua mi")

    def top(fn):
        arr = [[n, fn(v)] for n, v in by.items() if fn(v) > 0]
        arr.sort(key=lambda x: -x[1])
        return arr[:8]
    dest = {
        "corn": top(lambda v: v[1] + v[2]),
        "soy": top(lambda v: v[5]),
        "wheat": top(lambda v: v[0]),
    }
    return {"wk": wk, "sum": summ, "tot": tot, "dest": dest}


def fetch():
    r = requests.get(URL, timeout=60, headers={"User-Agent": wp.UA})
    r.raise_for_status()
    return r.text


def run():
    insp = parse(fetch())
    if wp.enabled():
        old = wp.load(PAGE).get("insp", {})
        if old.get("wk") == insp["wk"] and old.get("sum") == insp["sum"]:
            return "khong co bao cao moi (tuan %s)" % insp["wk"]
        wp.update_key(PAGE, "insp", insp)
        return "da cap nhat tuan %s" % insp["wk"]
    return "chua cau hinh WordPress; da parse tuan %s" % insp["wk"]
