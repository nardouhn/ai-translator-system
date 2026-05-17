# 🚀 AI Translator System - Full Stack Demo

Hệ thống dịch thuật AI chuyên nghiệp tích hợp **Custom AI Model (Qwen)**, **FastAPI Backend**, **Redis Caching** và **Flutter UI**. Hệ thống hỗ trợ dịch văn bản và dịch tài liệu (.pdf, .docx, .txt) với khả năng xử lý song song và tối ưu hóa GPU.

---

## 🛠 Yêu cầu hệ thống (Prerequisites)

Trước khi bắt đầu, hãy đảm bảo máy bạn đã cài đặt:
- **Docker & Docker Compose** (Để chạy Database & Cache)
- **Python 3.10+** (Cho Backend)
- **Flutter SDK** (Cho Frontend)
- **Git**

---

## 🏗 Bước 1: Khởi chạy Hạ tầng (Docker)

Hệ thống sử dụng PostgreSQL để lưu trữ dữ liệu và Redis để cache bản dịch.

1. Mở Terminal tại thư mục gốc của dự án.
2. Chạy lệnh:
   ```bash
   docker-compose up -d
   ```
3. Kiểm tra các container đang chạy:
   ```bash
   docker ps
   ```
   *Bạn sẽ thấy các dịch vụ `postgres` (port 5432) và `redis` (port 6379) đang hoạt động.*

---

## 🐍 Bước 2: Thiết lập Backend (FastAPI)

1. Di chuyển vào thư mục backend:
   ```bash
   cd backend
   ```
2. Tạo môi trường ảo và cài đặt thư viện:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Cấu hình file `.env` (Nếu chưa có, hãy tạo file `.env` dựa trên `.env.example`):
   ```env
   DATABASE_URL=postgresql://admin:password123@localhost:5432/ai_translator
   REDIS_URL=redis://localhost:6379/0
   ```
4. Chạy Migration để tạo cấu trúc bảng Database:
   ```bash
   alembic upgrade head
   ```
5. Khởi chạy Backend Server:
   ```bash
   python -m uvicorn app.main:app --reload
   ```
   *Backend sẽ chạy tại: http://127.0.0.1:8000*

---

## 📱 Bước 3: Thiết lập Frontend (Flutter)

1. Mở một Terminal mới và di chuyển vào thư mục client:
   ```bash
   cd app_client
   ```
2. Lấy các gói phụ thuộc:
   ```bash
   flutter pub get
   ```
3. Chạy ứng dụng (Demo tốt nhất trên Chrome hoặc Desktop):
   ```bash
   flutter run -d chrome
   ```

---

## 🤖 Bước 4: Kết nối AI Model (Kaggle/Ngrok)

Dự án này sử dụng một Model AI tùy chỉnh chạy trên GPU (Kaggle).
1. Đảm bảo Kaggle Server của bạn đang chạy và tunnel qua **Ngrok**.
2. Cập nhật URL Ngrok mới nhất vào file:
   - `backend/app/services/translator_provider.py` -> Biến `CUSTOM_MODEL_URL`.

---

## 🌟 Các tính năng chính để Test Demo

1. **Dịch văn bản (Text Translation)**:
   - Nhập văn bản tối đa 5000 ký tự.
   - Chọn chuyên ngành (General, IT, Medical,...) để thấy sự khác biệt của AI Model.
   - Kiểm tra tốc độ (Lần 2 dịch cùng nội dung sẽ rất nhanh nhờ Redis Cache).

2. **Dịch File (File Translation)**:
   - Upload file `.docx` hoặc `.pdf`.
   - Hệ thống sẽ giữ nguyên định dạng file gốc và trả về file đã dịch.
   - File dịch có thể tải về máy trực tiếp.

3. **Chế độ Sáng/Tối (Dark/Light Mode)**: 
   - Trải nghiệm UI hiện đại với hiệu ứng Glassmorphism.

---

## 📝 Lưu ý quan trọng
- Nếu gặp lỗi `psycopg2`, hãy đảm bảo bạn đã cài `libpq-dev` (Linux) hoặc sử dụng `pip install psycopg2-binary`.
- Giới hạn file upload hiện tại là **20MB**.
- GPU trên Kaggle sẽ xử lý tuần tự (Serial) thông qua cơ chế `gpu_lock` để tránh lỗi tràn bộ nhớ (OOM).

---
*Chúc bạn có trải nghiệm tuyệt vời với AI Translator!*
