# Kiến trúc Hệ thống — AI Translator (AutoTrans)

Tài liệu phân tích toàn diện kiến trúc, luồng dữ liệu và các kỹ thuật kỹ thuật được sử dụng trong toàn bộ dự án (Backend FastAPI + Flutter App Client).

---

## Tổng quan Hệ thống

```
┌─────────────────────────────────────────────────────────┐
│               Flutter App (AutoTrans)                   │
│   Web · Android · iOS · Windows · macOS · Linux        │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP / SSE
┌────────────────────▼────────────────────────────────────┐
│             FastAPI Backend (Railway)                   │
│  /api/v1/translate        → Text Translation (SSE)     │
│  /api/v1/file/translate   → File Upload + Background   │
│  /api/v1/test-cloud       → Health Check               │
└────┬──────────────┬──────────────────┬──────────────────┘
     │              │                  │
┌────▼───┐  ┌───────▼──────┐  ┌───────▼────────┐
│Supabase│  │ Upstash Redis│  │ Cloudflare R2  │
│(Postgres)│  │(Cache+RateL.)│  │(File Storage)  │
└────────┘  └──────────────┘  └────────────────┘
                                       │ ngrok tunnel
                              ┌────────▼───────┐
                              │  Custom AI Model│
                              │  (Kaggle GPU)   │
                              └────────────────┘
```

---

## 1. Backend (FastAPI)

### 1.1 Cấu hình & Khởi động

**File:** `app/main.py`, `app/settings.py`

**Kỹ thuật:**
- **Pydantic Settings** (`pydantic-settings`): Toàn bộ cấu hình nhạy cảm (`DATABASE_URL`, `REDIS_URL`, `R2_ACCESS_KEY_ID`...) được khai báo trong class `Settings(BaseSettings)`. Pydantic tự động đọc từ biến môi trường hoặc file `.env`, có validation kiểu dữ liệu tự động — không bao giờ hardcode secret vào code.
- **Dynamic CORS**: Đọc biến môi trường `FRONTEND_URL` (hỗ trợ nhiều URL phân cách bằng dấu phẩy) để cấu hình `CORSMiddleware` linh hoạt cho cả môi trường dev và production.
- **Port động**: `uvicorn` đọc `PORT` từ biến môi trường — tương thích hoàn toàn với Railway/Render/Fly.io vốn tự gán port ngẫu nhiên.

---

### 1.2 Session Management (Không cần Auth)

**File:** `app/services/session_service.py`, `app/api/v1/translate.py`, `app/api/v1/file_translate.py`

**Kỹ thuật:**
- Hệ thống **không dùng Login/JWT**. Thay vào đó, mỗi thiết bị/trình duyệt tự nhận dạng bằng một `session_id` dạng UUID4.
- Nếu request không có header `X-Session-ID` → Backend tự sinh UUID mới, lưu vào DB (bảng `session` — ghi IP address và User-Agent), và trả về trong response header `X-Session-ID`.
- Lần sau, client gửi lại `X-Session-ID` → Backend tái sử dụng session đó để theo dõi lịch sử và Rate Limiting.
- Lưu trữ Session sử dụng **Cloudflare-Connecting-IP header** (ưu tiên hơn `request.client.host`) để lấy đúng IP thật khi đứng sau Cloudflare proxy.

---

### 1.3 Rate Limiting (Chống Spam)

**File:** `app/services/rate_limit_service.py`

**Kỹ thuật: Redis Atomic Pipeline (INCR + EXPIRE)**
```
key = "rate_limit:{session_id}"

INCR key   → đếm số request trong window
EXPIRE key 60  → TTL 60 giây

Nếu count > 20 → HTTP 429 Too Many Requests
```

**Điểm quan trọng:** Dùng `pipeline(transaction=False)` để gửi 2 lệnh `INCR` và `EXPIRE` trong cùng một round-trip TCP. Nếu gửi tuần tự (2 lệnh riêng), server có thể crash giữa 2 lệnh → key tồn tại mãi không bao giờ expire (memory leak). Pipeline giải quyết race condition này.

---

