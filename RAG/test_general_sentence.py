import os
import sys

# Đảm bảo import được các module trong gói core
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.rag_manager import RAGManager
from core.engine import HybridInferenceEngine

def run_test():
    print("=" * 60)
    print("🧪 BÀI KIỂM TRA RAG PIPELINE - DOMAIN: GENERAL")
    print("=" * 60)

    # Khởi tạo RAG Manager
    db_path = "./VectorDB"
    print(f"📦 1. Đang khởi tạo RAG Manager (kết nối VectorDB tại '{db_path}')...")
    rag = RAGManager(db_path=db_path)

    # Khởi tạo Engine dịch thuật (Ưu tiên Gemini API nếu có key, nếu không dùng Dummy/Fallback)
    print("🚀 2. Đang khởi tạo Hybrid Inference Engine...")
    engine = HybridInferenceEngine()

    # Dữ liệu đầu vào
    test_text = "you are so beautiful"
    test_domain = "general"
    
    print("\n" + "-" * 60)
    print(f"📥 THÔNG TIN ĐẦU VÀO:")
    print(f"   - Câu cần dịch : '{test_text}'")
    print(f"   - Lĩnh vực     : {test_domain.upper()}")
    print("-" * 60 + "\n")

    # Bước 1: Kiểm tra Cache RAM
    print("🔍 Bước 1: Kiểm tra In-Memory Semantic Cache...")
    cached_result = rag.check_cache(test_text)
    if cached_result:
        print(f"   ➔ [CACHE HIT] Đã tìm thấy bản dịch trong bộ nhớ đệm: '{cached_result}'")
        print("\n🎉 HOÀN TẤT BÀI KIỂM TRA (TỪ CACHE)!")
        return

    print("   ➔ [CACHE MISS] Không có trong bộ nhớ đệm, tiếp tục truy vấn VectorDB...")

    # Bước 2: RAG Retrieval (Truy xuất tri thức từ VectorDB và Reranking)
    print("\n📚 Bước 2: Truy xuất tri thức (RAG Retrieval)...")
    context, terminology = rag.get_context(test_text, domain=test_domain)
    
    print(f"   ➔ Bối cảnh (Context) thu được : {context}")
    print(f"   ➔ Thuật ngữ (Glossary) thu được:\n{terminology}")

    # Bước 3: Xây dựng Prompt
    print("\n📝 Bước 3: Đóng gói Prompt gửi cho LLM...")
    full_prompt = rag.format_prompt(
        user_input=test_text,
        context=context,
        terminology=terminology,
        domain=test_domain,
        src="English",
        tgt="Vietnamese"
    )
    print("--- NỘI DUNG PROMPT ---")
    print(full_prompt)
    print("-----------------------")

    # Bước 4: Suy luận qua LLM
    print("\n🤖 Bước 4: Gọi LLM thực hiện dịch thuật...")
    translation = engine.generate(full_prompt)
    
    print("\n" + "=" * 60)
    print(f"🎯 KẾT QUẢ DỊCH THUẬT CUỐI CÙNG:")
    print(f"   '{translation.strip()}'")
    print("=" * 60)

    # Lưu vào cache cho lần sau
    if translation and "[LỖI" not in translation:
        rag.add_to_cache(test_text, translation.strip())
        print("💾 Đã lưu kết quả mới vào In-Memory Semantic Cache.")

if __name__ == "__main__":
    run_test()
