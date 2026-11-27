"""Tin nhanh tu Telegram SFI (Saigon Futures) len web GDHH247.

Chay 15 phut/lan tren GitHub Actions (workflow tin-nhanh-sfi.yml). Doc tin moi trong 2 nhom Telegram
cua anh Long ("SFI Thong tin FA", "SFI - Bao cao hang hoa"; SFI cho phep dung tu 27/11/2026),
loc tin hang hoa va vi mo quan trong, gop moi chuyen muc thanh 1 bai cho moi luot va dang ngay.

Secrets can co: TG_API_ID, TG_API_HASH, TG_SESSION (StringSession tao bang tao_session_telegram.py tren may
anh Long), WP_URL, WP_USER, WP_APP_PASSWORD. Thieu TG_* thi thoat binh thuong, khong bao loi.
Chi DOC Telegram: khong gui tin, khong danh dau gi them.
"""
import os
import re
import json
import html
import asyncio
import hashlib
import datetime

import requests

import wp

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tin_nhanh_sfi.json")
NHOM = ["SFI Thông tin FA", "SFI - Báo cáo hàng hóa"]
VN = datetime.timezone(datetime.timedelta(hours=7))
NGUON = "SFI (Saigon Futures)"

CAT = {"Kim loại": 4, "Nông sản": 5, "Năng lượng": 6, "Nguyên liệu công nghiệp": 13,
       "USDA Flash Sales": 5}
TEN_CAT = {4: "Kim loại", 5: "Nông sản", 6: "Năng lượng", 7: "Vĩ mô", 13: "Nguyên liệu công nghiệp"}
TAG = re.compile(r"\[([^\[\]]{2,40})\]\s*")

KW_NL = re.compile(r"dầu|khí đốt|khí tự nhiên|LNG|lọc dầu|Hormuz|OPEC|tàu chở dầu|xăng|diesel|nhiên liệu", re.I)
KW_NS = re.compile(r"ngũ cốc|lúa mì|ngô|đậu tương|Biển Đen|Odesa|gạo|phân bón", re.I)
KW_KL = re.compile(r"vàng|bạc|đồng|nhôm|niken|thiếc|kẽm|quặng|mỏ", re.I)
KW_NLCN = re.compile(r"cà phê|đường|bông|ca cao|dầu cọ|cao su", re.I)
KW_VM = re.compile(r"Fed|FOMC|lãi suất|lạm phát|CPI|PCE|PMI|GDP|việc làm|thuế|Trung Quốc|USD|đồng đô la|"
                   r"trái phiếu|Kho bạc|ECB|BOJ|PBOC|Nhân dân tệ|suy thoái", re.I)


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


def so_vn(t):
    """89,270 -> 89.270 ; 0.31% -> 0,31% (SFI hay viet so kieu Anh)."""
    t = re.sub(r"(?<![\d.,])(\d{1,3}(?:,\d{3})+)(?![\d,])", lambda m: m.group(1).replace(",", "#"), t)
    t = re.sub(r"(?<![\d.])(\d+)\.(\d+)(?![\d.])", r"\1,\2", t)
    return t.replace("#", ".")


def phan_loai(tag, text):
    if tag in CAT:
        return CAT[tag]
    if tag == "Vĩ mô" or tag == "Hàng hóa":
        return 7 if KW_VM.search(text) else None
    if tag == "Địa chính trị":
        if KW_NL.search(text):
            return 6
        if KW_NS.search(text):
            return 5
        return None
    # khong co nhan hoac nhan la (Viet Nam...): doan theo tu khoa
    for kw, c in ((KW_NLCN, 13), (KW_NL, 6), (KW_NS, 5), (KW_KL, 4)):
        if kw.search(text):
            return c
    return 7 if (tag and KW_VM.search(text)) else None


def tach(text):
    """Mot tin co the chua nhieu nhan '[A] ... [B] ...' -> [(nhan, noi dung)]."""
    text = text.strip()
    ms = list(TAG.finditer(text))
    if not ms:
        return [("", text)]
    out = []
    if ms[0].start() > 0 and text[:ms[0].start()].strip():
        out.append(("", text[:ms[0].start()].strip()))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        out.append((m.group(1).strip(), text[m.end():end].strip()))
    return out


def sach(t):
    t = so_vn(t)
    t = t.replace("&", " và ").replace("gd:", "gd :")
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def tieu_de_dong(t):
    dong = [x.strip() for x in t.split("\n") if x.strip()]
    if not dong:
        return "", ""
    dau = dong[0]
    than = " ".join(dong[1:])
    if not than and len(dau) > 170:
        m = re.match(r"(.{40,170}?[.;:])\s", dau)
        if m:
            than = dau[m.end():]
            dau = m.group(1)
    return dau.rstrip(" ."), than


def cat_ngan(t, n):
    if len(t) <= n:
        return t
    t = t[:n]
    return t[:t.rfind(" ")].rstrip(",;:") + "…"


