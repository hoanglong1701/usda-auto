"""Chay cac job: python -m gd.run esr insp prog ...  Ghi data/status.json de de kiem tra."""
import sys
import json
import os
import datetime
import traceback

import usda_esr
import usda_insp
import usda_prog
from names import unmapped

JOBS = {
    "esr": usda_esr.run,
    "insp": usda_insp.run,
    "prog": usda_prog.run,
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