### 1.4 Luồng Dịch Văn Bản (Text Translation)

**Files:** `app/api/v1/translate.py` → `app/services/translation_service.py` → `app/services/translator_provider.py`

#### Luồng hoàn chỉnh:

```
POST /api/v1/translate  {text, domain}
         │
         ▼
1. Kiểm tra DB cache (bảng translation, theo text_hash + domain_id)
   └── HIT → stream bản dịch cũ về ngay, return
         │
         ▼
2. Semantic Chunking (text_splitter.py)
   └── Cắt text thành chunks ≤600 ký tự theo thứ tự ưu tiên:
       \n\n > "." > ";" > "," > space > hard-split
         │
         ▼
3. Normalize mỗi chunk (strictly_normalize_text)
   └── Xóa zero-width chars (\u200b, \u200c, \u200d, \ufeff)
   └── Collapse whitespace thành 1 space
   └── Chunk rỗng sau normalize → bỏ qua (skip)
         │
         ▼
4. Batch Redis MGET — 1 round-trip cho N chunks
   └── HIT  → stream chunk đó về App ngay
   └── MISS → gọi AI Model
         │
         ▼
5. Gọi Custom AI Model (ngrok endpoint)
   └── Semaphore giới hạn 2 concurrent requests (tránh quá tải GPU đơn)
   └── Retry logic: 3 lần, exponential backoff (2s, 4s, 8s)
   └── Timeout: 300 giây/request
   └── Kiểm tra kết quả: [ERROR...], [TIMEOUT], [FAILED] → fail ngay
   └── None / Empty → fail ngay
   └── Thành công → stream về App, lưu Redis (MSET pipeline)
         │
         ▼
6. Ghi DB (background threadpool):
   └── Thành công → lưu bảng translation (cache DB dài hạn) + Logs(success)
   └── Thất bại   → Logs(failed, reason) — KHÔNG lưu bảng translation
```

**Kỹ thuật SSE (Server-Sent Events):**
- FastAPI trả về `StreamingResponse` với `media_type="text/event-stream"`.
- Format mỗi event: `data: {"chunk": "văn bản dịch"}\n\n`
- Mỗi chunk dịch xong được `yield` ngay lập tức thay vì đợi toàn bộ.
- Client (Flutter) nhận stream bằng `http.Request.send()` rồi lắng nghe `.stream`.

**Kỹ thuật Thread Safety:**
- Hàm streaming là `async generator` — chạy trên event loop.
- Các thao tác DB dùng SQLAlchemy sync được bọc trong `run_in_threadpool` để không block event loop.
- Cache Redis dùng `asyncio.create_task(mset_cached_translations(...))` — chạy nền không chặn stream.

---

### 1.5 Luồng Dịch Tài Liệu (File Translation)

**Files:** `app/api/v1/file_translate.py` → `app/services/file_translation_service.py` → `app/services/document_translator.py`

#### Luồng hoàn chỉnh:

```
POST /api/v1/file/translate  (multipart: file + domain)
         │
         ▼
1. Validate: định dạng (pdf/docx/txt), kích thước ≤5MB
         │
         ▼
2. Upload file gốc lên Cloudflare R2
   └── Key: "{uuid4}_{original_filename}"
         │
         ▼
3. Tạo bản ghi File trong PostgreSQL (status=pending)
   └── Trả về {file_id, status: "pending"} cho client ngay
         │
         ▼
4. BackgroundTasks.add_task(process_file_translation, ...)
   └── Tiến trình dịch chạy ngầm, HTTP response đã về client rồi
         │
         ▼ (Background)
5. Worker tải file từ R2 → local /tmp
         │
         ▼
6. Xử lý theo định dạng:
   ├── TXT: decode UTF-8 (fallback latin-1) → dịch từng dòng
   ├── DOCX: python-docx parse XML → lấy paragraphs + table cells
   │         → dịch theo batch → "tráo ruột" run (giữ font/bold/italic)
   └── PDF: pdf2docx convert → xử lý như DOCX → LibreOffice convert ngược lại PDF
         │
         ▼
7. Batch Translate với 2-tier cache:
   └── Cắt mỗi paragraph thành sub-chunks ≤600 chars
   └── MGET TẤT CẢ sub-chunks 1 lần duy nhất từ Redis
   └── MISS → gọi AI → kiểm tra fail → raise Exception nếu fail
   └── Flush cache mỗi 10 entries mới (asyncio.create_task)
   └── Cập nhật tiến độ vào Redis: "job_progress:{file_id}" = % (setex TTL 24h)
         │
         ▼
8. Upload bản dịch lên R2:
   └── Key: "translations/{uuid4}/{filename}_translated.ext"
   └── ContentType đúng (docx/pdf/txt)
   └── ContentDisposition: attachment để browser auto-download
         │
         ▼
9. Cập nhật DB:
   └── file_row.status = success, file_row.file_path = R2 key
   └── Lưu FileSegment (source + translated text từng đoạn)
   └── Logs(status=success)
   └── Redis progress = 100%
```

