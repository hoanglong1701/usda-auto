"""Chay cac job: python -m gd.run esr insp prog ...  Ghi data/status.json de de kiem tra."""
import sys
import json
import os
import datetime
import traceback

import usda_esr
import usda_insp
import usda_prog
import orgs
import wasde
import probe
import fred
import fred_monthly
import yeu_to
import dinh_luong
import kl_nlcn
import ns_enso
import gia_vn
import sua_trang_gia
import sua_khoi_enso
import lam_nong_cache
import chan_doan
import lich_kt
import anh_chuyen_muc
import sua_menu_trang
import cot
import nang_luong
import tuyen_duong
import gia_ca_phe
import gia_fob
import imf_no_cong
import wto_thue
import gia_nhap_khau
import cuoc_bien
import tom_tat
import doi_cache
import indexnow_all
import ico_ton_kho
import iandm_ca_phe
from names import unmapped

JOBS = {
    "esr": usda_esr.run,
    "insp": usda_insp.run,
    "prog": usda_prog.run,
    "orgs": orgs.run,
    "wasde": wasde.run,
    "probe": probe.run,
    "fred_test": fred.run,
    "fred_monthly": fred_monthly.run,
    "yeu_to": yeu_to.run,
    "dinh_luong": dinh_luong.run,
    "dinh_luong_thu": dinh_luong.run_dry,
    "kl_nlcn": kl_nlcn.run,
    "ns_enso": ns_enso.run,
    "gia_vn": gia_vn.run,
    "gia_vn_thu": gia_vn.run_dry,
    "sua_trang_gia": sua_trang_gia.run,
    "sua_khoi_enso": sua_khoi_enso.run,
    "lam_nong_cache": lam_nong_cache.run,
    "chan_doan": chan_doan.run,
    "lich_kt": lich_kt.run,
    "lich_kt_thu": lich_kt.run_dry,
    "anh_chuyen_muc": anh_chuyen_muc.run,
    "sua_menu_trang": sua_menu_trang.run,
    "cot": cot.run,
    "cot_thu": cot.run_dry,
    "nang_luong": nang_luong.run,
    "tuyen_duong": tuyen_duong.run,
    "gia_ca_phe": gia_ca_phe.run,
    "gia_fob": gia_fob.run,
    "gia_fob_thu": gia_fob.thu,
    "imf_no_cong": imf_no_cong.run,
    "imf_no_cong_thu": imf_no_cong.run_dry,
    "wto_thue": wto_thue.run,
    "wto_thue_thu": wto_thue.thu,
    "gia_nhap_khau": gia_nhap_khau.run,
    "gia_nhap_khau_thu": gia_nhap_khau.thu,
    "cuoc_bien": cuoc_bien.run,
    "cuoc_bien_thu": cuoc_bien.thu,
    "tom_tat": tom_tat.run,
    "tom_tat_thu": tom_tat.run_dry,
    "doi_cache": doi_cache.run,
    "doi_cache_lai": doi_cache.run_back,
    "indexnow_all": indexnow_all.run,
    "ico_ton_kho": ico_ton_kho.run,
    "iandm_ca_phe": iandm_ca_phe.run,
}


def main(names):
    os.makedirs("data", exist_ok=True)
    path = os.path.join("data", "status.json")
    try:
        status = json.load(open(path, encoding="utf-8"))
    except Exception:
        status = {}
    failed = False
    for n in names:
        fn = JOBS.get(n)
        if not fn:
            print("Job khong ton tai:", n)
            failed = True
            continue
        now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        try:
            msg = fn()
            status[n] = {"ok": True, "at": now, "msg": msg}
            print("[%s] OK: %s" % (n, msg))
        except Exception as e:  # noqa
            failed = True
            tb = traceback.format_exc()
            status[n] = {"ok": False, "at": now, "error": "%s: %s" % (type(e).__name__, e), "trace": tb[-1500:]}
            print("[%s] LOI: %s" % (n, e))
            print(tb)
    if unmapped:
        status["_ten_nuoc_chua_dich"] = sorted(unmapped)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=1)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
