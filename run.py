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
