import sys
import os

# Tự động thêm thư mục gốc của dự án vào PYTHONPATH
# Giúp chạy script từ bất kỳ đâu (root hay scripts/rag_core) đều không bị lỗi
# current_dir: /.../DataMining/scripts/rag_core
current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root: /.../DataMining
project_root = os.path.abspath(os.path.join(current_dir, "../../"))

if project_root not in sys.path:
    sys.path.append(project_root)

# Bây giờ có thể import thoải mái
from prompt_config import get_context_prompt, format_qwen_prompt
from scripts.rag_core.llm_engine_manual import LocalFileModelConnector, APIModelConnector, MockEngine

def run_manual_demo():
    print("=== DEMO DỊCH THUẬT: MANUAL RAG PIPELINE (OPTIMIZED) ===")
    
    # CHỌN ĐƯỜNG DẪN MÔ HÌNH MLX (Đã nén 5GB - Tối ưu cho Mac)
    # Sử dụng project_root để đường dẫn luôn đúng
    weight_file = os.path.join(project_root, "outputs", "completed_model_mlx")
    
    if not os.path.exists(weight_file):
        print(f"⚠️ Cảnh báo: Không tìm thấy mô hình tại {weight_file}")
        print("Đang thử kiểm tra các thư mục khác...")
        # Fallback thử tìm trong thư mục outputs gốc nếu project_root bị sai lệch
        weight_file = "outputs/completed_model_mlx"

    # Khởi tạo engine
    engine = LocalFileModelConnector(model_path=weight_file)
    
    test_query = "The patient presented with persistent vertigo and hearing loss. Upon examination, a diagnosis of Meniere's disease was suspected, and an intratympanic steroid injection was recommended to alleviate the symptoms."
    print(f"\n[1] Câu tiếng Anh: {test_query}")
    
    # Lấy ngữ cảnh RAG
    context = get_context_prompt(test_query, domain="medical_context")
    full_prompt = format_qwen_prompt(test_query, context)
    
    print("\n[2] Đang xử lý qua Engine đã chọn...")
    translation = engine.generate(full_prompt)
    
    print(f"\n[3] KẾT QUẢ DỊCH:\n{translation}")

if __name__ == "__main__":
    run_manual_demo()
