# Sử dụng Python bản nhẹ để tiết kiệm dung lượng
FROM python:3.10-slim

# Không tạo file .pyc và cho phép log hiển thị ngay lập tức
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Thiết lập thư mục làm việc chính
WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết (Postgres & Build tools)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements vào và cài đặt thư viện Python
# (Đặt ở /app để dùng chung nếu cần, hoặc /app/backend tùy bạn)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code dự án vào container
COPY . .

# Chuyển thư mục làm việc vào sâu bên trong folder backend 
# để Alembic và FastAPI nhìn thấy các file config (.ini, main.py)
WORKDIR /app/backend

# Mở port 8000
EXPOSE 8000

# Lệnh chạy ứng dụng
# --reload để tự động cập nhật khi bạn sửa code bên Antigravity
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]