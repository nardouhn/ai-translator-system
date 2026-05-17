# Giao diện Flutter UI — AutoTrans

Tài liệu mô tả chi tiết cấu trúc giao diện, widget catalog, design system và các kỹ thuật UI của Flutter App (`app_client`).

> Tham khảo thêm kiến trúc backend: [BACKEND_ARCHITECTURE.md](./BACKEND_ARCHITECTURE.md)

---

## 1. Design System

### 1.1 Màu sắc & Theme

**File:** `lib/app_theme.dart`

Toàn bộ app dùng **Material 3** (`useMaterial3: true`) với 2 theme hoàn chỉnh được định nghĩa tập trung:

| Token | Light Mode | Dark Mode | Mô tả |
|---|---|---|---|
| `primary` | `#7E3FB8` | `#A55EED` | Màu chủ đạo — tím gradient |
| `secondary` | `#B580E0` | `#C794F5` | Accent nhạt hơn |
| `background` | `#F8F5FB` | `#0D0814` | Nền toàn màn hình |
| `surface` | `#FFFFFF` | `#1A1325` | Nền Card/Panel |
| `onSurface` | `#1E1525` | `#EFE8F7` | Màu text chính |

**Typography:** `GoogleFonts.inter` — font Inter áp dụng toàn bộ `textTheme`. `titleLarge` và `bodyMedium` được override với `fontWeight: bold` và màu đúng theme.

**Card System (Material 3):**
```
Light: elevation=4, shadowColor=primary.withOpacity(0.10), radius=20
Dark:  elevation=8, shadowColor=black.withOpacity(0.40), radius=20
```

**NavigationRail** (sidebar điều hướng): Tự đổi màu indicator, icon và label theo theme — không cần style thủ công từng màn hình.

---

## 2. Điều hướng & Chuyển màn hình

**File:** `lib/home_screen.dart`

```
HomeScreen (StatefulWidget)
   │
   ├── _selectedIndex = 0 → TextTranslationView
   └── _selectedIndex = 1 → FileTranslationView
```

**Kỹ thuật AnimatedSwitcher:**
```dart
AnimatedSwitcher(
  duration: Duration(milliseconds: 220),
  child: KeyedSubtree(
    key: ValueKey<int>(_selectedIndex),  // ← key thay đổi → trigger animation
    child: _selectedIndex == 0 ? TextTranslationView(...) : FileTranslationView(...)
  )
)
```
- `AnimatedSwitcher` tự động phát hiện `child` thay đổi (nhờ `ValueKey`) và thực hiện cross-fade animation 220ms — chuyển màn hình mượt mà, không cần Navigator hay route.
- Không dùng state management package (Provider/Bloc/Riverpod) — state đơn giản đủ quản lý qua `setState` + callback truyền xuống.

---

## 3. Màn hình — Dịch Văn Bản

**File:** `lib/features/text_translation_view.dart`

#### Layout:
```
┌─────────────────────────────────────────────┐
│  TranslationTopBar (Logo + Nav + Theme btn) │
├─────────────────────────────────────────────┤
│  DomainDropdown (chọn lĩnh vực)             │
├──────────────────────────────────────────── │
│  TranslationDualPanel                        │
│  ┌──────────────┬───┬────────────────────┐  │
│  │ English Panel│ → │ Vietnamese Panel   │  │
│  │ [Text input] │   │ [Translated text]  │  │
│  │ 🔊  🎤  Char │   │ 🔊  📋  ↗       │  │
│  └──────────────┴───┴────────────────────┘  │
│  [Error message nếu có]                      │
│  TranslationBottomNote (ghi chú disclaimer) │
└─────────────────────────────────────────────┘
```

#### State được quản lý:
| State | Kiểu | Vai trò |
|---|---|---|
| `_inputController` | `TextEditingController` | Nội dung ô nhập |
| `_outputText` | `String` | Text dịch accumulate từ SSE |
| `_isLoading` | `bool` | Hiển thị spinner trên nút Translate |
| `_errorMessage` | `String` | Hiện lỗi dưới panel |
| `_selectedDomain` | `String` | Domain chọn từ dropdown |
| `_isSpeakingSource/Target` | `bool` | Toggle icon Stop/Play TTS |
| `_isListening` | `bool` | Toggle icon Mic đỏ khi đang nghe |

#### Responsive Strategy:
- `LayoutBuilder` đo `constraints.maxWidth` → `isMobile = width < 600`
- `base scale = (width / 1600).clamp(0.72, 1.0)` — mọi kích thước (font, padding, icon) nhân với `base` → tự scale tuyến tính theo màn hình
- Mobile: Column layout (input trên, output dưới)
- Desktop/Tablet: Row layout 2 cột song song (width: 1500 * scale)

---

## 4. Màn hình — Dịch File

**File:** `lib/features/file_translation_view.dart`

