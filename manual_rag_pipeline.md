# Kiến trúc Hệ thống RAG Thủ công (Manual RAG Pipeline)

Tài liệu này giải thích quy trình hoạt động của hệ thống Retrieval-Augmented Generation (RAG) khi được xây dựng "thủ công" (không qua thư viện trung gian như LangChain), tương đương với những gì đã được triển khai trong mã nguồn hiện tại của dự án.

## 1. Tổng quan Quy trình (High-Level Overview)

Hệ thống RAG thủ công được chia làm hai pha chính:
1. **Pha Indexing (Đánh chỉ mục)**: Chuyển đổi tri thức từ file thô vào cơ sở dữ liệu vector.
2. **Pha Inference (Suy luận)**: Khi người dùng đặt câu hỏi, hệ thống tìm kiếm thông tin liên quan và đưa vào prompt cho LLM.

---

## 2. Pha Indexing: Xây dựng Cơ sở Tri thức

Quy trình này được thực hiện trong `master_indexer.py`:

1. **Thu thập dữ liệu (Data Loading)**: Nạp các file JSON thuật ngữ (`medical_glossary.json`, `economic_context.json`, v.v.).
2. **Tiền xử lý (Pre-processing)**: Làm sạch văn bản, chuẩn hóa các cặp Anh - Việt.
3. **Tạo Embedding**: Sử dụng mô hình `all-MiniLM-L6-v2` (chạy offline) để biến mỗi đoạn văn bản thành một vector 384 chiều.
4. **Lưu trữ VectorDB**: Lưu các vector và metadata (nghĩa tiếng Việt, domain) vào **ChromaDB**.

---

## 3. Pha Inference: Truy xuất và Dịch thuật

Quy trình này diễn ra mỗi khi có yêu cầu dịch thuật (`prompt_config.py`):

### Bước 1: Truy xuất Sơ bộ (Stage 1 Retrieval)
- Sử dụng thuật toán **Vector Search** (thường là Cosine Similarity) để tìm nhanh ~50 ứng viên có độ tương đồng cao nhất với câu hỏi của người dùng trong ChromaDB.

### Bước 2: Reranking (Stage 2 - Đánh giá lại)
- Do Vector Search đôi khi chỉ tìm theo từ khóa, chúng ta sử dụng một mô hình **Cross-Encoder** (`ms-marco-MiniLM-L-6-v2`).
- Mô hình này so sánh trực tiếp "Câu hỏi" và "Từng ứng viên" để chấm điểm chính xác mức độ liên quan.
- Kết quả: Chọn ra **Top 10** ngữ cảnh tốt nhất.

### Bước 3: Xây dựng Expert Prompt
- Hệ thống lấy Top 10 kết quả đã rerank, phân loại chúng thành:
    - **Glossary (Từ điển)**: Các từ đơn lẻ xuất hiện trong câu.
    - **Translation Memory (Ngữ cảnh)**: Các câu ví dụ dài hơn.
- Tất cả được nhét vào một **Template Prompt chuyên gia** với cấu trúc:
    ```text
    ### Instruction: Bạn là dịch giả chuyên nghiệp...
    ### Glossary: {từ điển được tìm thấy}
    ### Context: {ví dụ tìm thấy}
    ### Input: {câu cần dịch}
    ### Response:
    ```

### Bước 4: Suy luận với LLM (Inference)
- Toàn bộ prompt được gửi tới mô hình **Qwen2.5 (Fine-tuned)**.
- Mô hình dựa trên tri thức được "nhắc bài" trong prompt để đưa ra bản dịch đúng thuật ngữ chuyên ngành.

---

## 4. Ưu điểm của Cách làm Thủ công

- **Kiểm soát tuyệt đối**: Bạn biết chính xác từng vector được tính toán và truyền đi như thế nào.
- **Hiệu năng**: Không bị overhead bởi các lớp trừu tượng của thư viện lớn.
- **Tối ưu hóa**: Dễ dàng tùy chỉnh logic Reranking hoặc Prompting theo đặc thù của mô hình Qwen.

---

> [!TIP]
> Việc chuyển sang LangChain ở bước tiếp theo sẽ giúp chúng ta quản lý các thành phần này một cách có hệ thống hơn, nhưng logic cốt lõi vẫn tuân theo quy trình 4 bước trên.
