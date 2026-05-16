# Hướng dẫn Khởi chạy Superset & Drupal Admin CMS

Tài liệu này hướng dẫn bạn cách khởi chạy hệ thống Superset tích hợp cùng với Drupal Admin CMS cho dự án AI Translator.

## 1. Yêu cầu hệ thống
- Đã cài đặt **Docker** và **Docker Compose**.
- Các port `8080` (Drupal) và `8088` (Superset) trên máy bạn phải đang trống.

## 2. Các bước khởi chạy hệ thống

### Bước 2.1. Build và Khởi động các Container

Mở terminal/command prompt tại thư mục gốc của dự án (`d:\ai_trans_demo`), và chạy lệnh sau để build và khởi động lại toàn bộ các dịch vụ (bao gồm Drupal, MariaDB, và Superset):

```bash
docker-compose up -d --build
```

Lệnh này sẽ:
- Khởi động Drupal CMS trên port `8080`.
- Build image của Superset từ thư mục `using_superset/superset`.
- Khởi chạy Superset trên port `8088`.
- Chạy ngầm kịch bản `auto_import.py` bên trong container `superset` để tự động khôi phục cấu hình dashboard có sẵn.

### Bước 2.2. Chờ quá trình Import Dashboard hoàn tất

Container `superset` sẽ mất khoảng 30 - 60 giây để khởi động hoàn toàn và import dashboard. Bạn có thể theo dõi log của Superset để xem tiến trình:

```bash
docker logs -f ai_trans_demo-superset-1
```
*(Tên container có thể thay đổi tùy thuộc vào tên thư mục dự án của bạn, thường là `<tên thư mục>-superset-1`)*.
Bạn nhấn `Ctrl+C` để thoát xem log.

### Bước 2.3. Truy cập vào Drupal Admin CMS

Bây giờ bạn có thể truy cập vào Drupal để xem dashboard phân tích đã được tích hợp:

1. Mở trình duyệt và truy cập: **http://localhost:8080**
2. Đăng nhập vào tài khoản Admin của Drupal (nếu hệ thống yêu cầu).
3. Truy cập vào trang quản trị AI Translator Dashboard:
   **http://localhost:8080/admin/config/ai-translator/dashboard**

Tại đây, bạn sẽ thấy giao diện **Advanced Analytics Dashboard**, trong đó có chứa báo cáo của Superset được nhúng trực tiếp qua Iframe. Do cấu hình `PUBLIC_ROLE_LIKE = "Admin"` đã được thiết lập, bạn sẽ không cần phải đăng nhập lại vào Superset để xem báo cáo.

## 3. Khắc phục sự cố thường gặp (Troubleshooting)

- **Iframe trắng hoặc báo lỗi Refused to Connect**:
  - Đảm bảo container `superset` đang chạy (`docker ps`).
  - Kiểm tra xem port `8088` đã được mở thành công chưa. Mở trình duyệt vào `http://localhost:8088`, nếu trang Superset tải lên được thì hệ thống đang hoạt động bình thường.
  - Kiểm tra log container xem quá trình khởi động có lỗi database nào không.

- **Không hiển thị biểu đồ hoặc báo "No Data"**:
  - Cơ sở dữ liệu SQLite của Superset được map tại thư mục `./using_superset/superset_home/superset.db`. Các biểu đồ này đang trỏ vào kết nối dữ liệu nào đó bên trong cấu hình xuất ra. Đảm bảo cấu hình Database Connection trong Superset của bạn đã được cập nhật trỏ đúng vào cơ sở dữ liệu thật nếu cần thiết. Bạn có thể đăng nhập trực tiếp `http://localhost:8088` với tài khoản admin (nếu có cấu hình) để tinh chỉnh kết nối này.

- **Xung đột Port**:
  - Nếu port `8088` bị chiếm dụng, bạn có thể vào file `docker-compose.yml`, tìm dòng `- "8088:8088"` và đổi thành `- "8089:8088"` (và nhớ cập nhật lại URL trong `DashboardController.php` của Drupal).
