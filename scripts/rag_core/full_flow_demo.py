import sys
import os
import time

# Tự động thêm thư mục gốc của dự án vào PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from prompt_config import get_context_prompt, format_qwen_prompt, check_semantic_cache, add_to_cache
from scripts.rag_core.llm_engine_manual import LocalFileModelConnector

def run_long_text_demo():
    model_path = os.path.join(project_root, "outputs", "completed_model_mlx")
    log_file = os.path.join(project_root, "demo_long_text_log.md")
    
    print(f"=== ĐANG CHẠY DEMO VĂN BẢN DÀI (LOG: {log_file}) ===")
    
    engine = LocalFileModelConnector(model_path=model_path)
    
    # Một đoạn văn bản y khoa rất dài về rung tâm nhĩ (Atrial Fibrillation)
    long_input = (
        "Atrial fibrillation (AF or A-fib) is a quivering or irregular heartbeat (arrhythmia) that can lead to blood clots, "
        "stroke, heart failure and other heart-related complications. A normal heart beats at a steady rhythm, but in "
        "atrial fibrillation, the upper chambers of the heart (the atria) beat irregularly and out of sync with the "
        "lower chambers (the ventricles). For many people, A-fib may have no symptoms. However, A-fib may cause a fast, "
        "pounding heartbeat, shortness of breath or weakness. Episodes of atrial fibrillation can come and go, or you "
        "may develop atrial fibrillation that doesn't go away and may require treatment. Although atrial fibrillation "
        "itself usually isn't life-threatening, it is a serious medical condition that requires proper treatment to "
        "prevent stroke. Treatment for atrial fibrillation may include medications, medical procedures and lifestyle "
        "changes to alter the heart's electrical system. The risk of atrial fibrillation increases with age and "
        "is more common in people with high blood pressure, obesity, and underlying heart disease. Early detection "
        "and management are crucial for reducing long-term morbidity and mortality. In addition to medical management, "
        "patients are often advised to monitor their symptoms closely and engage in heart-healthy behaviors, such as "
        "maintaining a balanced diet, exercising regularly, and avoiding excessive alcohol and caffeine consumption. "
        "Advancements in medical technology, including catheter ablation and minimally invasive surgical techniques, "
        "have provided more options for patients who do not respond well to traditional pharmacological therapies. "
        "The primary goal of these interventions is to restore a normal heart rhythm and alleviate the persistent "
        "symptoms that can significantly impair a patient's functional status and overall well-being. Ongoing clinical "
        "trials and research continue to explore the genetic and molecular underpinnings of atrial fibrillation, "
        "aiming to develop more targeted and effective therapeutic strategies for this prevalent cardiac disorder."
    )

    print("\n--- [LẦN 1] CHẠY MỚI (KHÔNG CÓ CACHE) ---")
    start_1 = time.time()
    
    # 1. RAG
    print("-> Đang truy xuất RAG...")
    context = get_context_prompt(long_input, domain="medical")
    
    # 2. LLM
    full_prompt = format_qwen_prompt(long_input, context, domain="Y tế (Medical)")
    print("-> Đang giải mã văn bản dài (Streaming)...")
    translation_1 = engine.generate(full_prompt, stream=True)
    add_to_cache(long_input, translation_1)
    
    end_1 = time.time()
    time_1 = end_1 - start_1

    print("\n--- [LẦN 2] CHẠY LẠI (DÙNG CACHE) ---")
    start_2 = time.time()
    
    # Kiểm tra cache
    translation_2 = check_semantic_cache(long_input)
    is_cached = translation_2 is not None
    
    end_2 = time.time()
    time_2 = end_2 - start_2

    # Ghi log
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("# 📑 BÁO CÁO HIỆU NĂNG VỚI VĂN BẢN DÀI\n\n")
        f.write(f"- **Độ dài văn bản**: {len(long_input.split())} từ\n\n")
        
        f.write("### ❌ LẦN 1: KHÔNG CACHE\n")
        f.write(f"- **Thời gian**: {time_1:.2f} giây\n")
        f.write(f"- **Kết quả**: {translation_1}\n\n")
        
        f.write("### ✅ LẦN 2: CÓ CACHE ⚡\n")
        f.write(f"- **Thời gian**: {time_2:.4f} giây\n")
        f.write(f"- **Kết quả**: {translation_2}\n\n")
        
        f.write(f"**=> TỐC ĐỘ TĂNG GẤP: {time_1 / time_2:.0f} LẦN!**\n")

    print(f"\n✅ ĐÃ XONG! Mời xem log tại '{log_file}'.")

if __name__ == "__main__":
    run_long_text_demo()
