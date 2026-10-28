"""Lam nong cache (Cache Enabler): goi lai cac trang chinh va bai moi nhat de nguoi doc gap ban cache.
Chay sau moi job du lieu (data.yml) va moi 30 phut (giam-sat.yml).
"""
import time
import requests
import wp

BASE = "https://giaodichhanghoa247.vn"
# trang chinh: duong dan khong co query (Cache Enabler bo qua URL co query)
TRANG = [
    "/", "/index.php/tin-tuc-nhanh/", "/index.php/dashboard-tong-hop/", "/index.php/gia-the-gioi-truc-tuyen/",
    "/index.php/phan-tich-thi-truong/", "/index.php/phan-tich-chuyen-sau/", "/index.php/khuyen-nghi/",
    "/index.php/ket-qua-khuyen-nghi/", "/index.php/phan-tich-cung-cau-san-pham/", "/index.php/kim-loai-quy/",
    "/index.php/kien-thuc-dau-tu/", "/index.php/ve-gdhh247/", "/index.php/mo-tai-khoan-gdhh/",
    "/index.php/phan-tich-nong-san/", "/index.php/phan-tich-kim-loai/", "/index.php/phan-tich-nguyen-lieu-cong-nghiep/",
    "/index.php/khuyen-nghi-ket-qua-khuyen-nghi/", "/index.php/tong-quat-kinh-te-the-gioi/",
    "/index.php/category/kim-loai/", "/index.php/category/nong-san/", "/index.php/category/nang-luong/",
    "/index.php/category/tin-tuc-vi-mo/", "/index.php/category/khuyen-nghi/", "/index.php/phan-tich-nang-luong/",
    "/index.php/gia-ca-phe/",
]
# trinh duyet that (Cache Enabler khong phan biet thiet bi, nhung gui UA nhu nguoi doc)
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
        hit = "cache-enabler" in r.headers.get("X-Cache-Handler", "") or "Cache Enabler by" in r.text[-300:]
        return r.status_code, ms, hit
    except Exception:  # noqa
        return 0, round((time.time() - t) * 1000), False


def run():
    ds = TRANG + bai_moi()
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
