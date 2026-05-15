import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
import os
from core.rag_manager import RAGManager
from core.engine import CloudInferenceEngine

def test_rag_system():
    print("=== 🔍 ĐANG KIỂM TRA HỆ THỐNG RAG ===")
    
    # 1. Khởi tạo (DB_PATH trỏ vào thư mục DB trong package)
    db_path = "./VectorDB_Gemini"
    model_path = os.getenv("MODEL_PATH", "ltyen05/qwen-domain-translator")
    
    if not os.path.exists(db_path):
        print(f"❌ LỖI: Không tìm thấy thư mục DB tại {db_path}")
        return

    rag = RAGManager(db_path=db_path)
    print("✅ Khởi tạo RAG thành công.")
    
    engine = CloudInferenceEngine(model_path=model_path)
    if engine.model:
        print("✅ Khởi tạo Model thành công.\n")
    else:
        print("⚠️ Không có Model thực sự (hoặc đường dẫn model không đúng). Sẽ chỉ in ra prompt.\n")

    # 2. Vòng lặp cho người dùng nhập
    while True:
        print("-" * 50)
        domain = input("Nhập domain (medical/economic/technical/general) hoặc 'q' để thoát: ").strip()
        if domain.lower() == 'q':
            break
            
        context_input = input("Nhập câu cần dịch: ").strip()
        if not context_input:
            continue

        print(f"\n--- 🧪 Đang xử lý ---")
        
        start_time = time.time()
        
        # Lấy ngữ cảnh
        context, terminology = rag.get_context(context_input, domain=domain)
        
        print("\n[THUẬT NGỮ TÌM ĐƯỢC (Glossary)]:")
        print(terminology)
        
        print("[NGỮ CẢNH TRUY XUẤT ĐƯỢC (Context)]:")
        print(context)
        
        # Tạo prompt hoàn chỉnh
        full_prompt = rag.format_prompt(
            user_input=context_input,
            context=context,
            terminology=terminology,
            domain=domain
        )
        
        print("-" * 50)
        print("✅ PROMPT CUỐI CÙNG SẼ GỬI ĐẾN LLM:")
        print(full_prompt)
        
        if engine.model:
            print("\n🔄 Đang dịch...")
            result = engine.generate(full_prompt)
            end_time = time.time()
            elapsed_time = end_time - start_time
            print("\n" + "=" * 60)
            print("✨ KẾT QUẢ DỊCH:")
            print(result.strip())
            print(f"⏱️ Thời gian tổng cộng: {elapsed_time:.2f} giây")
            print("=" * 60 + "\n")
        else:
            end_time = time.time()
            elapsed_time = end_time - start_time
            print("\n" + "=" * 60)
            print(f"⏱️ Thời gian xử lý RAG: {elapsed_time:.2f} giây (Chưa có bước dịch do thiếu model)")
            print("=" * 60 + "\n")

if __name__ == "__main__":
    test_rag_system()
