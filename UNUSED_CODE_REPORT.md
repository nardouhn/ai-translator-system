# Báo cáo: Các file, hàm và đoạn code thừa trong dự án (App & Web)

Dựa trên việc rà soát toàn bộ source code của phần Backend (FastAPI) và Client (Flutter), dưới đây là danh sách các file, hàm, đoạn code đang bị thừa (không còn được hệ thống sử dụng) cùng với lý do chi tiết.

*(Lưu ý: Báo cáo này đã loại bỏ hoàn toàn phần Admin CMS ra khỏi phạm vi đánh giá)*

---

## 1. Các file thừa có thể xóa bỏ hoàn toàn

### 1.1. `backend/app/worker.py`
- **Tình trạng:** Thừa 100%.
- **Lý do:** Đây là file cấu hình cho thư viện hàng đợi **ARQ** (kết hợp với Redis) để chạy background jobs cho việc dịch tài liệu. Tuy nhiên, toàn bộ logic dịch tài liệu hiện tại đã được bạn chuyển sang sử dụng tính năng **`BackgroundTasks`** tích hợp sẵn của FastAPI (được gọi ở dòng 92 trong file `app/api/v1/file_translate.py` và triển khai chi tiết tại `app/services/file_translation_service.py`). Do hệ thống không chạy tiến trình worker ARQ riêng biệt nữa, file này hoàn toàn vô tác dụng.

### 1.2. `backend/app/services/file_parser.py`
- **Tình trạng:** Thừa 100%.
- **Lý do:** File này chứa duy nhất hàm `extract_text(file: UploadFile)` dùng để đọc file `.txt`. Tuy nhiên, thực tế hệ thống đang xử lý text của mọi loại file (PDF, DOCX, TXT) thông qua các hàm trong `app/services/document_translator.py` (như `translate_txt_document`, `convert_pdf_to_docx`). Hàm `extract_text` này không còn được `import` hay gọi ở bất kỳ file API nào.

### 1.3. `backend/test_api.py`
- **Tình trạng:** Code rác trong quá trình Dev.
- **Lý do:** Đây chỉ là một script test giả lập bằng Python (sử dụng thư viện `requests`) trỏ cứng vào URL `http://127.0.0.1:8000/api/v1/file/translate`. Hiện tại backend của bạn đã lên môi trường Production (Railway) và App Flutter gọi API thông qua biến môi trường thực tế. Script này nên bị xóa để clean source code.

---

## 2. Các thư viện (Dependencies) thừa

### 2.1. Thư viện `arq` (dòng 15 trong `backend/requirements.txt`)
- **Tình trạng:** Cần gỡ bỏ (`pip uninstall arq`).
- **Lý do:** Đi kèm với việc bỏ file `worker.py`, thư viện ARQ không còn được sử dụng để khởi tạo worker ngầm nữa. Việc giữ lại sẽ làm tăng kích thước của Docker image một cách vô ích.

---

## 3. Các tham số, cấu hình, và đoạn code thừa

### 3.1. Truyền dữ liệu `source_lang` và `target_lang`
- **Tình trạng:** Thừa về mặt Logic.
- **Lý do:** Nếu bạn để ý trong đoạn script test (và có thể là trong một số logic API cũ của App Flutter), hệ thống có thói quen truyền lên `source_lang` và `target_lang`. Tuy nhiên, trong mã nguồn Backend thực tế hiện tại (`backend/app/api/v1/file_translate.py`), API Router **hoàn toàn không hứng** hai tham số này nữa. Model AI (Custom AI trên Kaggle) của bạn đã được hardcode / prompt ẩn để tự nhận diện ngôn ngữ và dịch sang Tiếng Việt. Do đó, việc Client (App/Web) gửi tham số này lên chỉ gây lãng phí băng thông payload.

### 3.2. Cấu hình Docker ở thư mục gốc (`d:\ai_trans_demo\docker-compose.yml`)
- **Tình trạng:** Thừa 90% (Nếu chỉ phát triển App/Web).
- **Lý do:** Hiện tại, Backend FastAPI đã được cấu hình độc lập để deploy lên Railway (thông qua `railway.json` và `Dockerfile` riêng trong folder `backend`). File `docker-compose.yml` ở thư mục gốc hiện chủ yếu dùng để khởi chạy **Drupal (Admin)** và **Superset (Analytics)**. Nếu bạn chỉ tập trung vào luồng xử lý của App và Web, thì file docker-compose này không có tác dụng gì cho backend FastAPI. Bạn có thể tách chúng ra một repo riêng biệt cho mảng "Quản trị nội bộ" để project App/Web được "sạch" nhất.

---

## Tóm tắt hành động dọn dẹp khuyên dùng (Clean-up Action)
1. Xóa file `backend/app/worker.py`
2. Xóa file `backend/app/services/file_parser.py`
3. Xóa file `backend/test_api.py`
4. Vào `requirements.txt` xóa dòng `arq`
5. Kiểm tra Flutter App, loại bỏ các tham số `source_lang` / `target_lang` trong các lệnh gọi HTTP nếu có.
