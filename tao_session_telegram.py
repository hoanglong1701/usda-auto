"""Chay MOT LAN tren may anh Long de tao TG_SESSION cho job tin nhanh SFI.

Cach chay (PowerShell):
    py -m pip install telethon
    py tao_session_telegram.py

Script hoi api_id, api_hash (lay o https://my.telegram.org > API development tools), so dien thoai,
ma xac nhan Telegram gui ve app, va mat khau 2 lop neu co. Moi thu chi nhap tren may anh, khong gui di dau.
Cuoi cung in ra mot chuoi dai: dan chuoi do vao GitHub Secret TG_SESSION.

CHUOI NAY CO QUYEN DANG NHAP TAI KHOAN TELEGRAM CUA ANH: khong gui cho ai, khong dan vao chat.
Muon thu hoi: Telegram > Settings > Devices, ket thuc phien "GDHH247 tin nhanh".
"""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("api_id: ").strip())
api_hash = input("api_hash: ").strip()
with TelegramClient(StringSession(), api_id, api_hash, device_model="GDHH247 tin nhanh") as client:
    print("\nDang nhap thanh cong:", client.get_me().first_name)
    print("\n===== TG_SESSION (dan vao GitHub Secret, KHONG gui cho ai) =====\n")
    print(client.session.save())
    print("\n=================================================================")