#### Kỹ thuật Format Preservation (Giữ định dạng DOCX):

```python
# document_translator.py — "Tráo ruột" kỹ thuật:
for paragraph in doc.paragraphs:
    # 1. Lưu style của run đầu tiên có nội dung
    first_run = paragraph.runs[0]
    font_name, font_size, bold, italic, underline, color = ...

    # 2. Xóa text của TẤT CẢ runs
    for run in paragraph.runs:
        run.text = ""

    # 3. Gán text dịch vào run[0], restore nguyên style
    paragraph.runs[0].text = translated_text
    paragraph.runs[0].font.name = font_name
    # ... restore bold, italic, underline, color
```

#### Kỹ thuật PDF Conversion:
- **pdf2docx**: Convert PDF → DOCX (giải mã tọa độ PDF thành paragraphs Word).
- **LibreOffice headless**: Convert DOCX → PDF sau khi dịch xong (`subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", ...])`).

---

### 1.6 Storage Service (Cloudflare R2)

**File:** `app/services/storage_service.py`

**Kỹ thuật:**
- **S3-compatible API**: R2 tương thích hoàn toàn với AWS S3 API. Dùng thư viện `aioboto3` (async boto3) để upload/download không block event loop.
- **Presigned URL**: Thay vì stream file qua Backend (tốn bandwidth), Backend chỉ sinh ra một URL có chữ ký (signed) với TTL 1 giờ. Client tải trực tiếp từ R2 CDN — Backend không tốn băng thông.
- **ContentDisposition header**: Set `attachment; filename="..."` ngay lúc upload để browser tự động download file đúng tên khi truy cập Presigned URL.
- **MIME type mapping**: Map đúng Content-Type cho từng định dạng (docx → `application/vnd.openxmlformats...`) để browser nhận dạng file đúng.

---

### 1.7 Translation Provider & Resilience

**File:** `app/services/translator_provider.py`

**Kỹ thuật:**
- **Semaphore (asyncio.Semaphore(2))**: Giới hạn tối đa 2 request song song đến AI Model. Model chạy trên GPU đơn (Kaggle) — nếu có 10 request đồng thời sẽ OOM crash.
- **Shared HTTP Client (Connection Pooling)**: Dùng một `httpx.AsyncClient` duy nhất được tái sử dụng (singleton pattern với lazy init). Tránh tạo TCP connection mới cho mỗi request — giảm latency đáng kể.
- **Exponential Backoff Retry**: Thất bại → chờ 2^(attempt+1) giây → thử lại. Tối đa 3 lần retry.
- **Failure Detection**: Kết quả trả về có prefix `[ERROR...]`, `[TIMEOUT]`, `[FAILED]` → được nhận biết là thất bại, không bao giờ lưu cache, không nhét vào file output.

---

### 1.8 Cache System (2 tầng)

**File:** `app/services/cache_service.py`, `app/services/redis_client.py`

#### Tầng Server — Redis (Upstash)

| Hàm | Mô tả |
|---|---|
| `mget_cached_translations(domain, chunks)` | Batch GET N keys trong 1 round-trip |
| `mset_cached_translations(domain, mapping)` | Batch SET N keys dùng Pipeline |

