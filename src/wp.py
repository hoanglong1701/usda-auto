"""Cập nhật khối nội dung trong một trang WordPress qua REST API."""
import os

import requests


def enabled():
    return all(os.environ.get(k) for k in ("WP_URL", "WP_USER", "WP_APP_PASSWORD", "WP_PAGE_ID"))


def publish(key, html):
    if not enabled():
        print(f"[wp] chưa cấu hình WordPress -> bỏ qua đăng '{key}'")
        return False
    base = os.environ["WP_URL"].rstrip("/")
    auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])
    url = f"{base}/wp-json/wp/v2/pages/{os.environ['WP_PAGE_ID']}"
    r = requests.get(url, params={"context": "edit"}, auth=auth, timeout=30)
    r.raise_for_status()
    raw = r.json()["content"]["raw"]
    start, end = f"<!-- USDA:{key}:start -->", f"<!-- USDA:{key}:end -->"
    block = f"{start}\n<!-- wp:html -->\n{html}\n<!-- /wp:html -->\n{end}"
    if start in raw and end in raw:
        new = raw[:raw.index(start)] + block + raw[raw.index(end) + len(end):]
    else:
        new = raw + "\n\n" + block
    r = requests.post(url, json={"content": new}, auth=auth, timeout=30)
    r.raise_for_status()
    print(f"[wp] đã cập nhật '{key}' lên trang {os.environ['WP_PAGE_ID']}")
    return True
