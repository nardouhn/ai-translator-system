# Kiến trúc Hệ thống & Luồng Dữ liệu (AI Translator)

Tài liệu này mô tả chi tiết kiến trúc của dự án, luồng dữ liệu của người dùng, và phân tích sâu vào các kỹ thuật (techniques) được sử dụng để giải quyết từng bài toán cụ thể.

## 1. Dịch thuật Văn bản (Text Translation)

### Luồng xử lý:
1. Người dùng nhập text trên ứng dụng Flutter.
2. Ứng dụng gửi HTTP POST request đến FastAPI (`/api/v1/translate`).
3. Backend gọi model AI bên ngoài và nhận kết quả.
4. Trả kết quả về ứng dụng liên tục để hiển thị.

### Kỹ thuật áp dụng (Techniques):
- **Server-Sent Events (SSE) & StreamingResponse:** Thay vì đợi AI dịch toàn bộ văn bản (có thể mất nhiều giây), FastAPI trả về `StreamingResponse` (media type `text/event-stream`). Khi AI sinh ra một từ/câu, nó lập tức được đẩy thẳng về cho client (Flutter). Kỹ thuật này giảm thiểu thời gian chờ (Latency/TTFB), tạo hiệu ứng "Typewriter" trên giao diện người dùng, giúp app luôn mượt mà.
- **Tách luồng xử lý đồng thời (Concurrency):** Sử dụng các hàm `async/await` của FastAPI kết hợp `run_in_threadpool` để không chặn (block) Main Event Loop khi đang xử lý luồng stream từ model.
- **Session Management:** Tự động sinh `X-Session-ID` hoặc đọc từ header. Cho phép theo dõi lượt dùng của từng thiết bị độc lập mà không cần phải xây dựng chức năng đăng nhập phức tạp (Auth).

## 2. Dịch thuật Tài liệu (Document Translation - PDF, DOCX, TXT)

### Luồng xử lý:
1. Người dùng chọn file trên giao diện đa nền tảng (Flutter).
2. Tải file lên FastAPI (`/api/v1/file/translate`).
3. Backend upload tạm lên Cloudflare R2, lưu vào database, trả về `file_id`.
4. Worker ngầm nhận `file_id`, tải file từ R2 xuống, xử lý dịch thuật, và upload bản dịch ngược lại lên R2.
5. App liên tục gọi (Polling) để lấy % tiến độ. Khi 100%, trả về URL tải.

### Kỹ thuật áp dụng (Techniques):

> [!NOTE]
> Xử lý file là tác vụ nặng nên kiến trúc bất đồng bộ và tối ưu bộ nhớ là bắt buộc.

#### a. Kiến trúc Bất đồng bộ (Asynchronous Background Tasks)
- **FastAPI BackgroundTasks & Redis:** Nếu dịch 1 file 5MB bằng AI trực tiếp trên API request, kết nối HTTP có thể bị timeout. Giải pháp là sử dụng `BackgroundTasks` tích hợp sẵn của FastAPI để đưa tiến trình dịch chạy ngầm. Quá trình dịch thuật được thực hiện ở hậu trường sau khi API đã trả về mã `file_id` lập tức cho client (non-blocking API). Mặc dù file `worker.py` (ARQ) và `arq` vẫn còn tồn tại trong source code (chưa dọn dẹp hết), nhưng hệ thống hiện tại đã chuyển sang dùng `BackgroundTasks` của FastAPI cho tiện lợi và giảm phụ thuộc.
- **Progress Tracking (Theo dõi tiến độ):** Trong lúc tác vụ ngầm đang dịch từng phần của file, nó cập nhật phần trăm tiến độ (% progress) thẳng vào in-memory database **Redis** thay vì PostgreSQL. App chỉ cần Polling Redis thông qua một API rất nhẹ để lấy được tiến trình theo thời gian thực mà không làm nặng CSDL chính.

