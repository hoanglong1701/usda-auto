"""Dựng khối HTML để chèn vào trang WordPress."""
from datetime import datetime, timedelta, timezone

DISCLAIMER = ("Nội dung tham khảo, không phải khuyến nghị đầu tư. Giao dịch hàng hóa phái sinh "
              "có rủi ro cao, nhà đầu tư tự chịu trách nhiệm quyết định của mình.")

CSS = """<style>
.usda{font-family:inherit;margin:0 0 28px}
.usda h3{margin:0 0 4px}
.usda .meta{color:#666;font-size:.88em;margin-bottom:10px}
.usda table{width:100%;border-collapse:collapse;font-size:.95em}
.usda th,.usda td{padding:7px 9px;border-bottom:1px solid #e3e3dc;text-align:right}
.usda th:first-child,.usda td:first-child{text-align:left}
.usda th{background:#f3f1e8;font-weight:600}
.usda .up{color:#2e7d32}.usda .down{color:#c62828}
.usda .note{color:#777;font-size:.8em;margin-top:8px}
</style>"""


def fmt(v, d=1):
    return "–" if v is None else f"{v:,.{d}f}"


def chg(v):
    if v is None:
        return "–"
    cls = "up" if v > 0 else "down" if v < 0 else ""
    return f'<span class="{cls}">{v:+.1f}%</span>'


def vn_time(iso):
    t = datetime.fromisoformat(iso).astimezone(timezone(timedelta(hours=7)))
    return t.strftime("%H:%M %d/%m/%Y (giờ Việt Nam)")


def header(d):
    return (f'<div class="usda"><h3>{d["title"]}</h3>'
            f'<div class="meta">Kỳ số liệu: {d["period"]} · Cập nhật: {vn_time(d["updated_at"])} · Nguồn: USDA NASS</div>')


def grain_stocks(d):
    h = header(d) + "<table><tr><th>Mặt hàng</th><th>Tồn kho (triệu bushel)</th>" \
        "<th>So với quý trước</th><th>So với cùng kỳ năm trước</th></tr>"
    for r in d["rows"]:
        h += (f'<tr><td>{r["label"]}</td><td>{fmt(r["value_mbu"])}</td>'
              f'<td>{chg(r["qoq_pct"])}</td><td>{chg(r["yoy_pct"])}</td></tr>')
    return h + f'</table><div class="note">{DISCLAIMER}</div></div>'


def crop_progress(d):
    h = header(d) + "<table><tr><th>Cây trồng / chỉ tiêu</th><th>Tuần này (%)</th>" \
        "<th>Tuần trước (%)</th><th>Cùng kỳ năm trước (%)</th><th>TB 5 năm (%)</th></tr>"
    for r in d["rows"]:
        h += (f'<tr><td>{r["commodity"]} – {r["item"]}</td><td>{fmt(r["this_week"], 0)}</td>'
              f'<td>{fmt(r["last_week"], 0)}</td><td>{fmt(r["last_year"], 0)}</td>'
              f'<td>{fmt(r["avg5"], 0)}</td></tr>')
    return h + f'</table><div class="note">{DISCLAIMER}</div></div>'


RENDERERS = {"grain_stocks": grain_stocks, "crop_progress": crop_progress}


def render(d):
    return CSS + RENDERERS[d["report"]](d)
