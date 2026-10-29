"""Lam nong cache (Cache Enabler hoac LiteSpeed Cache): goi lai cac trang chinh va bai moi nhat de nguoi doc gap ban cache.
Chay sau moi job du lieu (data.yml) va moi 30 phut (giam-sat.yml).
"""
import time
import requests
import wp

BASE = "https://giaodichhanghoa247.vn"
# trang chinh: duong dan khong co query (plugin cache bo qua URL co query); tien to /index.php them luc chay neu can
TRANG = [
    "/", "/tin-tuc-nhanh/", "/dashboard-tong-hop/", "/gia-the-gioi-truc-tuyen/",
    "/phan-tich-thi-truong/", "/phan-tich-chuyen-sau/", "/khuyen-nghi/",
    "/ket-qua-khuyen-nghi/", "/phan-tich-cung-cau-san-pham/", "/kim-loai-quy/",
    "/kien-thuc-dau-tu/", "/ve-gdhh247/", "/mo-tai-khoan-gdhh/",
    "/phan-tich-nong-san/", "/phan-tich-kim-loai/", "/phan-tich-nguyen-lieu-cong-nghiep/",
    "/khuyen-nghi-ket-qua-khuyen-nghi/", "/tong-quat-kinh-te-the-gioi/",
    "/category/kim-loai/", "/category/nong-san/", "/category/nang-luong/",
    "/category/tin-tuc-vi-mo/", "/category/khuyen-nghi/", "/phan-tich-nang-luong/",
    "/gia-ca-phe/",
]
# trinh duyet that (plugin cache khong phan biet thiet bi, nhung gui UA nhu nguoi doc)
HDR = {"User-Agent": wp.UA, "Accept": "text/html", "Accept-Encoding": "gzip"}


def bai_moi(n=20):
    try:
        r = requests.get(BASE + "/index.php/wp-json/wp/v2/posts", params={"per_page": n, "_fields": "link"},
                         headers={"User-Agent": wp.UA}, timeout=30)
        return [x["link"].replace(BASE, "") for x in r.json()]
    except Exception:  # noqa
        return []


def goi(path):
    t = time.time()
    try:
        r = requests.get(BASE + path, headers=HDR, timeout=60)
        ms = round((time.time() - t) * 1000)
        hit = ("cache-enabler" in r.headers.get("X-Cache-Handler", "") or "Cache Enabler by" in r.text[-300:]
               or "hit" in r.headers.get("X-LiteSpeed-Cache", "").lower())
        return r.status_code, ms, hit
    except Exception:  # noqa
        return 0, round((time.time() - t) * 1000), False


def run():
    tt = wp.tien_to()
    ds = [p if p == "/" else tt + p for p in TRANG] + bai_moi()
    lan1 = [(p,) + goi(p) for p in ds]
    # lan 2: kiem tra trang da vao cache chua
    lan2 = [(p,) + goi(p) for p in ds]
    loi = [p for p, st, _, _ in lan1 if st != 200]
    hit = sum(1 for _, _, _, h in lan2 if h)
    tb1 = round(sum(ms for _, _, ms, _ in lan1) / len(lan1))
    tb2 = round(sum(ms for _, _, ms, _ in lan2) / len(lan2))
    msg = "%d trang, lan 1 tb %d ms, lan 2 tb %d ms, %d/%d trang co cache" % (len(ds), tb1, tb2, hit, len(ds))
    if loi:
        msg += "; loi: " + ", ".join(loi[:5])
    return msg


if __name__ == "__main__":
    print(run())
