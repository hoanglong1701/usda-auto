"""Crop Progress (NASS) - tiến độ và tình trạng cây trồng Mỹ (thứ Hai hằng tuần, 4h chiều ET)."""
from datetime import datetime, timezone

import nass

NAME = "crop_progress"
TITLE = "Tiến độ & tình trạng cây trồng Mỹ (Crop Progress)"

COMMODITIES = {"CORN": "Ngô", "SOYBEANS": "Đậu tương", "WHEAT": "Lúa mì",
               "COTTON": "Bông", "SORGHUM": "Lúa miến", "RICE": "Lúa gạo"}
UNIT_VN = {
    "PCT PLANTED": "Đã gieo", "PCT EMERGED": "Đã nảy mầm", "PCT SILKING": "Phun râu",
    "PCT DOUGH": "Giai đoạn dough", "PCT DENTED": "Hạt lõm", "PCT MATURE": "Chín",
    "PCT HARVESTED": "Đã thu hoạch", "PCT BLOOMING": "Ra hoa", "PCT SETTING PODS": "Đậu quả",
    "PCT DROPPING LEAVES": "Rụng lá", "PCT SQUARING": "Hình thành nụ",
    "PCT SETTING BOLLS": "Đậu quả bông", "PCT BOLLS OPENING": "Nở quả bông",
    "PCT HEADED": "Trổ bông", "PCT COLORING": "Chuyển màu",
    "PCT EXCELLENT": "Xuất sắc", "PCT GOOD": "Tốt", "PCT FAIR": "Khá",
    "PCT POOR": "Kém", "PCT VERY POOR": "Rất kém",
}


def _unit(short_desc):
    if "MEASURED IN " in short_desc:
        return short_desc.split("MEASURED IN ")[-1].strip()
    return short_desc


def fetch(now=None):
    year = (now or datetime.now(timezone.utc)).year
    rows_out, latest_we = [], None
    for com, vn in COMMODITIES.items():
        data = []
        for cat in ("PROGRESS", "CONDITION"):
            data += nass.query(
                source_desc="SURVEY", commodity_desc=com, statisticcat_desc=cat,
                agg_level_desc="NATIONAL", freq_desc="WEEKLY", year__GE=year - 5,
            )
        series = {}  # (class, short_desc) -> {(year, week): (week_ending, value)}
        for r in data:
            sd = r["short_desc"]
            if "AVG" in sd or "PREVIOUS" in sd:
                continue
            v = nass.num(r["Value"])
            if v is None:
                continue
            wk = r["reference_period_desc"]  # "WEEK #39"
            series.setdefault((r.get("class_desc", ""), sd), {})[(int(r["year"]), wk)] = (r["week_ending"], v)
        ge = {}  # tính tổng Tốt+Xuất sắc
        for (cls, sd), pts in series.items():
            cur = [k for k in pts if k[0] == year]
            if not cur:
                continue
            k = max(cur, key=lambda x: pts[x][0])
            we, val = pts[k]
            wk = k[1]
            wknum = int(wk.split("#")[-1])
            prev_wk = f"WEEK #{wknum - 1:02d}"
            def get(y, w):
                for kk in (w, f"WEEK #{int(w.split('#')[-1])}", f"WEEK #{int(w.split('#')[-1]):02d}"):
                    if (y, kk) in pts:
                        return pts[(y, kk)][1]
                return None
            last_week = get(year, prev_wk)
            last_year = get(year - 1, wk)
            hist = [get(y, wk) for y in range(year - 5, year)]
            hist = [h for h in hist if h is not None]
            avg5 = sum(hist) / len(hist) if hist else None
            unit = _unit(sd)
            cls_txt = "" if cls.startswith("ALL") or not cls else f" ({cls.title()})"
            row = {
                "commodity": vn + cls_txt, "item": UNIT_VN.get(unit, unit.title()),
                "unit": unit, "week_ending": we, "this_week": val, "last_week": last_week,
                "last_year": last_year, "avg5": avg5,
            }
            rows_out.append(row)
            latest_we = max(latest_we, we) if latest_we else we
            if unit in ("PCT GOOD", "PCT EXCELLENT"):
                g = ge.setdefault((vn + cls_txt), {})
                for f in ("this_week", "last_week", "last_year", "avg5"):
                    g[f] = (g.get(f) or 0) + (row[f] or 0) if row[f] is not None else g.get(f)
        for name, g in ge.items():
            rows_out.append({"commodity": name, "item": "Tốt + Xuất sắc (G/E)", "unit": "GE",
                             "week_ending": latest_we, **g})
    if not rows_out:
        raise RuntimeError("Crop Progress: API không trả dữ liệu (ngoài mùa vụ hoặc sai tên trường).")
    rows_out = [r for r in rows_out if r["week_ending"] == latest_we]
    return {
        "report": NAME, "title": TITLE, "release_id": latest_we,
        "period": f"tuần kết thúc {latest_we}",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "unit": "% diện tích", "rows": rows_out,
    }
