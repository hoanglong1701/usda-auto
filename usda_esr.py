"""USDA FAS - Export Sales Report (ESR) hang tuan -> trang 801, khoa esr (phan cur; tu them lich su khi nien vu ket thuc)."""
import os
import datetime
import requests
import wp
from names import vn

API = "https://api.fas.usda.gov/api/esr"
PAGE = 801
CODES = {"ngo": 401, "dau_tuong": 801, "kho_dau": 901, "dau_dau": 902, "lua_mi": 107, "gao": 1505}
# thang/ngay ket thuc nien vu
MY_END = {401: (8, 31), 801: (8, 31), 901: (9, 30), 902: (9, 30), 107: (5, 31), 1505: (7, 31)}


def _get(path):
    r = requests.get(API + path, headers={"X-Api-Key": os.environ["FAS_API_KEY"], "User-Agent": wp.UA}, timeout=90)
    r.raise_for_status()
    return r.json()


def countries():
    d = _get("/countries")
    return {c["countryCode"]: c.get("countryDescription", "") for c in d}


def agg_for(code, my, cmap):
    rows = _get("/exports/commodityCode/%d/allCountries/marketYear/%d" % (code, my))
    if not rows:
        return None
    wk = max(r["weekEndingDate"][:10] for r in rows)
    agg = {}
    for r in rows:
        if r["weekEndingDate"][:10] != wk:
            continue
        name = vn(cmap.get(r["countryCode"], str(r["countryCode"])))
        a = agg.setdefault(name, [0, 0])
        a[0] += r.get("accumulatedExports") or 0
        a[1] += r.get("outstandingSales") or 0
    return wk, agg


def build_cur(code, my, wk, agg):
    ranked = sorted(agg.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))
    top = ranked[:10]
    tot_acc = round(sum(a[0] for a in agg.values()) / 1000)
    tot_out = round(sum(a[1] for a in agg.values()) / 1000)
    rows = [[n, round(a[0] / 1000), round(a[1] / 1000)] for n, a in top]
    rest = [tot_acc - sum(r[1] for r in rows), tot_out - sum(r[2] for r in rows)]
    end = MY_END[code]
    done = 1 if datetime.date.today() > datetime.date(my, end[0], end[1]) else 0
    return {"lbl": "%d/%02d" % (my - 1, my % 100), "done": done, "wk": wk,
            "rows": rows, "rest": rest, "acc": tot_acc, "out": tot_out}


def pick_year(code, cmap):
    y = datetime.date.today().year
    for my in (y + 1, y):
        got = agg_for(code, my, cmap)
        if got:
            return my, got
    raise RuntimeError("Khong co du lieu ESR cho ma %d" % code)


def add_history(item, code, old_lbl, cmap):
    """Them nien vu vua ket thuc vao p/o/t neu du dieu kien."""
    old_my = int(old_lbl.split("/")[0]) + 1
    idx = (old_my - 1) - item["y0"]
    keys = list(item["p"].keys())
    if len(item["t"]) != idx or any(len(item["p"][k]) != idx for k in keys) or len(item["o"]) != idx:
        return False
    got = agg_for(code, old_my, cmap)
    if not got:
        return False
    _, agg = got
    total = round(sum(a[0] for a in agg.values()) / 1000)
    s = 0
    for k in keys:
        v = round(agg.get(k, [0, 0])[0] / 1000)
        item["p"][k].append(v)
        s += v
    item["o"].append(total - s)
    item["t"].append(total)
    return True


def run():
    cmap = countries()
    page = wp.load(PAGE) if wp.enabled() else {"esr": {}}
    esr = page.get("esr", {})
    notes, changed = [], False
    new_wk = {}
    for key, code in CODES.items():
        my, (wk, agg) = pick_year(code, cmap)
        cur = build_cur(code, my, wk, agg)
        item = esr.get(key)
        new_wk[key] = wk
        if item is None:
            notes.append("%s: chua co trong trang 801" % key)
            continue
        old = item.get("cur", {})
        # kiem tra hop ly
        if old.get("lbl") == cur["lbl"]:
            if old.get("wk") and cur["wk"] < old["wk"]:
                notes.append("%s: tuan moi cu hon, bo qua" % key)
                continue
            oa = old.get("acc", 0) + old.get("out", 0)
            na = cur["acc"] + cur["out"]
            if oa and na and (na > 3 * oa or na * 3 < oa):
                notes.append("%s: so lieu lech > 3 lan, bo qua (%s -> %s)" % (key, oa, na))
                continue
            if old.get("wk") == cur["wk"] and old.get("acc") == cur["acc"] and old.get("out") == cur["out"]:
                continue
        else:
            if old.get("lbl") and add_history(item, code, old["lbl"], cmap):
                notes.append("%s: da them lich su nien vu %s" % (key, old["lbl"]))
            elif old.get("lbl"):
                notes.append("%s: CAN BO SUNG lich su nien vu %s (tu dong khong du dieu kien)" % (key, old["lbl"]))
        item["cur"] = cur
        changed = True
    if changed and wp.enabled():
        page["esr"] = esr
        page["asof"] = datetime.date.today().isoformat()
        wp.save(PAGE, page)
    msg = "co cap nhat" if changed else "khong co bao cao moi"
    return "%s; tuan %s; %s" % (msg, max(new_wk.values()), "; ".join(notes) or "ok")
