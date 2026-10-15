"""Goi 'do nguon': thu thap cac nguon du lieu KHONG can trinh duyet (gat qua headless tren GitHub
Actions), ghi vao data/probe.json. KHONG ghi len WordPress - day la du lieu tho de cac tac vu Claude
(lich kinh te trang 176, cong cu dinh luong trang 478, Pink Sheet/Fed trang 111, theo doi tuoi du lieu)
doc lai va xu ly tiep, khong tu dong dang web.

Nguon da thu (fetch duoc thang bang requests, khong can JS):
 - FRED CSV: loi suat 10Y/2Y, Fed Funds, CPI, USD index, breakeven 10Y
 - Yahoo chart: GC=F (vang), SI=F (bac) - gia futures tuan gan nhat
 - CFTC f_disagg.txt: vi the COT vang/bac (Disaggregated Futures Only Report)
 - World Bank Pink Sheet (CMO-Historical-Data-Monthly.xlsx): gia vang/bac thang gan nhat

Nguon CHUA thu duoc tu GitHub (ghi ro trong "notes", van can tac vu Claude co trinh duyet):
 - Lich kinh te ForexFactory/TradingView: can JS render, khong co API cong khai on dinh
 - IMF DataMapper: IMF chan dia chi IP cua GitHub Actions (403), da biet tu truoc (xem orgs.py)
 - NY Fed / BLS: chua tim duoc endpoint CSV cong khai on dinh, de danh cho ban sau
"""
import io
import re
import csv
import json
import datetime
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

FRED_SERIES = {
    "DGS10": "Loi suat trai phieu My 10 nam",
    "DGS2": "Loi suat trai phieu My 2 nam",
    "FEDFUNDS": "Lai suat Fed Funds hieu dung",
    "DTWEXBGS": "Chi so USD (broad, Fed)",
    "T10YIE": "Breakeven lam phat 10 nam",
    "CPIAUCSL": "CPI My (chua dieu chinh mua vu)",
}

YAHOO_SYMBOLS = {"GC=F": "Vang futures (COMEX)", "SI=F": "Bac futures (COMEX)"}

CFTC_URLS = [
    # f_disagg.txt = Disaggregated report: CHI co nong san/nang luong, KHONG co vang/bac (da kiem chung).
    # deacot.txt = Legacy report (Futures Only): co TAT CA hang hoa, bao gom vang/bac tren COMEX.
    ("legacy", "https://www.cftc.gov/dea/newcot/deacot.txt"),
    ("disaggregated", "https://www.cftc.gov/dea/newcot/f_disagg.txt"),
]
WB_COMMODITY_PAGE = "https://www.worldbank.org/en/research/commodity-markets"


def _get(url, **kw):
    kw.setdefault("timeout", 60)
    kw.setdefault("headers", {"User-Agent": UA})
    r = requests.get(url, **kw)
    r.raise_for_status()
    return r


def fred_series(series_id, n_last=60):
    try:
        r = _get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": series_id}, timeout=90)
    except requests.exceptions.ReadTimeout:
        r = _get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": series_id}, timeout=90)  # 1 lan thu lai
    rows = list(csv.reader(io.StringIO(r.text)))
    rows = rows[1:]  # bo header "DATE,<id>"
    pts = []
    for d, v in rows:
        if v in (".", ""):
            continue
        pts.append([d, float(v)])
    if not pts:
        raise RuntimeError("FRED %s: khong co diem du lieu hop le" % series_id)
    return {"latest_date": pts[-1][0], "latest_value": pts[-1][1], "series": pts[-n_last:]}


def yahoo_quote(symbol):
    r = _get(
        "https://query1.finance.yahoo.com/v8/finance/chart/%s" % symbol,
        params={"range": "5d", "interval": "1d"},
    )
    j = r.json()
    res = j["chart"]["result"][0]
    ts = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    pts = [[datetime.datetime.utcfromtimestamp(t).date().isoformat(), c]
           for t, c in zip(ts, closes) if c is not None]
    if not pts:
        raise RuntimeError("Yahoo %s: khong co diem dong cua" % symbol)
    return {"latest_date": pts[-1][0], "latest_close": pts[-1][1], "series": pts}


