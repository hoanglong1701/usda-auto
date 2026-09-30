"""Client cho NASS Quick Stats API."""
import os
import time

import requests

BASE = "https://quickstats.nass.usda.gov/api/api_GET/"


def query(**params):
    """Gọi Quick Stats, trả về list dòng dữ liệu ([] nếu không có dữ liệu)."""
    p = {"key": os.environ["NASS_API_KEY"], "format": "JSON", **params}
    last = None
    for i in range(3):
        try:
            r = requests.get(BASE, params=p, timeout=60)
        except requests.RequestException as e:  # lỗi mạng -> thử lại
            last = e
            time.sleep(5 * (i + 1))
            continue
        if r.status_code == 200:
            return r.json().get("data", [])
        if r.status_code == 400 and "no data" in r.text.lower():
            return []
        last = RuntimeError(f"NASS HTTP {r.status_code}: {r.text[:300]}")
        if r.status_code in (400, 401, 403):
            break  # lỗi tham số/key: không thử lại
        time.sleep(5 * (i + 1))
    raise last


def num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, TypeError):
        return None
