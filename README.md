# GDHH247 – dữ liệu tự động

Các job Python chạy trên GitHub Actions, lấy số liệu công khai và ghi vào trang dữ liệu ẩn của giaodichhanghoa247.vn (không tốn token Claude).

| Job | Trang đích | Lịch (UTC) |
|---|---|---|
| esr – xuất khẩu hằng tuần USDA | 801, khóa esr | Thứ Năm 12:45, 13:30, 14:30; thứ Sáu 00:30 |
| insp – thanh tra xuất khẩu | 801, khóa insp | Thứ Hai 17:30, 19:30, 23:30; thứ Ba 02:30, 17:30 |
| prog – Crop Progress | 801, khóa prog | Thứ Hai 20:10, 21:10, 22:10; thứ Ba 20:10, 21:10 |

Các lần chạy lặp trong ngày là có chủ đích: job bỏ qua nếu không có báo cáo mới.

Secrets cần có: WP_URL, WP_USER, WP_APP_PASSWORD, FAS_API_KEY.

Kiểm tra: mở data/status.json (job nào chạy lúc nào, OK hay lỗi). Chạy tay: tab Actions, chọn workflow, Run workflow.
