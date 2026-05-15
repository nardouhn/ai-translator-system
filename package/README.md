# Autonomous RAG Translation Pipeline (Standard Version)

Chào mừng bạn đến với mô-đun **Agentic RAG Translator**. Đây là phiên bản tiêu chuẩn (chạy Local/API) của hệ thống dịch thuật dựa trên RAG (Retrieval-Augmented Generation) được thiết kế đặc biệt để bóc tách thuật ngữ tự động.

## 📂 Cấu trúc thư mục

```text
package/
├── core/                        # Bộ não cốt lõi
│   ├── engine.py                # Quản lý AI (MLX Local)
│   ├── rag_manager.py           # Quản lý VectorDB (ChromaDB)
│
├── tests/                       # Các bài test hệ thống
│   ├── test_local.py            # Test RAG cơ bản
│   ├── test_edge_cases.py       # Test chống Prompt Injection
│   ├── test_single_words.py     # Test các từ đơn lẻ khó
│
├── crawlers/                    # Hệ thống bọ cào dữ liệu (Crawler)
│   ├── no_ai_crawler.py         # Crawler bằng BeautifulSoup thuần (HTML)
│   └── real_crawler_extractor.py# Crawler siêu việt dùng AI để bóc tách JSON
│
├── app.py                       # API Web Server (FastAPI)
└── docker-compose.yaml          # Quản lý môi trường
```

---

## 🛠 Hướng dẫn Cài đặt & Sử dụng

### 1. Chuẩn bị môi trường
Bật Terminal, trỏ vào thư mục `package` và cài đặt thư viện cần thiết:
```bash
cd package
pip install -r requirements.txt
pip install bs4 requests
```

### 2. Cấu hình AI Engine Đa nền tảng (Cross-Platform)
Hệ thống sử dụng LLM chạy trực tiếp trên máy của bạn và đã được code tối ưu **tự động phát hiện hệ điều hành**:
- Nếu chạy trên **Mac (Apple Silicon)**: Tự động dùng `mlx_lm` để chạy với tốc độ siêu tốc.
- Nếu chạy trên **Windows/Linux**: Tự động chuyển sang `transformers` & `PyTorch` để tận dụng Card NVIDIA (CUDA).

Để đổi Model, AI Engineer không cần sửa code. Chỉ cần đổi cấu hình bằng biến môi trường (Environment Variables) trước khi chạy:

```bash
# Ví dụ 1: Chạy Qwen trên máy Mac
export MODEL_PATH="mlx-community/Qwen2.5-7B-Instruct-4bit"

# Ví dụ 2: AI Engineer chạy Llama 3 trên máy Windows/Linux
export MODEL_PATH="meta-llama/Meta-Llama-3-8B-Instruct"
```

---

## 🚀 Các kịch bản chạy (Run Scripts)

**LƯU Ý:** Luôn đứng ở thư mục `package` để chạy lệnh `python`.

### Kịch bản 1: Cào dữ liệu tự động từ Wikipedia
Tính năng này sẽ truy cập API của Wikipedia, lấy bài viết, dùng AI bóc tách từ vựng, và lưu vào "Sổ Nam Tào" để chống trùng lặp.
```bash
python crawlers/real_crawler_extractor.py
```
*(Bạn cũng có thể chạy thử `python crawlers/no_ai_crawler.py` để xem phương pháp cào truyền thống thất bại như thế nào so với AI).*

### Kịch bản 2: Test dịch thuật với RAG
Chạy lệnh sau để thử nghiệm AI dịch một đoạn văn bản có áp dụng các thuật ngữ vừa cào được:
```bash
python tests/test_edge_cases.py
```

### Kịch bản 3: Khởi động API Server
Nếu muốn tích hợp hệ thống này vào Web/App, bạn bật server FastAPI lên:
```bash
docker-compose up -d
```
Hoặc chạy chay không cần Docker:
```bash
uvicorn app:app --reload --port 8000
```
