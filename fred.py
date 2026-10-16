"""Test + thu thap du lieu tu FRED API chinh thuc (api.stlouisfed.org), dung FRED_API_KEY.
Khac voi fredgraph.csv (fred.stlouisfed.org) da bi mang GitHub Actions chan hoan toan truoc day.
"""
import os
import json
import urllib.request
import urllib.error

API = "https://api.stlouisfed.org/fred/series/observations"
SERIES = {
    "DFEDTARU": "Fed funds target rate (can tren)",
    "FEDFUNDS": "Fed funds effective rate (thang)",
    "GS10": "Loi suat TPCP My 10 nam (thang)",
    "DFII10": "Loi suat thuc TIPS 10 nam",
    "CPIAUCSL": "CPI (chua dieu chinh mua)",
    "T10Y2Y": "Chenh lech loi suat 10nam-2nam",
}


def fetch_series(series_id, key, limit=5):
    url = (API + "?series_id=%s&api_key=%s&file_type=json&sort_order=desc&limit=%d"
           % (series_id, key, limit))
    req = urllib.request.Request(url, headers={"User-Agent": "gdhh247-probe/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))
    obs = data.get("observations", [])
    return [[o["date"], o["value"]] for o in obs]


def run():
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise RuntimeError("Thieu secret FRED_API_KEY")
    out = {"ok": {}, "errors": {}}
    for sid, label in SERIES.items():
        try:
            out["ok"][sid] = {"label": label, "latest": fetch_series(sid, key, limit=3)}
        except urllib.error.HTTPError as e:
            out["errors"][sid] = "HTTP %s: %s" % (e.code, e.read()[:300].decode("utf-8", "ignore"))
        except Exception as e:  # noqa
            out["errors"][sid] = "%s: %s" % (type(e).__name__, e)
    os.makedirs("data", exist_ok=True)
    with open("data/fred_test.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    n_ok = len(out["ok"])
    n_err = len(out["errors"])
    if n_ok == 0:
        raise RuntimeError("FRED API khong goi duoc tu runner nay: %s" % out["errors"])
    return "FRED API: %d/%d chuoi lay duoc" % (n_ok, len(SERIES))