#### Layout:
```
┌─────────────────────────────────────────────────────┐
│  TranslationTopBar                                  │
├─────────────────────────┬───────────────────────────┤
│  Main Card              │  Queue Card               │
│                         │                           │
│  "File Translation"     │  "Translation Queue"      │
│  description text       │                           │
│                         │  [QueueItemCard]          │
│  [UploadDropzone]       │  ├── 📄 file.pdf          │
│    hoặc                 │  │   1.2MB · Processing   │
│  [FileInfoCard]         │  │   ████░░ 60%           │
│                         │  │                        │
│  DomainDropdown         │  └── 📄 report.docx       │
│  [EN → VI labels]       │      0.8MB · Done ✅ ↓   │
│  [Translate btn]        │                           │
└─────────────────────────┴───────────────────────────┘
```

#### Queue System:
```dart
final List<Map<String, dynamic>> _activeQueue = [];

// Mỗi item trong queue có:
{
  'fileName': 'report.pdf',
  'fileType': 'pdf',
  'fileSize': '1.2 MB',
  'status': 'Processing (45%)...',
  'progress': 0.45,              // 0.0 → 1.0
  'fileUrl': 'https://...',      // R2 presigned URL khi done
  'fileContentB64': '...',       // base64 fallback nếu không có URL
}
```

Queue hỗ trợ **nhiều file đồng thời** (mỗi file một `QueueItemCard` với progress bar riêng).

---

## 5. Widget Catalog — 9 Components

#### 1. `TranslationTopBar`
- Logo `AutoTrans` + icon `g_translate_rounded` (bên trái)
- Nav button → chuyển sang màn hình kia (file hoặc text, label đổi theo context)
- IconButton toggle Dark/Light mode (icon `light_mode` / `dark_mode`)
- **Responsive**: Trên mobile ẩn text "AutoTrans", chỉ giữ icon

#### 2. `TranslationDualPanel`
- 2 pane (Source / Target) bố cục nằm ngang trên desktop, dọc trên mobile
- **Source pane** (trái): `TextField` với `maxLength=5000`, `expands=true` (fill height)
- **Target pane** (phải): `SelectableText` — user có thể chọn và copy text
- Character counter `{n} / 5000` ở footer trái của source pane
- **Translate button**: Hình tròn gradient tím (`#8B2CFF → #D22DFF`), boxShadow glow 22px, hiển thị `CircularProgressIndicator` khi loading
- Divider dọc (desktop) / ngang (mobile) giữa 2 pane

#### 3. `UploadDropzone`
- Package `desktop_drop` — `DropTarget` wrapper bắt sự kiện kéo thả file
- `DottedBorder` (package `dotted_border`) — viền đứt nét thay đổi màu khi đang drag
- Background fill tím nhạt khi drag over (`primaryColor.withOpacity(0.15)`)
- "Browse Files" button với gradient + `file_picker` dialog khi tap
- Hint text "Drag and drop PDF, DOCX, or TXT here" + size limit warning

#### 4. `FileInfoCard`
- Hiển thị file đã chọn: icon loại file, tên file, nút ✕ để bỏ chọn
- Thay thế `UploadDropzone` sau khi user chọn file thành công

#### 5. `SidebarQueueWidget` + `QueueItemCard`
- `ListView.separated` với `shrinkWrap: true` (không scroll riêng, parent scroll)
- Mỗi card: icon file (🔴 PDF / 🔵 DOCX / ⚫ TXT), tên, size, status text
- `LinearProgressIndicator` (height=4px, bo góc 4px) hiện khi `0 < progress < 1.0`
- Button thay đổi theo trạng thái: `Download ↓` khi done, `Delete 🗑️` khi lỗi, `...` khi đang dịch

#### 6. `DomainDropdown`
- Dropdown chọn lĩnh vực: General / Medical / Technical / Economic
- Style custom (không dùng default Flutter dropdown) — bo góc, màu theo theme
- `scale` parameter — tự scale kích thước theo màn hình

#### 7. `DomainSelector`
- Biến thể khác của domain selection (chip/tab style)

#### 8. `TranslationBottomNote`
- Disclaimer nhỏ ở cuối màn hình text translation
- Thông báo về giới hạn và chất lượng dịch AI

#### 9. `FileTrannsslationPanel`
- Panel tổng hợp cho màn hình file (dùng nội bộ)

---

## 6. Packages Flutter

| Package | Vai trò |
|---|---|
| `http` | HTTP client + SSE streaming |
| `file_picker` | Chọn file qua dialog chuẩn (hỗ trợ Web bytes) |
| `desktop_drop` | Drag & Drop file (Web + Desktop) |
| `dotted_border` | Viền đứt nét cho Dropzone |
| `url_launcher` | Mở Presigned URL trong browser ngoài (Mobile) |
| `universal_html` | DOM API cho Web (Blob, AnchorElement download) |
| `flutter_tts` | Text-to-Speech đa nền tảng |
| `speech_to_text` | Speech-to-Text (Mic input) |
| `shared_preferences` | Local cache key-value (Tier 1 cache) |
| `crypto` | MD5 hash cho cache key generation |
| `google_fonts` | Font Inter từ Google Fonts |


