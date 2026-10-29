"""Thue nhap khau MFN cua cac nuoc mua lon theo WTO Timeseries API -> khoa "mfn" cua trang du lieu 1791.

Khoa WTO_API_KEY (GitHub Secrets, anh Long dang ky mien phi tai apiportal.wto.org).
Che do thu(): do danh sach chi tieu thue quan va thu goi du lieu theo ma HS, chi in ra, khong ghi.
"""
import os
import json
import requests
import wp

BASE = "https://api.wto.org/timeseries/v1"
PAGE = 1791
# ten tren web -> ma nuoc WTO
NUOC = {"Trung Quốc": "156", "EU": "918", "Ấn Độ": "356", "Nhật Bản": "392", "Hàn Quốc": "410",
        "Indonesia": "360", "Việt Nam": "704", "Mexico": "484"}
# san pham tren web -> ma HS 6 so dai dien
HS = {"dau": "120190", "ngo": "100590", "mi": "100199", "kho": "230400", "dd": "150710"}


def goi(path, **params):
    key = os.environ.get("WTO_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Chua co WTO_API_KEY")
    r = requests.get(BASE + path, params=params, timeout=90,
                     headers={"Ocp-Apim-Subscription-Key": key, "User-Agent": wp.UA})
    if r.status_code >= 400:
        raise RuntimeError("WTO %s tra %d: %s" % (path, r.status_code, r.text[:200].replace("\n", " ")))
    return r.json()


def thu():
    ds = goi("/indicators", i="all", lang=1)
    out = []
    for x in ds:
        ten = (x.get("name") or "") + " " + (x.get("code") or "")
        if any(k in ten.lower() for k in ("duty", "duties", "tariff", "mfn")):
            out.append(x)
    print("Tong %d chi tieu, %d lien quan thue" % (len(ds), len(out)))
    for x in out:
        print(json.dumps({k: x.get(k) for k in ("code", "name", "productClassification", "frequencyCode",
                                                "startYear", "endYear", "numberReporters")}, ensure_ascii=False))
    thanh_cong = []
    for x in out:
        pcl = str(x.get("productClassification") or "")
        if "HS" not in pcl.upper():
            continue
        for pc in ("120190", "1201"):
            try:
                d = goi("/data", i=x["code"], r="156", p="default", ps="2020-2026", pc=pc, fmt="json", mode="full", lang=1, max=20)
            except Exception as e:  # noqa
                print("  %s pc=%s: %s" % (x["code"], pc, str(e)[:160]))
                continue
            rows = d.get("Dataset") or d.get("dataset") or d
            print("  %s pc=%s: %s" % (x["code"], pc, json.dumps(rows, ensure_ascii=False)[:600]))
            if rows:
                thanh_cong.append(x["code"])
                break
    return "da do %d chi tieu thue, goi duoc du lieu HS: %s" % (len(out), ", ".join(thanh_cong) or "khong")
