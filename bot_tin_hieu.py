"""Ket qua bot tin hieu GDHH247 len trang "Bot giao dich" (web GDHH247).

Chay trong workflow tin-nhanh-sfi.yml (15 phut/lan), sau buoc tin nhanh SFI, dung chung phien Telegram TG_SESSION.
Doc tin bot dang trong kenh rieng tu cua tung bot (anh Long la chu kenh), tach lenh vao / chot 50% / dong lenh,
tinh ket qua theo R va ghi khoi HTML giua 2 marker tren trang BOT_PAGE. Chi ghi khi noi dung doi (tranh tao
ban luu vo ich). Cong khai: lenh DA DONG day du; lenh dang mo chi bao "dang co lenh mo" (chi tiet danh cho khach
trong kenh). Ket qua la tin hieu that da gui, KHONG phai backtest.

Dinh dang tin (indicator Pine GDHH247_<san pham>):
  GDHH247 Bac SILVER: GD2 Trend D1 giam | M30 Pha Donchian 200 | SHORT @ 44.894 | SL 45.593 | TP 42.798
  GDHH247 Bac SILVER: M30 Pha Donchian 200 cham TP1, chot 50%, SL ve hoa von 44.894
  GDHH247 Bac SILVER: dong M30 Pha Donchian 200 SHORT | +1.25R | Cham TP2

Chay tay de xem HTML (khong can Telegram/WP): python bot_tin_hieu.py --xem
"""
import os
import re
import sys
import json
import html
import asyncio
import datetime

import wp

BOT_PAGE = int(os.environ.get("BOT_PAGE", "3711") or 3711)  # trang /bot-giao-dich/
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bot_tin_hieu.json")
VN = datetime.timezone(datetime.timedelta(hours=7))
M_START = "<!-- bot-ket-qua:start -->"
M_END = "<!-- bot-ket-qua:end -->"

BOTS = [
    {"key": "bac", "ten": "Bạc", "chat": -1006030382274, "kenh": "GDHH247 - Bạc",
     "mo_ta": "Bám theo giai đoạn thị trường (xu hướng D1, trạng thái H1), vào lệnh khi có tín hiệu phá vỡ hoặc "
              "từ chối trên khung M15, M30, H1. Mỗi lệnh có sẵn điểm cắt lỗ và chốt lời; một số phương án chốt "
              "50% ở TP1 rồi dời cắt lỗ về hòa vốn.",
     "san": "Bạc COMEX qua MXV"},
]

RX_VAO = re.compile(r"^GDHH247 (?P<sp>.+?) (?P<tk>\S+): (?P<gd>GĐ\d[^|]*?)\s*\|\s*(?P<pa>[^|]+?)\s*\|\s*"
                    r"(?P<dir>LONG|SHORT) @ (?P<e>[\d.,]+)\s*\|\s*SL (?P<sl>[\d.,]+)\s*\|\s*TP (?P<tp>[\d.,]+)")
RX_TP1 = re.compile(r"^GDHH247 (?P<sp>.+?) (?P<tk>\S+): (?P<pa>.+?) chạm TP1")
RX_DONG = re.compile(r"^GDHH247 (?P<sp>.+?) (?P<tk>\S+): đóng (?P<pa>.+?) (?P<dir>LONG|SHORT)\s*\|\s*"
                     r"(?P<r>[+-]?[\d.,]+)R\s*\|\s*(?P<why>.+)$")


def doc_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa
        return {}


def ghi_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def so(t):
    return float(t.replace(",", ""))


def phan_tich(text):
    """Tin bot -> su kien dict hoac None."""
    t = (text or "").strip().splitlines()[0] if text else ""
    m = RX_VAO.match(t)
    if m:
        return {"loai": "vao", "pa": m["pa"].strip(), "dir": m["dir"], "gd": m["gd"].strip(),
                "e": m["e"], "sl": m["sl"], "tp": m["tp"]}
    m = RX_DONG.match(t)
    if m:
        return {"loai": "dong", "pa": m["pa"].strip(), "dir": m["dir"], "r": so(m["r"]), "why": m["why"].strip()}
    m = RX_TP1.match(t)
    if m:
        return {"loai": "tp1", "pa": m["pa"].strip()}
    return None


