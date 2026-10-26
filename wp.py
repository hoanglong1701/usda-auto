"""Doc/ghi trang du lieu an (#gd-data) tren WordPress qua REST + Application Password."""
import os
import re
import json
import datetime
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PRE = re.compile(r'<pre id="gd-data"[^>]*>(.*?)</pre>', re.S)


def _cfg():
    base = os.environ.get("WP_URL", "").strip().rstrip("/")
    user = os.environ.get("WP_USER", "").strip()
    pw = os.environ.get("WP_APP_PASSWORD", "").strip()
    return base, user, pw


def enabled():
    b, u, p = _cfg()
    return bool(b and u and p)


def _url(pid):
    return _cfg()[0] + "/index.php/wp-json/wp/v2/pages/%d" % pid


def _sess():
    _, u, p = _cfg()
    s = requests.Session()
    s.auth = (u, p)
    s.headers.update({"User-Agent": UA, "Accept": "application/json"})
    return s


def unesc(t):
    return t.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load(pid):
    """Tra ve dict trong #gd-data cua trang pid."""
    r = _sess().get(_url(pid), params={"context": "edit", "_fields": "content.raw"}, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError("WordPress tra %d khi doc trang %d: %s" % (r.status_code, pid, r.text[:200].replace("\n", " ")))
    raw = r.json()["content"]["raw"]
    m = PRE.search(raw)
    if not m:
        raise RuntimeError("Trang %d khong co #gd-data" % pid)
    return json.loads(unesc(m.group(1)))


def save(pid, obj):
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    content = ('<!-- wp:html -->\n<pre id="gd-data" style="display:none">'
               + esc(s) + '</pre>\n<!-- /wp:html -->')
    r = _sess().post(_url(pid), json={"content": content}, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError("WordPress tra %d khi ghi trang %d: %s" % (r.status_code, pid, r.text[:200].replace("\n", " ")))
    # doc lai de chac chan ghi dung
    back = load(pid)
    if json.dumps(back, sort_keys=True) != json.dumps(obj, sort_keys=True):
        raise RuntimeError("Doc lai trang %d khong khop du lieu vua ghi" % pid)


def get_raw(pid):
    """Tra ve toan bo content.raw cua trang pid (khong phai trang gd-data)."""
    r = _sess().get(_url(pid), params={"context": "edit", "_fields": "content.raw"}, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError("WordPress tra %d khi doc trang %d: %s" % (r.status_code, pid, r.text[:200].replace("\n", " ")))
    return r.json()["content"]["raw"]


def backup_raw(pid, raw):
    """Luu noi dung cu cua trang vao data/backup/trang<id>_<ngay>.html truoc khi ghi de."""
    os.makedirs(os.path.join("data", "backup"), exist_ok=True)
    p = os.path.join("data", "backup", "trang%d_%s.html" % (pid, datetime.date.today().isoformat()))
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as f:
            f.write(raw)


def set_raw(pid, content):
    """Ghi de toan bo content cua trang pid. Tra ve noi dung doc lai de nguoi goi
    tu kiem tra (WordPress co the chuan hoa nhe whitespace nen khong so sanh byte-for-byte)."""
    r = _sess().post(_url(pid), json={"content": content}, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError("WordPress tra %d khi ghi trang %d: %s" % (r.status_code, pid, r.text[:200].replace("\n", " ")))
    return get_raw(pid)


def update_key(pid, key, value):
    """Chi thay mot khoa cua JSON, giu nguyen cac khoa con lai, dat asof = hom nay."""
    obj = load(pid)
    obj[key] = value
    obj["asof"] = datetime.date.today().isoformat()
    save(pid, obj)