#### b. Giữ nguyên định dạng tài liệu (Format Preservation & Layout Retention)
- **Bóc tách XML cho DOCX:** Sử dụng thư viện `python-docx` để duyệt qua từng đoạn văn (paragraph) và các ô trong bảng (tables) của file Word.
- **Kỹ thuật "Tráo ruột" (Run manipulation):** Trong file `.docx`, text nằm trong các `run` (chứa font chữ, màu sắc, in nghiêng, in đậm). Kỹ thuật ở đây (`document_translator.py`) là xóa text cũ ở các `run` sau, và gán nội dung dịch mới đè vào `run` đầu tiên, đồng thời copy nguyên các thuộc tính font chữ, size, in đậm/nghiêng của đoạn gốc áp sang đoạn mới. Điều này giúp bản dịch giữ cấu trúc giống bản gốc nhất có thể.
- **Xử lý PDF qua DOCX Convert:** Định dạng PDF được compile cứng thành tọa độ hiển thị nên rất khó thay đổi text mà không làm vỡ layout. Giải pháp áp dụng là dùng thư viện convert PDF thành DOCX, sau đó áp dụng quy trình dịch của DOCX.

#### c. Kỹ thuật chia nhỏ ngữ nghĩa (Semantic Chunking)
- Việc nén cả tài liệu 100 trang cho AI sẽ gây lỗi vượt số Token (Token limit exceeded) hoặc làm AI bị "ảo giác" (Hallucination).
- **Thuật toán chia đệ quy (`text_splitter.py`):** Dùng Regex ưu tiên ngắt theo đoạn văn (`\n\n`), nếu đoạn văn vẫn dài thì chia theo kết thúc câu (`. `), rồi theo dấu chấm phẩy (`; `), theo dấu phẩy (`, `) và cuối cùng là ép ngắt cứng nếu đoạn quá `600 ký tự`. Cách chia theo "ngữ nghĩa" này giúp AI dịch đúng văn cảnh mà không bị cắt ngang giữa từ.

#### d. Dịch theo lô (Batch Translation)
- Thay vì gửi 100 request HTTP tuần tự cho 100 câu dịch (mất hàng phút chờ mạng), kỹ thuật này gộp nhiều đoạn văn bản (chunks) vào thành một `List` và gọi API AI (Batching). AI sẽ xử lý nội bộ nhiều text song song và trả về danh sách kết quả, tăng tốc độ xử lý dịch file lên gấp nhiều lần.

#### e. Lưu trữ đám mây an toàn & tiết kiệm (Cloudflare R2 Presigned URLs)
- **S3 API Compatibility:** File gốc tải lên và bản dịch sinh ra không nằm trên ổ cứng VPS để tránh tốn dung lượng và dễ dàng mở rộng nhiều server. Tất cả được đẩy lên R2.
- **Presigned URLs:** Backend sinh ra một đường link tạm thời (có chữ ký và thời hạn sống, ví dụ 10-15 phút). App tải trực tiếp từ máy chủ băng thông rộng của R2 chứ không đi xuyên qua API Backend, giúp backend hoàn toàn "thảnh thơi" về mặt mạng lưới.

## 3. Triển khai đa nền tảng (Cross-Platform Deployment)

### Kỹ thuật áp dụng (Techniques):
- **Single Codebase với Flutter:** Source code tại thư mục `app_client` chỉ cần viết 1 lần bằng Dart. Trình biên dịch (Compiler) của Flutter sẽ vẽ UI gốc không thông qua Webview.
  - Hỗ trợ Native OS: Render engine (Skia/Impeller) vẽ đồ họa tương đương Native App, compile ra file cài đặt độc lập (APK/AAB cho Android, IPA cho iOS, EXE cho Windows).
  - Web Support: Tự động compile ra WASM/JS để chạy mượt mà ngay trên trình duyệt mà không cần cài đặt.
  - Desktop-grade UX: Sử dụng gói `desktop_drop` để kích hoạt tính năng drag-and-drop cho thao tác kéo file trên máy tính bàn.
- **FastAPI Containerization:** Toàn bộ logic server (`backend/Dockerfile`) được gói thành Docker Container. File `docker-compose.yml` định nghĩa hạ tầng liền khối bao gồm Backend Container, Redis Container và PostgreSQL Container.
  - Giúp dự án chạy được trên môi trường dev nội bộ dễ dàng.
  - Dễ dàng đem file `docker-compose` hoặc file cấu hình đính kèm triển khai thẳng lên các hệ thống triển khai CI/CD hoặc các nền tảng PaaS (như Railway) không tốn công cấu hình biến môi trường server phức tạp.