def ghep_lenh(sk):
    """Danh sach su kien (theo thoi gian) -> (lenh da dong, lenh dang mo)."""
    mo, dong = [], []
    for s in sk:
        if s["loai"] == "vao":
            mo.append(dict(s, tp1=False))
        elif s["loai"] == "tp1":
            for x in reversed(mo):
                if x["pa"] == s["pa"]:
                    x["tp1"] = True
                    break
        elif s["loai"] == "dong":
            vt = None
            for i in range(len(mo) - 1, -1, -1):
                if mo[i]["pa"] == s["pa"] and mo[i]["dir"] == s["dir"]:
                    vt = i
                    break
            x = mo.pop(vt) if vt is not None else {"pa": s["pa"], "dir": s["dir"], "t": None, "e": "", "sl": "", "tp": "", "gd": ""}
            dong.append(dict(x, t_dong=s["t"], r=s["r"], why=s["why"]))
    return dong, mo


def vn_so(x, nd=2):
    s = ("%." + str(nd) + "f") % x
    s = s.rstrip("0").rstrip(".") if "." in s else s
    return s.replace(".", ",")


def vn_gia(t):
    return (t or "").replace(",", "").replace(".", ",")


def vn_tg(iso):
    if not iso:
        return "–"
    d = datetime.datetime.fromisoformat(iso).astimezone(VN)
    return d.strftime("%H:%M %d/%m/%Y")


def svg_luy_ke(rs):
    if not rs:
        return ""
    cum, c = [0.0], 0.0
    for r in rs:
        c += r
        cum.append(c)
    W, H, P = 640, 180, 14
    lo, hi = min(cum + [0]), max(cum + [0])
    if hi - lo < 1:
        hi, lo = hi + 0.5, lo - 0.5
    n = len(cum) - 1 or 1

    def xy(i, v):
        return P + (W - 2 * P) * i / n, P + (H - 2 * P) * (hi - v) / (hi - lo)

    pts = " ".join("%.1f,%.1f" % xy(i, v) for i, v in enumerate(cum))
    y0 = xy(0, 0)[1]
    mau = "#0a8f5a" if cum[-1] >= 0 else "#c80000"
    return ('<svg viewBox="0 0 %d %d" role="img" aria-label="Lũy kế R theo từng lệnh" class="gb-svg">'
            '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#bbb" stroke-dasharray="4 4"/>'
            '<polyline fill="none" stroke="%s" stroke-width="2.5" points="%s"/></svg>'
            % (W, H, P, y0, W - P, y0, mau, pts))


