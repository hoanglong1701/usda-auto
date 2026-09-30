"""Chạy tất cả báo cáo: nếu có kỳ mới so với state.json thì lưu JSON + đăng lên WordPress."""
import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "reports"))

import crop_progress  # noqa: E402
import grain_stocks  # noqa: E402
import render  # noqa: E402
import wp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state.json"
DATA = ROOT / "data"
REPORTS = [grain_stocks, crop_progress]  # thêm WASDE, PSD... ở đây


def main():
    force = os.environ.get("FORCE") == "1"
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    DATA.mkdir(exist_ok=True)
    failed = 0
    for mod in REPORTS:
        try:
            d = mod.fetch()
            if not force and state.get(mod.NAME) == d["release_id"]:
                print(f"[{mod.NAME}] chưa có kỳ mới ({d['release_id']})")
                continue
            (DATA / f"{mod.NAME}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2))
            html = render.render(d)
            (DATA / f"{mod.NAME}.html").write_text(html)
            wp.publish(mod.NAME, html)
            state[mod.NAME] = d["release_id"]
            print(f"[{mod.NAME}] KỲ MỚI {d['release_id']} -> đã lưu")
        except Exception:
            failed += 1
            print(f"[{mod.NAME}] LỖI:\n{traceback.format_exc()}")
    STATE.write_text(json.dumps(state, indent=2))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
