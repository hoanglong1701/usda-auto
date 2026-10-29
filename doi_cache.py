"""Chuyen plugin cache (chay tay): tat Cache Enabler, bat LiteSpeed Cache (dung loai may chu LiteSpeed cua host).
Lam qua REST /wp/v2/plugins. Neu LiteSpeed Cache khong bat duoc thi bat lai Cache Enabler.
Dao nguoc: job doi_cache_lai.
"""
import time
import requests
import wp

CE = "cache-enabler/cache-enabler"
LS = "litespeed-cache/litespeed-cache"


def _set(s, base, plugin, status):
    r = s.post("%s/%s" % (base, plugin), json={"status": status}, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError("%s -> %s loi %d: %s" % (plugin, status, r.status_code, r.text[:200]))
    return r.json().get("status")


def _check():
    u = "https://giaodichhanghoa247.vn%s/kim-loai-quy/" % wp.tien_to()
    h = {"User-Agent": wp.UA, "Accept": "text/html"}
    out = []
    for _ in range(3):
        r = requests.get(u, headers=h, timeout=60)
        out.append((r.status_code, r.headers.get("X-LiteSpeed-Cache", "")))
        time.sleep(2)
    return out


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    s = wp._sess()
    base = wp._cfg()[0] + "/index.php/wp-json/wp/v2/plugins"
    a = _set(s, base, CE, "inactive")
    try:
        b = _set(s, base, LS, "active")
    except Exception:
        _set(s, base, CE, "active")
        raise
    chk = _check()
    if any(st != 200 for st, _ in chk):
        _set(s, base, LS, "inactive")
        _set(s, base, CE, "active")
        raise RuntimeError("Trang loi sau khi doi cache %s, da quay lai Cache Enabler" % chk)
    return "cache-enabler %s, litespeed-cache %s; kiem tra %s" % (a, b, chk)


def run_back():
    s = wp._sess()
    base = wp._cfg()[0] + "/index.php/wp-json/wp/v2/plugins"
    return "litespeed-cache %s, cache-enabler %s" % (_set(s, base, LS, "inactive"), _set(s, base, CE, "active"))