async def lay_tin(st):
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    api_id = int(os.environ["TG_API_ID"])
    # bo khoang trang, xuong dong, dau nhay lo dinh khi copy tu PowerShell (chuoi bi ngat dong)
    ses = re.sub(r"[\s\"'`=]+", "", os.environ["TG_SESSION"])
    ses += "=" * (-(len(ses) - 1) % 4)
    print("Do dai TG_SESSION:", len(ses), "(chuan ~353, bat dau bang 1:", ses[:1] == "1", ")")
    client = TelegramClient(StringSession(ses), api_id, os.environ["TG_API_HASH"].strip())
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("TG_SESSION het han hoac bi thu hoi: tao lai bang tao_session_telegram.py")
    ids = st.setdefault("chat", {})
    if not all(n in ids for n in NHOM):
        async for d in client.iter_dialogs():
            if d.name in NHOM:
                ids[d.name] = d.id
    moi = []
    bay_gio = datetime.datetime.now(datetime.timezone.utc)
    for ten in NHOM:
        cid = ids.get(ten)
        if cid is None:
            print("Khong thay nhom:", ten)
            continue
        last = st.setdefault("last", {}).get(ten)
        kw = {"min_id": last, "reverse": True, "limit": 400} if last else {"limit": 60}
        top = last or 0
        async for m in client.iter_messages(cid, **kw):
            top = max(top, m.id)
            if not last and (bay_gio - m.date).total_seconds() > 3600:
                continue  # lan dau chi lay 60 phut gan nhat, tranh dang don
            if m.message:
                moi.append((ten, m.id, m.date, m.message))
        st["last"][ten] = top
    await client.disconnect()
    moi.sort(key=lambda x: x[2])
    return moi


def dang(cat, muc):
    """muc: [(gio 'HH:MM', ngay 'DD/MM/YYYY', dau, than)] cung chuyen muc -> 1 bai."""
    s = wp._sess()
    base = wp._cfg()[0] + "/index.php/wp-json/wp/v2/posts"
    chinh = max(muc, key=lambda x: len(x[3]) + len(x[2]))
    td = chinh[2]
    for x in muc:
        if x is not chinh and len(td) + len(x[2]) + 2 <= 150:
            td += "; " + x[2]
            break
    td = cat_ngan(td, 160)
    cuoi = muc[-1]
    noi = ['<!-- wp:paragraph -->\n<p><strong>Thời gian tin: %s %s (giờ VN)</strong> · Nguồn: %s</p>\n<!-- /wp:paragraph -->'
           % (cuoi[0], cuoi[1], NGUON)]
    li = []
    for gio, _, dau, than in muc:
        nd = html.escape(dau) + (". " + html.escape(cat_ngan(than, 900)) if than else ".")
        li.append("<!-- wp:list-item -->\n<li><strong>%s:</strong> %s</li>\n<!-- /wp:list-item -->" % (gio, nd))
    noi.append('<!-- wp:list -->\n<ul class="wp-block-list">' + "\n".join(li) + "</ul>\n<!-- /wp:list -->")
    content = "\n\n".join(noi).replace("&amp;", "và").replace("&#x27;", "’").replace("&quot;", "\"")
    r = s.post(base, json={"title": td, "content": content, "status": "publish", "categories": [cat]}, timeout=60)
    r.raise_for_status()
    return r.json().get("id"), td


def main():
    if not all(os.environ.get(k) for k in ("TG_API_ID", "TG_API_HASH", "TG_SESSION")):
        print("Chua co TG_API_ID/TG_API_HASH/TG_SESSION: bo qua")
        return
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    st = doc_state()
    tin = asyncio.run(lay_tin(st))
    da = set(st.get("hash", []))
    nhom = {}
    for ten, mid, d, text in tin:
        v = d.astimezone(VN)
        for tag, nd in tach(text):
            nd = sach(nd)
            if len(nd) < 25:
                continue
            c = phan_loai(tag, nd)
            if not c:
                continue
            h = hashlib.md5(re.sub(r"\W+", "", nd.lower())[:200].encode()).hexdigest()[:12]
            if h in da:
                continue
            da.add(h)
            dau, than = tieu_de_dong(nd)
            if dau:
                nhom.setdefault(c, []).append((v.strftime("%H:%M"), v.strftime("%d/%m/%Y"), dau, than))
    ket = []
    for c, muc in sorted(nhom.items()):
        pid, td = dang(c, muc[:25])
        ket.append("%s %s (%d tin): %s" % (TEN_CAT[c], pid, len(muc), td))
    st["hash"] = list(da)[-1500:]
    st["luot"] = datetime.datetime.now(VN).strftime("%Y-%m-%d %H:%M")
    st.setdefault("bai", [])
    st["bai"] = (st["bai"] + ket)[-100:]
    ghi_state(st)
    print("\n".join(ket) if ket else "Khong co tin moi can dang (%d tin doc)" % len(tin))


if __name__ == "__main__":
    main()
