"""USDA NASS - Crop Progress (esmis .txt) -> trang 801, khoa prog."""
import re
import datetime
import requests
from . import wp

LIST_URL = "https://esmis.nal.usda.gov/publication/crop-progress"
PAGE = 801
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
ROW = re.compile(r"^(.{1,17}?)\s*\.*:\s*(.+)$")


def mdate(s):
    m = re.search(r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})", s)
    if not m:
        return None
    return datetime.date(int(m.group(3)), MONTHS.index(m.group(1)) + 1, int(m.group(2))).isoformat()


def vals(s):
    out = []
    for t in s.split():
        if t == "-":
            out.append(0)
        elif t == "(NA)":
            out.append(None)
        else:
            try:
                out.append(int(t))
            except ValueError:
                return None
    return out


def parse(text):
    lines = text.replace("\r", "").split("\n")
    rel = None
    for ln in lines[:15]:
        if ln.startswith("Released"):
            rel = mdate(ln)
            break
    if not rel:
        # co the ngay nam o dong ke tiep
        rel = mdate(" ".join(lines[:15]))
    # tim cac phan
    heads = []
    for i in range(len(lines) - 1):
        ln = lines[i]
        if ln and not ln.startswith(" ") and " - " in ln and (lines[i + 1].startswith("[") or lines[i + 1].startswith("---")):
            heads.append(i)
    heads.append(len(lines))
    cond, prog, wk = [], [], None
    for a, b in zip(heads, heads[1:]):
        title = lines[a]
        name = title.split(" - ")[0].strip()
        if name.startswith("Days Suitable"):
            continue
        rows = []
        for ln in lines[a + 1:b]:
            if re.search(r"percent", ln, re.I):
                continue
            m = ROW.match(ln)
            if not m:
                continue
            label = m.group(1).strip()
            v = vals(m.group(2))
            if v is None or not label:
                continue
            rows.append((label, v))
        if "Week Ending" in title:
            w = mdate(title.split("Week Ending")[1])
            nat = [v for l, v in rows if l.endswith("States") or l.startswith("United States") or l.startswith("Total")]
            pw = [v for l, v in rows if l.startswith("Previous week")]
            py = [v for l, v in rows if l.startswith("Previous year")]
            if not nat:
                continue
            cond.append([name.replace(" Condition", ""), nat[0], pw[0] if pw else None, py[0] if py else None])
            wk = wk or w
        else:
            nat = [v for l, v in rows if l.endswith("States") or l.startswith("United States") or l.startswith("Total")]
            if nat and len(nat[0]) == 4:
                prog.append([name, nat[0]])
    P = {"rel": rel, "wk": wk, "cond": cond, "prog": prog}
    # kiem tra
    if len(cond) < 3 and len(prog) < 3:
        raise RuntimeError("Qua it muc cond/prog: %d/%d" % (len(cond), len(prog)))
    for c in cond:
        nums = [x for x in c[1] if x is not None]
        if len(c[1]) != 5 or abs(sum(nums) - 100) > 2:
            raise RuntimeError("Condition khong cong ~100: %s" % c)
    return P


def latest_url():
    r = requests.get(LIST_URL, timeout=60, headers={"User-Agent": wp.UA})
    r.raise_for_status()
    m = re.search(r'href="([^"]+\.txt)"', r.text)
    if not m:
        raise RuntimeError("Khong thay link .txt")
    u = m.group(1)
    if u.startswith("/"):
        u = "https://esmis.nal.usda.gov" + u
    return u


def run():
    t = requests.get(latest_url(), timeout=90, headers={"User-Agent": wp.UA}).text
    P = parse(t)
    if wp.enabled():
        old = wp.load(PAGE).get("prog", {})
        if old.get("rel") == P["rel"]:
            return "khong co bao cao moi (phat hanh %s)" % P["rel"]
        wp.update_key(PAGE, "prog", P)
        return "da cap nhat phat hanh %s, tuan %s" % (P["rel"], P["wk"])
    return "chua cau hinh WordPress; da parse %s" % P["rel"]
