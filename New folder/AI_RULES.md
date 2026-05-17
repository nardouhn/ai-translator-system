# SYSTEM INSTRUCTIONS: AI TRANSLATOR FULLSTACK (ANTIGRAVITY AGENT OPTIMIZED)

**Stack:** Flutter (UI) | Python FastAPI (API) | PostgreSQL (DB) | Redis (Cache) | CMS (Admin)

---

## 1. AGENTIC WORKFLOW & WORKSPACE MANAGEMENT
- **Direct File Editing:** You are an Antigravity Agent. Do NOT output code blocks in the chat unless you need to explain a complex concept. Use your editor capabilities to apply changes directly to the workspace files.
- **Context Gathering:** Do not ask the user to paste code. Use your workspace access to read `pubspec.yaml`, `requirements.txt`, and any relevant files to build your own context before acting.
- **Planning & Artifacts:** For complex or multi-file features, generate an Implementation Plan (Artifact) first. Wait for user feedback or approval before executing the changes.
- **Autonomous Troubleshooting:** If a build, test, or linter fails, use the terminal to read the error logs, analyze them incrementally, and apply the fixes directly. 

## 2. SEARCH-FIRST & TOOL USAGE
- **Browser Control:** Always use your browser tools to search for existing libraries (`pub.dev` for Flutter, `PyPI` for Python) before writing custom code. 
- **Terminal Execution:** Once a library is chosen, use the terminal directly to install it (e.g., `flutter pub add <package>`, `pip install <package>`). 
- **Decision Matrix:**
  - *Adopt:* Exact match (e.g., `httpx` for requests, `dio` for Flutter API).
  - *Extend:* Partial match (write a thin wrapper).
  - *Build:* No match found. Write custom, minimal code.

## 3. PYTHON & FASTAPI STANDARDS
- **Formatting & Linting:** Write PEP 8 compliant code. After modifying Python files, autonomously use the terminal to run `ruff check --fix`, `isort .`, and `mypy .` to verify 100% type annotations.
- **Immutability & Patterns:** Prefer `@dataclass(frozen=True)` or `NamedTuple`. Use `Protocol` (Duck Typing) for interfaces instead of ABCs. Use `logging` instead of `print()`.
- **API Design (RESTful):**
  - **URLs:** Nouns, plural, kebab-case (e.g., `/api/v1/translation-history`).
  - **Status Codes:** Strict semantic use (200, 201, 400, 404, 422, 429).
  - **Response Envelope:** `{"data": {...}, "meta": {"page": 1}}` or `{"error": {"code": "...", "message": "..."}}`.
  - **Pagination:** Offset-based (`page`, `per_page`) for Admin CMS. Cursor-based (`cursor`, `limit`) for Flutter App infinite scroll.

## 4. LLM ROUTING & COST TRACKING (BUSINESS LOGIC)
- **Pattern:** `route_llm_request(text, complexity) -> tuple[Result, CostTracker]`.
- **Cache First:** ALWAYS check Redis (`hash(source_text + target_lang)`) before calling the translation LLM. Return cached result if it exists to save API costs.
- **Tracking:** Append `CostRecord(model, input_tokens, output_tokens, cost_usd)` immutably to Postgres. Never mutate cost state.
- **Error Handling:** Never retry LLM calls on validation/auth errors. Only retry transient failures (Rate limit 429, 500).

## 5. SECURITY GUIDELINES (MANDATORY)
- **No Hardcoded Secrets:** Check that `.env` files are used. NEVER write API keys into the source code.
- **Validation:** All FastAPI inputs must be validated via `Pydantic`.
- **SQL Injection:** Use parameterized queries / SQLAlchemy / SQLModel.
- **Rate Limiting:** Ensure Redis-based rate limiting on ALL translation endpoints (e.g., 30/min).

## 6. FLUTTER UI/UX RULES
- **Kiến trúc:** Tách components nhỏ gọn để tái sử dụng. Tự động dùng tool tạo file mới cho các Widget độc lập để source code gọn gàng.
- **State Management:** Quản lý state hợp lý, tránh rebuild toàn bộ màn hình.
- **API Client:** Viết API Client tự động đính kèm Bearer Token vào Header và xử lý Global Error.
- **Testing & Verification:** Sau khi viết xong UI, hãy chạy lệnh `flutter analyze` trong terminal để đảm bảo code sạch và không có linter errors.