def cftc_disagg():
    out = {}
    fetch_errors = []
    found_in = None
    lines = None
    for label, url in CFTC_URLS:
        try:
            r = _get(url)
            cand_lines = r.text.splitlines()
        except Exception as e:  # noqa
            fetch_errors.append("%s (%s): %s" % (label, url, e))
            continue
        has_gold = any(ln.upper().startswith("GOLD") or "- GOLD" in ln.upper()[:60] for ln in cand_lines[:2000])
        if has_gold:
            found_in = label
            lines = cand_lines
            break
        if lines is None:
            lines = cand_lines  # giu ban cuoi cung de bao loi neu khong co ban nao co GOLD
    if lines is None:
        out["gold"] = out["silver"] = {"error": "khong tai duoc file CFTC nao: %s" % "; ".join(fetch_errors)}
        return out
    for key, pat in (("gold", "GOLD"), ("silver", "SILVER")):
        row = next((ln for ln in lines if ln.upper().startswith(pat) or ("- " + pat) in ln.upper()[:60]), None)
        if not row:
            out[key] = {"error": "khong tim thay dong %s trong file CFTC da thu (%s)" % (
                pat, found_in or "khong file nao co GOLD")}
            continue
        cols = [c.strip() for c in row.split(",")]
        out[key] = {"source_report": found_in, "raw_header": cols[0], "n_cols": len(cols), "raw_cols_tail": cols[-12:]}
    out["_note"] = ("Dong raw tu bao cao CFTC (%s), CHUA parse thanh vi the rong cu the - " % (found_in or "?") +
                     "tac vu Claude doc cot theo dung vi tri (dinh dang CFTC co the doi) roi tinh CG/CS.")
    return out


def wb_pink_sheet_url():
    """Tim link xlsx moi nhat tren trang Commodity Markets (hash trong URL doi hang thang)."""
    r = _get(WB_COMMODITY_PAGE)
    m = re.search(r'https://thedocs\.worldbank\.org/[^"\']+CMO-Historical-Data-Monthly\.xlsx', r.text)
    if not m:
        raise RuntimeError("Khong tim thay link CMO-Historical-Data-Monthly.xlsx tren trang Commodity Markets")
    return m.group(0)


def wb_pink_sheet():
    url = wb_pink_sheet_url()
    r = _get(url)
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(r.content), data_only=True, read_only=True)
    if "Monthly Prices" not in wb.sheetnames:
        raise RuntimeError("Pink Sheet: khong thay sheet 'Monthly Prices'")
    ws = wb["Monthly Prices"]
    rows = list(ws.iter_rows(values_only=True))
    header_row_idx = None
    for i, row in enumerate(rows[:10]):
        if row and any(isinstance(c, str) and "gold" in c.lower() for c in row):
            header_row_idx = i
            break
    if header_row_idx is None:
        raise RuntimeError("Pink Sheet: khong tim thay dong tieu de co 'Gold'")
    header = rows[header_row_idx]
    gold_col = next(i for i, c in enumerate(header) if isinstance(c, str) and c.strip().lower().startswith("gold"))
    silver_col = next(i for i, c in enumerate(header) if isinstance(c, str) and c.strip().lower().startswith("silver"))
    data_rows = [row for row in rows[header_row_idx + 1:] if row and row[0] and str(row[0]).strip()]
    last = data_rows[-1]
    return {
        "latest_month_label": str(last[0]).strip(),
        "gold_usd_per_toz": last[gold_col],
        "silver_usd_per_toz": last[silver_col],
    }


def run():
    out = {"asof": datetime.date.today().isoformat(), "errors": [], "notes": [
        "Lich kinh te ForexFactory/TradingView: can trinh duyet/JS, khong fetch duoc tu GitHub Actions.",
        "IMF DataMapper: IMF chan IP GitHub Actions (403) - van can tac vu Claude hang quy.",
        "NY Fed / BLS: chua co nguon CSV cong khai on dinh, de ban sau.",
    ]}

    out["fred"] = {}
    for sid, label in FRED_SERIES.items():
        try:
            out["fred"][sid] = dict(fred_series(sid), label=label)
        except Exception as e:  # noqa
            out["fred"][sid] = {"label": label, "error": "%s: %s" % (type(e).__name__, e)}
            out["errors"].append("fred/%s: %s" % (sid, e))

    out["yahoo"] = {}
    for sym, label in YAHOO_SYMBOLS.items():
        try:
            out["yahoo"][sym] = dict(yahoo_quote(sym), label=label)
        except Exception as e:  # noqa
            out["yahoo"][sym] = {"label": label, "error": "%s: %s" % (type(e).__name__, e)}
            out["errors"].append("yahoo/%s: %s" % (sym, e))

    try:
        out["cftc_disagg"] = cftc_disagg()
    except Exception as e:  # noqa
        out["cftc_disagg"] = {"error": "%s: %s" % (type(e).__name__, e)}
        out["errors"].append("cftc_disagg: %s" % e)

    try:
        out["worldbank_pink_sheet"] = wb_pink_sheet()
    except Exception as e:  # noqa
        out["worldbank_pink_sheet"] = {"error": "%s: %s" % (type(e).__name__, e)}
        out["errors"].append("worldbank_pink_sheet: %s" % e)

    with open("data/probe.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    n_err = len(out["errors"])
    if n_err:
        return "ghi data/probe.json, %d nguon loi: %s" % (n_err, "; ".join(out["errors"][:3]))
    return "ghi data/probe.json, tat ca nguon OK"