**Cache Key Format:**
```
translate:v8:{domain}:en:vi:{SHA256(normalized_text)}
```
- `v8` = Model Version — đổi số này để invalidate toàn bộ cache cũ
- Normalized text: xóa invisible chars, collapse whitespace trước khi hash → đảm bảo `"Hello  World"` và `"Hello World"` cùng key

**Connection Pool**: `ConnectionPool.from_url()` → một pool dùng chung cho toàn app, không tạo connection mới mỗi request. Hỗ trợ SSL (`rediss://`) cho Upstash cloud.

**TTL**: 7 ngày (`604800` giây) cho mọi translation cache key.

---

### 1.9 Database Schema

**File:** `app/db/models.py` (SQLAlchemy 2.0 Mapped Columns)

| Bảng | Mục đích | Quan hệ |
|---|---|---|
| `session` | Lưu thiết bị (IP + User-Agent + session_id) | 1:N với translation, file, logs |
| `domain` | Master data: general/medical/technical/economic | FK trong translation, file |
| `translation` | Cache DB dài hạn: source → translated text + hash | Unique(text_hash, domain_id) |
| `file` | Metadata file upload + trạng thái + R2 key | 1:N với file_segment |
| `file_segment` | Từng đoạn dịch trong file (source + translated) | N:1 với file |
| `logs` | Audit log mọi request (success/failed + thời gian) | FK session, translation, file |

**Kỹ thuật Alembic**: Schema migration được quản lý bằng Alembic. Không bao giờ sửa DB thủ công — mọi thay đổi schema tạo file migration versioned.

---

### 1.10 Health Check API

**File:** `app/api/v1/health.py` — Endpoint `GET /api/v1/test-cloud`

Kiểm tra đồng thời 3 dịch vụ cloud:
1. **PostgreSQL**: `SELECT 1` — xác nhận connection DB
2. **Redis**: `PING` — xác nhận connection Redis
3. **Cloudflare R2**: `head_bucket` — xác nhận credential R2 hợp lệ

Trả về status report từng dịch vụ với ✅/❌. Dùng để debug production mà không cần access server.

---

## 2. Flutter App Client (AutoTrans)

### 2.1 Cấu trúc App

```
lib/
├── main.dart              → Entry point, ThemeMode state
├── app_theme.dart         → Light/Dark theme definitions
├── home_screen.dart       → Điều hướng giữa 2 màn hình chính
├── features/
│   ├── text_translation_view.dart   → Màn hình dịch văn bản
│   └── file_translation_view.dart   → Màn hình dịch file
├── services/
│   ├── api_service.dart             → HTTP client, SSE consumer
│   └── local_cache_service.dart     → Cache local SharedPreferences
└── widgets/                         → 9 reusable components
    ├── translation_dual_panel.dart  → Panel 2 cột input/output
    ├── upload_dropzone.dart         → Drag & Drop file zone
    ├── sidebar_queue.dart           → Queue dịch file + progress bar
    ├── domain_dropdown.dart         → Dropdown chọn lĩnh vực
    └── ...
```

### 2.2 Theme System

**File:** `app_theme.dart`

- Định nghĩa 2 theme hoàn chỉnh (Light/Dark) dùng `ThemeData` + `ColorScheme`.
- `ThemeMode` state được quản lý ở root widget (`AutoTransApp`) và truyền xuống qua callback `onToggleTheme` — không cần state management package.
- Google Fonts tích hợp qua package `google_fonts`.

### 2.3 Text Translation View

**Kỹ thuật:**
- **SSE Consumer**: Dùng `http.Request.send()` nhận về `StreamedResponse`, lắng nghe `.stream.transform(utf8.decoder)`. Buffer từng fragment, split theo `\n\n`, parse JSON từng event `data: {...}`.
- **Real-time Typewriter Effect**: Mỗi SSE event nhận được gọi `setState(() => _outputText += chunk)` → text chạy ra từng chữ trên giao diện.
- **Speech-to-Text** (`speech_to_text`): Nhận diện giọng nói tiếng Anh (`localeId: 'en_US'`), điền thẳng vào input field.
- **Text-to-Speech** (`flutter_tts`): Phát âm cả văn bản gốc (tiếng Anh) và bản dịch (tiếng Việt) với locale phù hợp.
- **Local Cache** (`SharedPreferences`): Trước khi gọi API, kiểm tra cache thiết bị theo key `MD5(text + targetLang + domain)`. HIT → hiển thị ngay, không tốn network.
- **Character Limit**: Validate ≤5000 ký tự ngay trên client trước khi gửi request.