def the_bot(b, sk):
    dong, mo = ghep_lenh(sk)
    rs = [x["r"] for x in dong]
    n = len(rs)
    thang = sum(1 for r in rs if r > 0)
    tong = sum(rs)
    dd, dinh, c = 0.0, 0.0, 0.0
    for r in rs:
        c += r
        dinh = max(dinh, c)
        dd = max(dd, dinh - c)
    bd = sk[0]["t"] if sk else None
    if mo:
        tt = '<span class="gb-tt on">Đang có lệnh mở</span><span class="gb-nho">Chi tiết lệnh đang mở chỉ gửi cho khách trong kênh.</span>'
    else:
        tt = '<span class="gb-tt">Đứng ngoài thị trường</span>'
    o = ['<div class="gb-c">',
         '<div class="gb-h"><h3>Bot giao dịch %s</h3><span class="gb-san">%s</span></div>' % (b["ten"], b["san"]),
         '<p class="gb-mt">%s</p>' % html.escape(b["mo_ta"]),
         '<div class="gb-st">%s</div>' % tt]
    if n:
        o.append('<div class="gb-k">'
                 '<div><b>%d</b><span>Lệnh đã đóng</span></div>'
                 '<div><b>%s%%</b><span>Tỷ lệ thắng</span></div>'
                 '<div><b class="%s">%s%sR</b><span>Tổng kết quả</span></div>'
                 '<div><b>%sR</b><span>Trung bình mỗi lệnh</span></div>'
                 '<div><b>-%sR</b><span>Sụt giảm lớn nhất</span></div></div>'
                 % (n, vn_so(100.0 * thang / n, 1), "up" if tong >= 0 else "dn", "+" if tong >= 0 else "",
                    vn_so(tong), vn_so(tong / n), vn_so(dd)))
        o.append(svg_luy_ke(rs))
        hang = []
        for x in reversed(dong[-30:]):
            hang.append('<tr><td>%s</td><td>%s</td><td class="%s">%s</td><td>%s</td><td>%s</td><td>%s</td>'
                        '<td>%s</td><td class="%s">%s%sR</td><td>%s</td></tr>'
                        % (vn_tg(x.get("t")), html.escape(x["pa"]), "up" if x["dir"] == "LONG" else "dn",
                           "Mua" if x["dir"] == "LONG" else "Bán", vn_gia(x.get("e")), vn_gia(x.get("sl")),
                           vn_gia(x.get("tp")), vn_tg(x.get("t_dong")), "up" if x["r"] > 0 else "dn", "+" if x["r"] > 0 else "",
                           vn_so(x["r"]), html.escape(x["why"])))
        o.append('<div class="gb-tb"><table><thead><tr><th>Vào lệnh</th><th>Phương án</th><th>Chiều</th>'
                 '<th>Giá vào</th><th>Cắt lỗ</th><th>Chốt lời</th><th>Đóng lệnh</th><th>Kết quả</th>'
                 '<th>Lý do đóng</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(hang))
        o.append('<p class="gb-nho">Bảng hiện 30 lệnh đã đóng gần nhất. Giá vào, cắt lỗ, chốt lời là giá tham chiếu '
                 'theo nguồn dữ liệu bot dùng để ra tín hiệu, có thể chênh nhẹ so với giá khớp trên MXV.</p>')
    else:
        o.append('<p class="gb-nho">Chưa có lệnh nào đóng kể từ khi bắt đầu theo dõi công khai. Kết quả sẽ tự cập nhật '
                 'sau mỗi lệnh.</p>')
    o.append('<p class="gb-nho">Theo dõi công khai từ: %s.</p>' % (vn_tg(bd) if bd else "khi có tín hiệu đầu tiên"))
    o.append("</div>")
    return "\n".join(o)


def khoi_html(st):
    the = [the_bot(b, st.get("sk", {}).get(b["key"], [])) for b in BOTS]
    moi = max([s["t"] for v in st.get("sk", {}).values() for s in v] or [""])
    cap = ('<p class="gb-cn">Cập nhật đến tín hiệu lúc %s (giờ VN).</p>' % vn_tg(moi)) if moi else ""
    return "\n".join(the) + "\n" + cap


async def lay_tin(st):
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    ses = re.sub(r"[\s\"'`=]+", "", os.environ["TG_SESSION"])
    ses += "=" * (-(len(ses) - 1) % 4)
    client = TelegramClient(StringSession(ses), int(os.environ["TG_API_ID"]), os.environ["TG_API_HASH"].strip())
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("TG_SESSION het han hoac bi thu hoi")
    can = {b["chat"]: b for b in BOTS}
    ent = {}
    async for d in client.iter_dialogs():
        if d.id in can:
            ent[d.id] = d.entity
    last = st.setdefault("last", {})
    sk = st.setdefault("sk", {})
    moi = 0
    for cid, b in can.items():
        if cid not in ent:
            print("Khong thay kenh:", b["kenh"])
            continue
        lid = last.get(b["key"], 0)
        top = lid
        async for m in client.iter_messages(ent[cid], min_id=lid, reverse=True, limit=500):
            top = max(top, m.id)
            s = phan_tich(m.message)
            if s:
                s["t"] = m.date.astimezone(datetime.timezone.utc).isoformat(timespec="seconds")
                s["id"] = m.id
                sk.setdefault(b["key"], []).append(s)
                moi += 1
        last[b["key"]] = top
    await client.disconnect()
    return moi


def ghi_trang(khoi):
    raw = wp.get_raw(BOT_PAGE)
    if raw.count(M_START) != 1 or raw.count(M_END) != 1:
        raise RuntimeError("Trang %d khong co dung 1 cap marker bot-ket-qua" % BOT_PAGE)
    a = raw.index(M_START) + len(M_START)
    z = raw.index(M_END)
    if raw[a:z].strip() == khoi.strip():
        return False
    wp.backup_raw(BOT_PAGE, raw)
    wp.set_raw(BOT_PAGE, raw[:a] + "\n" + khoi + "\n" + raw[z:])
    return True


def main():
    if "--xem" in sys.argv:
        print(khoi_html(doc_state()))
        return
    if not all(os.environ.get(k) for k in ("TG_API_ID", "TG_API_HASH", "TG_SESSION")):
        print("Chua co TG_*: bo qua")
        return
    if not (wp.enabled() and BOT_PAGE):
        raise RuntimeError("Thieu WP_* hoac BOT_PAGE")
    st = doc_state()
    moi = asyncio.run(lay_tin(st))
    ghi_state(st)
    doi = ghi_trang(khoi_html(st))
    print("Tin bot moi: %d | trang %d %s" % (moi, BOT_PAGE, "da cap nhat" if doi else "khong doi"))


if __name__ == "__main__":
    main()
