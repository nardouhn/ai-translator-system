import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.rag_manager import RAGManager
from core.engine import CloudInferenceEngine
from core.kafka_worker import KafkaRAGWorker

app = FastAPI(
    title="AI Translation RAG API",
    version="1.0.0",
    description="Hệ thống dịch thuật AI sử dụng RAG (Retrieval-Augmented Generation) với hỗ trợ cập nhật Kafka."
)

# --- Initialization ---
MODEL_PATH = os.getenv("MODEL_PATH", "ltyen05/qwen-domain-translator")
DB_PATH = os.getenv("DB_PATH", "./VectorDB_Gemini")
KAFKA_SERVERS = os.getenv("KAFKA_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "translation_updates")

print("=" * 50)
print("  AI Translation RAG API - Initializing...")
print(f"  MODEL_PATH: {MODEL_PATH}")
print(f"  DB_PATH:    {DB_PATH}")
print(f"  KAFKA:      {KAFKA_SERVERS} (Topic: {KAFKA_TOPIC})")
print("=" * 50)

rag = RAGManager(db_path=DB_PATH)
engine = CloudInferenceEngine(model_path=MODEL_PATH)

# Start Kafka Worker in background
if os.getenv("ENABLE_KAFKA", "false").lower() == "true":
    kafka_worker = KafkaRAGWorker(rag, KAFKA_SERVERS, KAFKA_TOPIC)
    kafka_worker.start()

# --- Pydantic Models ---
class TranslationRequest(BaseModel):
    text: str
    domain: Optional[str] = "general"
    source_lang: Optional[str] = "English"
    target_lang: Optional[str] = "Vietnamese"

class TranslationResponse(BaseModel):
    translation: str
    detected_domain: str

# --- Endpoints ---
@app.get("/", tags=["Health"])
def health_check():
    """Kiểm tra trạng thái hoạt động của API."""
    return {
        "status": "online",
        "model_path": MODEL_PATH,
        "db_path": DB_PATH
    }

@app.post("/translate", response_model=TranslationResponse, tags=["Translation"])
def translate(req: TranslationRequest):
    """
    Dịch văn bản sử dụng RAG pipeline với Semantic Cache.
    """
    try:
        # Chuẩn hóa domain về chữ thường bất kể UI gửi hoa hay thường
        domain_str = req.domain.lower() if req.domain else "general"
        
        # 0. Check Semantic Cache (Tối ưu tốc độ cho câu lặp lại)
        cached_result = rag.check_cache(req.text)
        if cached_result:
            print(f"🚀 Cache Hit: Returning cached translation for '{req.text[:30]}...'")
            return TranslationResponse(
                translation=cached_result.strip(),
                detected_domain=domain_str
            )

        # 1. RAG Retrieval
        context, terminology = rag.get_context(req.text, domain=domain_str)
        
        # 2. Build Prompt
        full_prompt = rag.format_prompt(
            user_input=req.text,
            context=context,
            terminology=terminology,
            domain=domain_str,
            src=req.source_lang,
            tgt=req.target_lang
        )
        
        # 3. LLM Inference
        result = engine.generate(full_prompt)
        
        # 4. Save to Cache
        if result and "[ERROR]" not in result:
            rag.add_to_cache(req.text, result)
        
        return TranslationResponse(
            translation=result.strip(),
            detected_domain=domain_str
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
