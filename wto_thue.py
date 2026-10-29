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


# "HS MFN - Simple average ad valorem duty", theo ma HS 6 so, hang nam
CHI_TIEU = "HS_A_0010"


def lay_nuoc(ma):
    """{ma HS: (thue %, nam)} cua nam moi nhat co so lieu."""
    d = goi("/data", i=CHI_TIEU, r=ma, ps="2019-2026", pc=",".join(HS.values()), fmt="json", mode="full",
            lang=1, max=500)
    rows = d.get("Dataset") or d.get("dataset") or []
    out = {}
    for x in rows:
        pc = str(x.get("ProductOrSectorCode") or x.get("productOrSectorCode") or "")
        nam = int(x.get("Year") or x.get("year") or 0)
        v = x.get("Value", x.get("value"))
        if v is None or pc not in HS.values():
            continue
        if pc not in out or nam > out[pc][1]:
            out[pc] = (round(float(v), 1), nam)
    return out, rows


def run():
    mfn, thieu = {}, []
    for ten, ma in NUOC.items():
        try:
            got, _ = lay_nuoc(ma)
        except Exception as e:  # noqa
            thieu.append("%s (%s)" % (ten, str(e)[:60]))
            continue
        hang = {}
        for sp, pc in HS.items():
            if pc in got:
                v, nam = got[pc]
                # thue ngoai han ngach co the rat cao (vi du ngo Han Quoc ~429%)
                if not 0 <= v <= 1000:
                    raise RuntimeError("Thue %s %s bat thuong: %s" % (ten, sp, v))
                hang[sp] = [v, nam]
        if hang:
            mfn[ten] = hang
        else:
            thieu.append("%s (khong co so)" % ten)
    if len(mfn) < 4:
        raise RuntimeError("Chi lay duoc MFN cua %d nuoc: %s" % (len(mfn), "; ".join(thieu)))
    obj = wp.load(PAGE) or {}
    if obj.get("mfn") == mfn:
        return "WTO MFN khong doi (%d nuoc)" % len(mfn)
    obj["mfn"] = mfn
    wp.save(PAGE, obj)
    return "da ghi MFN WTO cho %d nuoc%s" % (len(mfn), ("; thieu: " + "; ".join(thieu)) if thieu else "")


def thu():
    for ten in ("Trung Quốc", "EU"):
        got, rows = lay_nuoc(NUOC[ten])
        print(ten, "so dong:", len(rows))
        print(json.dumps(rows[:3], ensure_ascii=False)[:1200])
        print(ten, "ket qua:", got)
    return "chay thu, khong ghi"
