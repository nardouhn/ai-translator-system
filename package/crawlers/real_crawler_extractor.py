import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
import json
import time
import requests
from core.engine import CloudInferenceEngine

# Danh sách các bài viết (Từ khóa) trên Wikipedia Anh - Việt
WIKI_PAGES = [
    {
        "domain": "economic",
        "en_title": "Inflation",
        "vi_title": "Lạm phát"
    },
    {
        "domain": "medical",
        "en_title": "Myocardial infarction",
        "vi_title": "Nhồi máu cơ tim"
    },
    {
        "domain": "technical",
        "en_title": "Cloud computing",
        "vi_title": "Điện toán đám mây"
    }
]

def fetch_wiki_summary(title, lang="en"):
    """Dùng API của Wikipedia để cào đoạn tóm tắt đầu tiên của một bài viết."""
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": True,       # Chỉ lấy phần mở bài (Introduction)
        "explaintext": True,   # Lấy text thuần, bỏ mã HTML
        "titles": title,
        "format": "json"
    }
    
    headers = {
        'User-Agent': 'DataMiningRAGBot/1.0 (study_project)'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            if page_id != "-1":
                # Trả về khoảng 3-4 câu đầu tiên để LLM không bị ngợp
                full_text = page_data.get("extract", "")
                sentences = full_text.split(". ")
                return ". ".join(sentences[:3]) + "."
    except Exception as e:
        print(f"Lỗi khi cào Wiki bài {title}: {e}")
    return ""

def build_extraction_prompt(en_text, vi_text, domain):
    return f"""<|im_start|>system
Bạn là chuyên gia khai phá dữ liệu thuật ngữ. Nhiệm vụ của bạn là đọc phần tóm tắt Wikipedia bằng tiếng Anh và tiếng Việt dưới đây thuộc lĩnh vực [{domain.upper()}], sau đó đối chiếu để tìm ra các cặp thuật ngữ chuyên ngành tương đương nhau.

Yêu cầu BẮT BUỘC:
1. Chỉ trích xuất danh từ chuyên ngành hoặc cụm danh từ cốt lõi.
2. Trả kết quả DUY NHẤT dưới dạng MẢNG JSON hợp lệ. KHÔNG giải thích.
3. Nếu không tìm thấy, trả về: []

Ví dụ format:
[
  {{"en": "central bank", "vi": "ngân hàng trung ương"}},
  {{"en": "interest rates", "vi": "lãi suất"}}
]
<|im_end|>
<|im_start|>user
Wiki Tiếng Anh: "{en_text}"
Wiki Tiếng Việt: "{vi_text}"<|im_end|>
<|im_start|>assistant
"""

HISTORY_FILE = "crawled_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_history(history_set):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(list(history_set), f, ensure_ascii=False, indent=2)

import hashlib

def run_real_crawler():
    print("=== 🌍 KHỞI ĐỘNG CRAWLER ĐỌC WIKIPEDIA ===")
    
    # Load model
    model_path = os.getenv("MODEL_PATH", "mlx-community/Qwen2.5-7B-Instruct-4bit")
    engine = CloudInferenceEngine(model_path=model_path)
    
    if not engine.model:
        return

    # Tải "Sổ Nam Tào" (Những bài đã cào)
    crawled_history = load_history()
    print(f"\n[INFO] Đã cào trước đây: {len(crawled_history)} bài viết.")

    print("\nĐang tiến hành Cào Dữ Liệu (Crawling) trực tiếp từ Wikipedia...")
    print("="*80)

    for item in WIKI_PAGES:
        # Băm URL thành ID duy nhất (Tránh lỗi trùng tên bài báo)
        url = f"https://en.wikipedia.org/wiki/{item['en_title']}"
        article_id = hashlib.md5(url.encode('utf-8')).hexdigest()
        
        print(f"\n📡 Đang cào bài: {item['en_title']} / {item['vi_title']} [{item['domain'].upper()}]")
        print(f"  🔑 Sinh mã ID nội bộ: {article_id}")
        
        # KIỂM TRA CHỐNG TRÙNG LẶP
        if article_id in crawled_history:
            print("  ⏭️  [BỎ QUA]: Bài này đã cào vào những ngày trước. Bỏ qua để tiết kiệm AI!")
            continue
            
        en_text = fetch_wiki_summary(item['en_title'], lang="en")
        vi_text = fetch_wiki_summary(item['vi_title'], lang="vi")
        
        if not en_text or not vi_text:
            print("⚠️ Bỏ qua do không tải được bài viết.")
            continue
            
        print(f"  [EN Crawled]: {en_text[:150]}...")
        print(f"  [VI Crawled]: {vi_text[:150]}...")
        
        prompt = build_extraction_prompt(en_text, vi_text, item['domain'])
        
        print("  🧠 Bơm vào LLM để bóc tách từ vựng...")
        start_time = time.time()
        result = engine.generate(prompt)
        result = result.strip()
        
        # Clean JSON
        if result.startswith("```json"):
            result = result.replace("```json", "").replace("```", "").strip()
            
        elapsed = time.time() - start_time
        print(f"  ✅ Trích xuất JSON ({elapsed:.2f}s):")
        print(f"  {result}")
        
        # Đánh dấu bài này đã cào xong và lưu Sổ
        crawled_history.add(article_id)
        save_history(crawled_history)
        print("  📝 Đã lưu vào sổ tay chống trùng lặp.")
        print("-" * 80)

if __name__ == "__main__":
    run_real_crawler()
