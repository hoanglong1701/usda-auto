"""Job HANG THANG (thay the hoan toan tac vu Claude "Gia vang bac thang + lai suat Fed"):
bo sung thang moi vao HX (trang 111, widget #gdq) va G/S/E (widget #gdfh), dung FRED API chinh thuc
(api.stlouisfed.org, can FRED_API_KEY) + World Bank Pink Sheet (qua probe.wb_pink_sheet_tail).
CHI sua trang 111. Khong dong tac vu Claude cu tu dong - de anh Long tat thu cong sau khi xac nhan ok.
"""
import os
import re
import json
import datetime
import urllib.request
import urllib.error
import calendar

import wp
import probe

FRED_API = "https://api.stlouisfed.org/fred/series/observations"
PAGE_ID = 111


def _fred_get(series_id, start, end, key):
    url = (FRED_API + "?series_id=%s&api_key=%s&file_type=json&observation_start=%s"
           "&observation_end=%s&sort_order=asc" % (series_id, key, start, end))
    req = urllib.request.Request(url, headers={"User-Agent": "gdhh247-fred/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data.get("observations", [])


def _month_bounds(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    last_day = calendar.monthrange(y, m)[1]
    return "%s-01" % ym, "%04d-%02d-%02d" % (y, m, last_day)


def month_value(series_id, ym, key):
    """Gia tri cua 1 chuoi THANG (GS10, FEDFUNDS, CPIAUCSL) tai thang ym. None neu chua co."""
    start, end = _month_bounds(ym)
    obs = _fred_get(series_id, start, end, key)
    for o in obs:
        if o["date"] == start and o["value"] not in (".", None):
            return float(o["value"])
    return None


def month_avg_daily(series_id, ym, key):
    """Trung binh thang cua 1 chuoi HANG NGAY (vd T10Y2Y)."""
    start, end = _month_bounds(ym)
    obs = _fred_get(series_id, start, end, key)
    vals = [float(o["value"]) for o in obs if o["value"] not in (".", None)]
    if not vals:
        return None
    return sum(vals) / len(vals)


def cpi_yoy(ym, key):
    y, m = int(ym[:4]), int(ym[5:7])
    cur = month_value("CPIAUCSL", ym, key)
    prev_ym = "%04d-%02d" % (y - 1, m)
    prev = month_value("CPIAUCSL", prev_ym, key)
    if cur is None or prev is None or prev == 0:
        return None
    return (cur - prev) / prev * 100.0


def add_months(ym, n):
    y, m = int(ym[:4]), int(ym[5:7])
    m += n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return "%04d-%02d" % (y, m)


def find_balanced(s, open_idx, open_ch, close_ch):
    depth = 0
    i = open_idx
    while i < len(s):
        if s[i] == open_ch:
            depth += 1
        elif s[i] == close_ch:
            depth -= 1
            if depth == 0:
                return open_idx, i + 1
        i += 1
    raise RuntimeError("Khong tim thay dau dong khop cho vi tri %d" % open_idx)


def extract_array(raw, marker, start_hint=0):
    idx = raw.index(marker, start_hint)
    br = idx + len(marker) - 1  # vi tri cua '['
    s, e = find_balanced(raw, br, "[", "]")
    return raw[s:e], s, e


def extract_object(raw, marker, start_hint=0):
    idx = raw.index(marker, start_hint)
    br = idx + len(marker) - 1  # vi tri cua '{'
    s, e = find_balanced(raw, br, "{", "}")
    return raw[s:e], s, e


def fred_events(key, since_date):
    """Doc chuoi DFEDTARU hang ngay tu since_date den nay, tra ve danh sach
    [ngay_cong_bo(YYYY-MM-DD), delta, muc_moi] cho moi lan doi >= 0.25 diem %."""
    today = datetime.date.today().isoformat()
    obs = _fred_get("DFEDTARU", since_date, today, key)
    vals = [(o["date"], float(o["value"])) for o in obs if o["value"] not in (".", None)]
    events = []
    for i in range(1, len(vals)):
        d, v = vals[i]
        pd_, pv = vals[i - 1]
        delta = round(v - pv, 2)
        if abs(delta) >= 0.25:
            ann_date = (datetime.date.fromisoformat(d) - datetime.timedelta(days=1)).isoformat()
            events.append([ann_date, delta, v])
    return events


def run():
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise RuntimeError("Thieu secret FRED_API_KEY")
    if not wp.enabled():
        raise RuntimeError("Thieu secret WP_URL/WP_USER/WP_APP_PASSWORD")

    raw = wp.get_raw(PAGE_ID)

    hx_text, hx_s, hx_e = extract_object(raw, "HX={")
    HX = json.loads(hx_text)
    for k in ("g", "s", "t10", "cs", "ff", "cpi", "ry"):
        if len(HX[k]) != HX["n"]:
            raise RuntimeError("HX.%s dai %d khac n=%d, dung lai de tranh ghi sai" % (k, len(HX[k]), HX["n"]))

    idx_gdfh = raw.index('id="gdfh"')
    g_text, g_s, g_e = extract_array(raw, "G=[", idx_gdfh)
    G = json.loads(g_text)
    s_text, s_s, s_e = extract_array(raw, "S=[", idx_gdfh)
    S = json.loads(s_text)
    e_text, e_s, e_e = extract_array(raw, "E=[", idx_gdfh)
    E = json.loads(e_text)
    if len(G) != len(S):
        raise RuntimeError("G va S trong #gdfh khac do dai (%d vs %d), dung lai" % (len(G), len(S)))
    # G[0] phai khop HX.g tai thang bat dau cua no (da xac minh 1982-01 = index 144 truoc day)
    g_start_idx = HX["n"] - len(G)
    if G[0] != HX["g"][g_start_idx] or S[0] != HX["s"][g_start_idx]:
        raise RuntimeError("G/S khong khop voi duoi cua HX.g/HX.s, dung lai de tranh ghi sai")

    last_idx = HX["n"] - 1
    last_ym = "%04d-%02d" % (HX["y"] + last_idx // 12, last_idx % 12 + 1)

    pink = probe.wb_pink_sheet_tail(8)
    pink_map = {p["m"]: p for p in pink}

    added = []
    skipped = []
    ym = add_months(last_ym, 1)
    while ym in pink_map:
        p = pink_map[ym]
        gold, silver = p["gold"], p["silver"]
        if gold is None or silver is None:
            skipped.append("%s: Pink Sheet thieu gia" % ym)
            break
        t10 = month_value("GS10", ym, key)
        ff = month_value("FEDFUNDS", ym, key)
        cs = month_avg_daily("T10Y2Y", ym, key)
        cpi = cpi_yoy(ym, key)
        if None in (t10, ff, cs, cpi):
            skipped.append("%s: FRED chua co du du lieu (t10=%s ff=%s cs=%s cpi=%s)" % (ym, t10, ff, cs, cpi))
            break
        ry = round(t10 - cpi, 1)
        g_val = round(gold)
        s_val = round(silver, 1)
        t10 = round(t10, 2)
        ff = round(ff, 2)
        cs = round(cs, 2)
        cpi = round(cpi, 1)
        prev_g = HX["g"][-1]
        prev_s = HX["s"][-1]
        if prev_g and abs(g_val - prev_g) / prev_g > 0.15:
            skipped.append("%s: gia vang %s lech >15%% so voi thang truoc (%s), dung lai cho kiem tra tay" % (ym, g_val, prev_g))
            break
        if prev_s and abs(s_val - prev_s) / prev_s > 0.15:
            skipped.append("%s: gia bac %s lech >15%% so voi thang truoc (%s), dung lai cho kiem tra tay" % (ym, s_val, prev_s))
            break
        HX["g"].append(g_val)
        HX["s"].append(s_val)
        HX["t10"].append(t10)
        HX["cs"].append(cs)
        HX["ff"].append(ff)
        HX["cpi"].append(cpi)
        HX["ry"].append(ry)
        HX["n"] += 1
        G.append(g_val)
        S.append(s_val)
        added.append({"m": ym, "g": g_val, "s": s_val, "t10": t10, "ff": ff, "cs": cs, "cpi": cpi, "ry": ry})
        ym = add_months(ym, 1)

    if not added:
        msg = "chua co thang moi de bo sung (HX dang den %s)" % last_ym
        if skipped:
            msg += "; " + "; ".join(skipped)
        return msg

    # --- su kien Fed: quet tu ngay cua phan tu E cuoi cung (hoac 400 ngay truoc neu E rong) ---
    since = E[-1][0] if E else (datetime.date.today() - datetime.timedelta(days=400)).isoformat()
    try:
        new_events = fred_events(key, since)
    except Exception as e:  # noqa
        new_events = []
        skipped.append("fred_events loi: %s" % e)
    existing_dates = {e[0] for e in E}
    for ev in new_events:
        if ev[0] not in existing_dates:
            E.append(ev)
            existing_dates.add(ev[0])

    # --- ghi lai vao raw content, thay dung 1 lan moi vi tri (tu cuoi ve dau de khong lech offset) ---
    new_hx_text = json.dumps(HX, ensure_ascii=False, separators=(",", ":"))
    new_g_text = json.dumps(G, ensure_ascii=False, separators=(",", ":"))
    new_s_text = json.dumps(S, ensure_ascii=False, separators=(",", ":"))
    new_e_text = json.dumps(E, ensure_ascii=False, separators=(",", ":"))

    replacements = sorted(
        [(hx_s, hx_e, new_hx_text), (g_s, g_e, new_g_text), (s_s, s_e, new_s_text), (e_s, e_e, new_e_text)],
        key=lambda x: x[0], reverse=True,
    )
    new_raw = raw
    for s_, e_, txt in replacements:
        if re.search(r"&(?!amp;|lt;|gt;)", txt):
            raise RuntimeError("Du lieu moi co ky tu & tho, dung lai truoc khi ghi")
        new_raw = new_raw[:s_] + txt + new_raw[e_:]

    back = wp.set_raw(PAGE_ID, new_raw)
    if new_hx_text not in back or new_e_text not in back:
        raise RuntimeError("Doc lai trang %d sau khi ghi khong thay du lieu moi" % PAGE_ID)

    with open("data/fred_monthly.json", "w", encoding="utf-8") as f:
        json.dump({"asof": datetime.date.today().isoformat(), "added": added,
                    "new_events": [e for e in E if e[0] not in existing_dates or True][-len(new_events):],
                    "skipped": skipped}, f, ensure_ascii=False, indent=1)

    msg = "da them %d thang (%s..%s), %d su kien Fed moi" % (
        len(added), added[0]["m"], added[-1]["m"], len(new_events))
    if skipped:
        msg += "; con cho: " + "; ".join(skipped)
    return msg
