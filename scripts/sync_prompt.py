import re
# Import các thành phần cần thiết từ file cấu hình cũ
from prompt_config import collection, glossary_collection

def get_sync_context(user_input):
    """
    Truy xuất Glossary và Translation Memory từ VectorDB
    """
    # 1. Truy xuất Translation Memory (TM)
    tm_text = "Không có ví dụ tương ứng."
    try:
        tm_results = collection.query(query_texts=[user_input], n_results=1)
        if tm_results.get("documents") and tm_results["documents"][0]:
            retrieved_en = tm_results["documents"][0][0]
            retrieved_vi = tm_results["metadatas"][0][0].get("vi", "")
            tm_text = f"English: {retrieved_en}\nVietnamese meaning: {retrieved_vi}"
    except Exception as e:
        print(f"[CẢNH BÁO] Lỗi truy xuất TM: {e}")

    # 2. Truy xuất Glossary (Từ điển)
    glossary_text = "Không phát hiện thuật ngữ đặc biệt nào trong câu."
    found_terms = []
    try:
        glossary_results = glossary_collection.query(query_texts=[user_input], n_results=30)
        user_input_lower = user_input.lower()
        
        if glossary_results.get("documents") and glossary_results["documents"][0]:
            for i, term in enumerate(glossary_results["documents"][0]):
                meta = glossary_results["metadatas"][0][i]
                # Kiểm tra xem thuật ngữ có thực sự xuất hiện trong câu không
                pattern = r'\b' + re.escape(term.lower()) + r'\b'
                if re.search(pattern, user_input_lower):
                    found_terms.append(f"- '{term}': Dịch là '{meta['translation']}' -> Rule: {meta['rule']}")
            
            if found_terms:
                glossary_text = "\n".join(found_terms[:15]) # Lấy tối đa 15 thuật ngữ
    except Exception as e:
        print(f"[CẢNH BÁO] Lỗi truy xuất Glossary: {e}")

    return glossary_text, tm_text

def create_sync_prompt(en_input, domain="Công nghệ thông tin"):
    """
    Tạo prompt theo cấu trúc template mới
    """
    glossary, tm = get_sync_context(en_input)
    
    prompt = f"""Dưới đây là yêu cầu dịch thuật chuyên ngành.

### Instruction:
Bạn là dịch giả chuyên nghiệp trong lĩnh vực {domain}. Hãy dịch câu tiếng Anh sau sang tiếng Việt sát nghĩa và đúng ngữ cảnh chuyên ngành nhất. 

QUY TẮC BẮT BUỘC:
- Tuân thủ Glossary nếu có.
- Giữ nguyên code snippets, tên hàm, biến, HTML/Markdown.
- Không dịch nội dung bên trong code.
- Không thêm giải thích.

### Glossary:
{glossary}

### Translation Memory:
{tm}

### Input:
{en_input}

### Response:
"""
    return prompt

if __name__ == "__main__":
    # Chạy thử nghiệm
    test_query = "The system will return a 404 error if the resource is not found."
    print("--- SYNC PROMPT TEST ---")
    print(create_sync_prompt(test_query))
