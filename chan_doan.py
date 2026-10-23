"""Chan doan (chay tay): kiem tra cu phap PHP cua mu-plugin trong thu muc wp/ va trang thai plugin WordPress."""
import glob
import subprocess
import requests
import wp


def run():
    out = []
    for f in sorted(glob.glob("wp/*.php")):
        r = subprocess.run(["php", "-l", f], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("Loi cu phap PHP %s: %s" % (f, (r.stdout + r.stderr).strip()[:300]))
        out.append("%s: cu phap OK" % f)
    if wp.enabled():
        base = wp._cfg()[0]
        r = wp._sess().get(base + "/index.php/wp-json/wp/v2/plugins", params={"_fields": "plugin,status,version"}, timeout=60)
        if r.status_code == 200:
            out.append("plugin: " + "; ".join("%s %s %s" % (p["plugin"].split("/")[0], p["version"], p["status"]) for p in r.json()))
        else:
            out.append("khong doc duoc danh sach plugin (%d)" % r.status_code)
    return " | ".join(out)
