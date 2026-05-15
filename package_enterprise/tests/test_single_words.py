import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
import os
from core.rag_manager import RAGManager

def test_single_words():
    print("=== 🔍 TEST TỪ ĐƠN TRÊN CẢ 4 LĨNH VỰC ===\n")
    
    db_path = "./VectorDB"
    if not os.path.exists(db_path):
        print(f"❌ LỖI: Không tìm thấy thư mục DB tại {db_path}")
        return

    rag = RAGManager(db_path=db_path)
    print("✅ Khởi tạo RAG thành công.\n")

    # Danh sách từ đơn test cho từng domain
    test_cases = {
        "medical": [
            "stroke",
            "diabetes",
            "hypertension",
            "cancer",
            "tumor",
            "surgery",
            "pneumonia",
            "vaccine",
            "antibiotic",
            "cholesterol",
            "arrhythmia",
            "anesthesia",
            "diagnosis",
            "inflammation",
            "infection",
        ],
        "economic": [
            "inflation",
            "GDP",
            "recession",
            "tariff",
            "revenue",
            "deficit",
            "subsidy",
            "dividend",
            "bankruptcy",
            "commodity",
            "depreciation",
            "equity",
            "interest",
            "investment",
            "mortgage",
        ],
        "technical": [
            "algorithm",
            "bandwidth",
            "encryption",
            "firewall",
            "latency",
            "middleware",
            "compiler",
            "protocol",
            "blockchain",
            "API",
            "cache",
            "debugging",
            "kernel",
            "server",
            "container",
        ],
        "general": [
            "environment",
            "education",
            "sustainability",
            "democracy",
            "innovation",
            "globalization",
            "culture",
            "immigration",
            "infrastructure",
            "tourism",
            "diplomacy",
            "poverty",
            "legislation",
            "volunteer",
            "heritage",
        ],
    }

    total_tests = sum(len(words) for words in test_cases.values())
    test_count = 0

    for domain, words in test_cases.items():
        print(f"\n{'='*60}")
        print(f"📂 DOMAIN: {domain.upper()} ({len(words)} từ)")
        print(f"{'='*60}")

        for word in words:
            test_count += 1
            print(f"\n--- [{test_count}/{total_tests}] 🔎 \"{word}\" ({domain}) ---")

            start_time = time.time()

            context, terminology = rag.get_context(word, domain=domain)

            elapsed = time.time() - start_time

            print(f"  [Glossary]: {terminology.strip() if terminology.strip() != 'N/A' else '❌ Không tìm thấy'}")
            print(f"  [Context]:  {context.strip()[:150] if context.strip() != 'N/A' else '❌ Không tìm thấy'}{'...' if len(context.strip()) > 150 else ''}")
            print(f"  ⏱️ {elapsed:.3f}s")

    print(f"\n{'='*60}")
    print(f"✅ HOÀN TẤT: Đã test {total_tests} từ đơn trên 4 lĩnh vực.")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_single_words()
