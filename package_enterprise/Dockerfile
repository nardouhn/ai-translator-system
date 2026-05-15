# Sử dụng image chính thức của Airflow (Đã có sẵn Airflow, nhanh hơn 10 lần)
FROM apache/airflow:2.10.2-python3.10

USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow
WORKDIR /app

# Copy requirements và cài đặt (Airflow đã có sẵn nên chỉ cài thêm thư viện thiếu)
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 \
    -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Copy toàn bộ code vào
COPY --chown=airflow:root . .

# Mặc định Airflow image sẽ dùng các biến môi trường của nó, 
# nhưng chúng ta vẫn giữ các port cũ cho Translator API
EXPOSE 8000

# Lệnh chạy mặc định (Sẽ được docker-compose ghi đè tùy vào service)
CMD ["python", "app.py"]
