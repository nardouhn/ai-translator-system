# Báo cáo: Các Tệp Tin và Thư Mục Không Cần Thiết Để Chạy Dự Án

Sau khi quét toàn bộ mã nguồn của dự án `ai_trans_demo`, dưới đây là danh sách các tệp tin và thư mục **không cần thiết** cho quá trình chạy thực tế của ứng dụng (Frontend Flutter & Backend FastAPI) cùng với lý do cụ thể. Bạn hoàn toàn có thể xóa hoặc di chuyển chúng ra chỗ khác để dự án gọn gàng hơn.

## 1. Các Thư Mục Môi Trường Ảo (Virtual Environments) Thừa
Dự án của bạn đang có quá nhiều môi trường ảo Python bị trùng lặp. Bạn chỉ cần giữ lại **1 môi trường duy nhất** (thường là `.venv` ở trong thư mục backend) mà bạn dùng để chạy lệnh `uvicorn`. Các thư mục còn lại đang chiếm rất nhiều dung lượng rác:
- `d:\ai_trans_demo\venv\` (Tại thư mục gốc)
- `d:\ai_trans_demo\.venv\` (Tại thư mục gốc)
- `d:\ai_trans_demo\backend\venv\` (Bị dư thừa trong backend)
> **Khuyến nghị:** Xóa các thư mục venv không sử dụng để tiết kiệm hàng GB dung lượng ổ cứng.

## 2. Các File Jupyter Notebook (Prototyping)
Các tệp có đuôi `.ipynb` thường được dùng để thử nghiệm code AI hoặc deploy lên Kaggle/Google Colab. Chúng không tham gia vào luồng chạy thực tế của FastAPI:
- `deploy (1).ipynb`
- `deploy-model (1).ipynb`
- `deploy-model.ipynb`
- `deploy.ipynb`

## 3. Các Tệp Tài Liệu / Dữ Liệu Mẫu (Sample Files)
Đây là các file dùng để test tính năng dịch tài liệu, hoàn toàn có thể xóa khỏi thư mục source code:
- `100 truyện ngắn_Ms Hoa Giao tiếp.pdf`
- `Hanwha Life Esports.docx`
- `bản ngắn.docx`
- `medical.txt`

## 4. Các Tệp Hình Ảnh (Assets Không Dùng Trong Code)
Có một số ảnh chụp màn hình / sơ đồ nằm rải rác ở thư mục gốc, có lẽ dùng để đính kèm vào file `README.md` chứ không được Flutter hay Backend gọi tới trong quá trình chạy:
- `dfile.png`, `dtext.png`, `lfile.png`, `ltext.png`
- `supabase-schema-.png`

## 5. Các Thư Mục Rỗng / Lỗi Tạo Nhầm
- `d:\ai_trans_demo\admin_cms\` (Thư mục trống hoàn toàn, có thể là project định làm thêm nhưng chưa code).
- `d:\ai_trans_demo\backend\backend\` (Có vẻ như bạn đã gõ nhầm lệnh tạo thư mục lồng nhau).

## 6. Các Tệp Script Nháp (Scratch & Test Scripts)
Trong thư mục `backend/`, có rất nhiều tệp script nháp được tạo ra trong quá trình bạn debug hoặc test thử API. Các tệp này không nằm trong luồng chạy của `app.main:app`:
- Thư mục `backend/scratch/`
- `backend/scratch2.py` đến `backend/scratch6.py`
- `backend/scratch6_out.txt`
- `backend/test_api.py` (Script để test độc lập API).

## 7. Các Tệp Cấu Hình Docker Cục Bộ (Local Docker)
Vì bạn đã chuyển sang dùng **Cloud Database (Supabase)** và **Cloud Cache (Upstash Redis)** nên việc dùng Docker để chạy Local Database/Redis là không còn cần thiết nữa. Bạn có thể xóa các file sau nếu không có ý định chạy cục bộ bằng Docker:
- `docker-compose.yml`
- `Dockerfile`

> **Giải đáp: Dữ liệu (JSON/Cache/DB) cũ của Docker đi đâu rồi?**
> Trước khi bạn lên Cloud, dữ liệu (các bản dịch, cache) **không được lưu thành các file JSON hay .db trong thư mục project này**. Thay vào đó, Docker lưu ngầm chúng vào các "ổ cứng ảo" gọi là **Volumes** (cụ thể là `postgres_data` và `redis_data` được định nghĩa trong file compose). 
> Hiện tại đống dữ liệu cũ đó vẫn đang nằm "ngủ đông" an toàn bên trong hệ thống của Docker (thường nằm ở `\\wsl$\docker-desktop-data\...` trên Windows). 
> - Nếu bạn muốn dọn sạch chúng cho nhẹ máy, hãy gõ lệnh: `docker compose down -v` (nếu file yml còn đó) hoặc `docker volume prune`.

## 8. Cấu hình IDE (.cursorrules)
- `.cursorrules`: Đây là file hướng dẫn (Prompt) dành riêng cho trình soạn thảo code **Cursor IDE**. Nếu bạn đang dùng Cursor thì cứ giữ lại vì nó giúp AI code chuẩn hơn theo style của dự án. Nếu bạn dùng VSCode/IDE khác thì xóa file này thoải mái vì nó vô tác dụng.

---
**Tóm lại:** Mã nguồn chính của bạn chỉ tập trung gọn gàng trong `app_client` (mã Flutter) và thư mục `backend/app` cùng các file cấu hình như `requirements.txt`, `alembic.ini`. Tất cả các tệp liệt kê bên trên (bao gồm cả các cấu hình Docker cũ) đều có thể "tiễn vong" một cách an toàn!