### 2.4 File Translation View

**Kỹ thuật:**
- **Adaptive Polling**: 20 request đầu (40 giây) → cách 2 giây/lần. Sau đó → cách 5 giây/lần. Tiết kiệm pin cho mobile file lớn mà vẫn responsive.
- **Network Resilience**: Đếm `consecutiveErrors`. Nếu poll thất bại liên tiếp 15 lần → throw Exception. Mỗi poll thành công reset counter về 0.
- **Drag & Drop** (`desktop_drop`): Kéo thả file trực tiếp vào vùng upload — kỹ thuật desktop-grade dùng được trên Web và Desktop.
- **File Picker** (`file_picker`): Chọn file qua dialog chuẩn, whitelist chỉ `pdf/docx/txt`. Trên Web dùng `withData: true` để đọc bytes (vì Web không có đường dẫn file).
- **Cross-platform Download**:
  - Web: Tạo `Blob` → `AnchorElement` với `download` attribute → click programmatically
  - Mobile/Desktop: Dùng `url_launcher` mở Presigned URL trong browser ngoài

### 2.5 API Service

**File:** `lib/services/api_service.dart`

- **Environment Switching**: Flag `useLocalBackend` — `false` → trỏ thẳng vào Railway production. `true` → tự phát hiện host (Web dùng `Uri.base.host`, Mobile dùng LAN IP).
- **Session Persistence**: `static String? sessionId` — lưu trong memory suốt vòng đời app. Đọc từ response header `X-Session-ID`, gửi lại trong header mọi request tiếp theo.
- **Timeout**: Text streaming 120 giây, File upload 60 giây, Status polling 15 giây.

---

## 3. Hạ tầng & Triển khai

### 3.1 Backend — Railway

```dockerfile
# Dockerfile
FROM python:3.11-slim
RUN apt-get install -y libreoffice-core libreoffice-writer  # PDF conversion
RUN pip install -r requirements.txt
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1
```

- **LibreOffice trong Docker**: Cài thẳng vào image để có thể convert DOCX → PDF headless.
- **Single Worker**: `--workers 1` vì app dùng in-memory state (Semaphore, shared httpx client). Multi-worker sẽ tạo nhiều process riêng biệt không chia sẻ state.

### 3.2 Flutter — Cross-Platform Build Matrix

| Lệnh | Output | Nơi deploy |
|---|---|---|
| `flutter build web` | `build/web/` (JS + WASM) | Vercel / Netlify / Cloudflare Pages |
| `flutter build apk` | `.apk` | Google Play Store / side-load |
| `flutter build appbundle` | `.aab` | Google Play Store (tối ưu hơn apk) |
| `flutter build ipa` | `.ipa` | Apple App Store (cần macOS + Xcode) |
| `flutter build windows` | `.exe` | Direct distribute / Microsoft Store |
| `flutter build macos` | `.app` | Direct distribute / Mac App Store |

### 3.3 Môi trường Cloud

| Dịch vụ | Vai trò | Ghi chú |
|---|---|---|
| **Railway** | Host FastAPI Backend | Auto-deploy từ Git push |
| **Supabase** | PostgreSQL Database | Connection pooling built-in |
| **Upstash** | Redis | Serverless Redis, hỗ trợ `rediss://` SSL |
| **Cloudflare R2** | Object Storage | S3-compatible, free egress bandwidth |
| **Kaggle + ngrok** | Custom AI Model | GPU miễn phí, expose qua ngrok tunnel |

---

## 4. Sơ đồ Luồng Cache (2 tầng)

---
