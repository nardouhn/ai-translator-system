# Cấu Trúc Kiến Trúc Hệ Thống (PlantUML)
Bạn có thể copy toàn bộ đoạn mã PlantUML dưới đây và dán vào [PlantText](https://www.planttext.com/), [PlantUML Web](https://www.plantuml.com/plantuml/uml/) hoặc plugin tích hợp trong Draw.io (Arrange > Insert > Advanced > PlantUML) để sinh ra sơ đồ kiến trúc hoàn chỉnh.

```plantuml
@startuml
!theme plain
left to right direction
skinparam componentStyle rectangle
skinparam backgroundColor #FFFFFF
skinparam arrowColor #333333
skinparam defaultFontName Arial
skinparam nodesep 50
skinparam ranksep 70

title AI Translator - High Level Architecture

package "1. Client" #E3F2FD {
  component "Flutter App / Web" as Client
}

package "2. Backend Server" #E8F5E9 {
  component "API Gateway" as Gateway
  component "Text Translation Service" as TextSvc
  component "File Translation Worker" as FileSvc
}

package "3. Data & Storage" #F9FBE7 {
  database "Redis (Cache & State)" as Redis
  database "PostgreSQL (Database)" as Postgres
  cloud "Cloudflare R2 (Storage)" as Storage
}

cloud "4. External AI" #F3E5F7 {
  component "Kaggle GPU Model" as AI
}

' --- Main Data Flow ---
Client ==> Gateway : HTTP / SSE

Gateway --> TextSvc
Gateway --> FileSvc
Gateway --> Storage

TextSvc ==> AI
FileSvc ==> AI

' --- Secondary Flow ---
TextSvc ..> Redis
TextSvc ..> Postgres

FileSvc ..> Redis
FileSvc ..> Postgres
FileSvc ..> Storage

@enduml
```

### Hướng dẫn sử dụng trong Draw.io:
1. Truy cập [app.diagrams.net](https://app.diagrams.net/)
2. Tạo một bản vẽ trống.
3. Nhấp vào nút dấu cộng **`+`** trên thanh công cụ (hoặc menu **Arrange** > **Insert** > **Advanced** > **PlantUML...**).
4. Dán toàn bộ khối code nằm trong ```` ```plantuml .... ``` ```` ở trên vào ô.
5. Bấm **Insert**, draw.io sẽ tự động vẽ ra toàn bộ các khối kiến trúc và mũi tên cực kỳ chuyên nghiệp!
