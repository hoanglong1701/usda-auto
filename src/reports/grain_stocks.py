"""Grain Stocks (NASS) - tồn kho ngũ cốc quý của Mỹ.

Ra vào ngày làm việc cuối của tháng 3, 6, 9 và đầu tháng 1 (12:00 ET).
"""
from datetime import datetime, timezone

import nass

NAME = "grain_stocks"
TITLE = "Tồn kho ngũ cốc Mỹ (Grain Stocks)"

COMMODITIES = {
    "CORN": "Ngô",
    "SOYBEANS": "Đậu tương",
    "WHEAT": "Lúa mì",
    "SORGHUM": "Lúa miến",
    "BARLEY": "Đại mạch",
    "OATS": "Yến mạch",
}
MONTHS = {"FIRST OF JAN": 1, "FIRST OF MAR": 3, "FIRST OF JUN": 6,
          "FIRST OF SEP": 9, "FIRST OF DEC": 12}
REF_VN = {1: "1/1", 3: "1/3", 6: "1/6", 9: "1/9", 12: "1/12"}


def _keep(r):
    if r.get("unit_desc") != "BU" or r.get("domain_desc") != "TOTAL":
        return False
    if r.get("reference_period_desc") not in MONTHS:
        return False
    for f in ("class_desc", "util_practice_desc", "prodn_practice_desc"):
        v = r.get(f)
        if v and not v.startswith("ALL"):
            return False
    return True


def _label(short_desc, vn):
    if "ON FARM" in short_desc:
        return f"{vn} - trong trang trại"
    if "OFF FARM" in short_desc:
        return f"{vn} - ngoài trang trại"
    return f"{vn} - tổng tồn kho"


def fetch(now=None):
    year = (now or datetime.now(timezone.utc)).year
    out, latest_key = [], None
    for com, vn in COMMODITIES.items():
        rows = nass.query(
            source_desc="SURVEY", commodity_desc=com, statisticcat_desc="STOCKS",
            agg_level_desc="NATIONAL", year__GE=year - 2,
        )
        series = {}
        for r in rows:
            if not _keep(r):
                continue
            v = nass.num(r["Value"])
            if v is None:
                continue
            key = (int(r["year"]), MONTHS[r["reference_period_desc"]])
            series.setdefault(r["short_desc"], {})[key] = v
        for sd, pts in series.items():
            keys = sorted(pts)
            cur = keys[-1]
            prev_q = keys[-2] if len(keys) > 1 else None
            prev_y = (cur[0] - 1, cur[1])
            val = pts[cur]
            def pct(a, b):
                return None if not b else (a / b - 1) * 100
            out.append({
                "label": _label(sd, vn),
                "short_desc": sd,
                "period": f"{REF_VN[cur[1]]}/{cur[0]}",
                "value_mbu": val / 1e6,
                "prev_q_mbu": pts[prev_q] / 1e6 if prev_q else None,
                "prev_y_mbu": pts.get(prev_y, None) and pts[prev_y] / 1e6,
                "qoq_pct": pct(val, pts[prev_q]) if prev_q else None,
                "yoy_pct": pct(val, pts[prev_y]) if prev_y in pts else None,
                "_key": cur,
            })
            latest_key = max(latest_key, cur) if latest_key else cur
    if not out:
        raise RuntimeError("Grain Stocks: API không trả dữ liệu (kiểm tra tên trường).")
    out.sort(key=lambda x: (x["label"].split(" - ")[0], x["label"]))
    for o in out:
        o.pop("_key")
    return {
        "report": NAME,
        "title": TITLE,
        "release_id": f"{latest_key[0]}-{latest_key[1]:02d}",
        "period": f"{REF_VN[latest_key[1]]}/{latest_key[0]}",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "unit": "triệu bushel",
        "rows": [o for o in out if f"{REF_VN[latest_key[1]]}/{latest_key[0]}" == o["period"]],
    }
