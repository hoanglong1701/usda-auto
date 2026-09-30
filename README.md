# usda-auto – tự động cập nhật báo cáo USDA lên giaodichhanghoa247.vn

Script chạy trên GitHub Actions (không cần bật máy, không tốn usage Claude).
Mỗi 5 phút trong khung giờ ra báo cáo, nó hỏi API của USDA; nếu có kỳ số liệu mới
thì lưu JSON vào thư mục `data/` và cập nhật khối nội dung trên trang WordPress.

Báo cáo đã có: **Grain Stocks**, **Crop Progress** (NASS Quick Stats).
Sẽ thêm: WASDE, PSD, Export Sales (thêm 1 file trong `src/reports/` và 1 dòng trong `main.py`).

## Cài đặt (làm 1 lần)

1. Trên GitHub (tài khoản hoanglong1701) tạo repo mới, ví dụ `usda-auto`.
   Nên chọn **Public** (dữ liệu USDA vốn công khai, Actions miễn phí không giới hạn;
   khoá API nằm trong Secrets nên không bị lộ). Chọn Private thì có thể hết 2.000 phút miễn phí/tháng.
2. Upload toàn bộ nội dung thư mục này lên repo (Add file > Upload files, kéo thả cả thư mục,
   nhớ có cả thư mục ẩn `.github`). Nếu trình duyệt không kéo được thư mục ẩn, tạo file
   `.github/workflows/usda.yml` bằng nút Add file > Create new file rồi dán nội dung.
3. Vào Settings > Secrets and variables > Actions > New repository secret, thêm lần lượt:

   | Tên secret | Giá trị |
   |---|---|
   | `NASS_API_KEY` | key Quick Stats (nên tạo key mới) |
   | `WP_URL` | `https://giaodichhanghoa247.vn` |
   | `WP_USER` | tên đăng nhập WordPress quản trị |
   | `WP_APP_PASSWORD` | Application Password (Users > Profile > Application Passwords) |
   | `WP_PAGE_ID` | ID trang "Số liệu USDA" (số sau `post=` khi sửa trang) |

   Chưa có 4 secret WordPress thì script vẫn chạy, chỉ lưu JSON và bỏ qua bước đăng.
4. Vào tab Actions > usda-auto > Run workflow để chạy thử.
   Ô `force` = 1 nghĩa là đăng lại dù chưa có kỳ mới (dùng khi thử).
5. Xem nhật ký chạy. Dòng `KỲ MỚI ... đã lưu` là thành công. Nếu lỗi, copy nhật ký gửi Claude.

## Xử lý sự cố thường gặp

- `401/403` khi đăng WordPress: một số host chặn header Authorization. Thêm vào `.htaccess`:
  `RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]`, hoặc nhờ nhà cung cấp host mở REST API.
- `API không trả dữ liệu`: tên trường của NASS có thể khác dự kiến; gửi nhật ký để chỉnh.
- Dữ liệu trong API NASS thường ra trễ vài phút sau khi USDA công bố, nên kỳ mới sẽ xuất hiện
  ở lần chạy 5 phút kế tiếp.
- GitHub có thể trễ vài phút ở lịch chạy tự động; đó là bình thường.

## Bảo mật

Không ghi khoá API hay mật khẩu vào code. Chỉ dùng GitHub Secrets.
