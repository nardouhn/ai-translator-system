# Biểu Đồ Lớp (Class Diagram) - PlantUML
Bạn có thể copy toàn bộ đoạn mã dưới đây dán vào Draw.io (chọn **Arrange** > **Insert** > **Advanced** > **PlantUML...**) để sinh ra sơ đồ các lớp (Class Diagram) cho hệ thống.

Sơ đồ này tập trung vào 3 nhóm chính: **Database Models**, **Backend Services** và **Frontend Services**, bao gồm cả các thuộc tính và phương thức cốt lõi.

```plantuml
@startuml
!theme plain
skinparam classAttributeIconSize 0
skinparam defaultFontName Arial
skinparam nodesep 70
skinparam ranksep 80
left to right direction

title AI Translator - OOP Class Diagram

' --- Frontend Layer ---
class ApiClient {
  - String baseUrl
  - String sessionId
  + translateTextStream(text: String): Stream
  + translateFile(fileBytes: bytes): Integer
  + checkFileStatus(fileId: Integer): Map
}

' --- Business Logic Layer (OOP Design) ---
abstract class BaseTranslationService {
  # String currentDomain
  # map_domain_to_id(domain: String): Integer
  + {abstract} translate()
}

class TextTranslationService {
  + stream_translate_text(text: String): AsyncGenerator
  + translate()
}

class FileTranslationService {
  + process_file_translation(file_id: Integer, file_path: String)
  - _do_translate_batch(texts: List): List
  + translate()
}

' --- Utility / Helper Classes ---
class TranslatorProvider {
  - Semaphore concurrency_limit
  + translate_with_provider(text: String): Tuple
  + translate_chunk_async(text: String): String
}

class StorageService {
  + upload_file(file: bytes): String
  + get_presigned_url(object_key: String): String
}

class CacheService {
  + mget_cached_translations(domain: String, chunks: List): Map
  + mset_cached_translations(domain: String, mapping: Map)
}

' --- Data Access Layer ---
class FileModel {
  - Integer file_id
  - String original_filename
  - String status
  + save()
  + update_status()
}

class FileSegmentModel {
  - Integer segment_order
  - String source_text
  - String translated_text
  + save()
}

' ==========================================
' OOP RELATIONSHIPS
' ==========================================

' 1. Inheritance (Kế thừa)
BaseTranslationService <|-- TextTranslationService
BaseTranslationService <|-- FileTranslationService

' 2. Composition (Bao gộp dữ liệu)
FileModel "1" *-- "*" FileSegmentModel : contains >

' 3. Aggregation (Tập hợp/Sử dụng dịch vụ)
BaseTranslationService o-- CacheService : uses >
BaseTranslationService o-- TranslatorProvider : uses >
FileTranslationService o-- StorageService : uses >
FileTranslationService o-- FileModel : updates >

' 4. Association (Giao tiếp)
ApiClient --> TextTranslationService : HTTP request >
ApiClient --> FileTranslationService : HTTP request >

@enduml
```
