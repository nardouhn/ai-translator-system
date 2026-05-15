import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import requests
from bs4 import BeautifulSoup

# Danh sách các bài viết (Từ khóa) trên Wikipedia Anh - Việt
WIKI_PAGES = [
    {
        "domain": "economic",
        "en_title": "Inflation",
        "vi_title": "Lạm_phát"
    },
    {
        "domain": "medical",
        "en_title": "Myocardial_infarction",
        "vi_title": "Nhồi_máu_cơ_tim"
    },
    {
        "domain": "technical",
        "en_title": "Cloud_computing",
        "vi_title": "Điện_toán_đám_mây"
    }
]

def crawl_bold_terms_from_wiki(title, lang="en"):
    """
    Cào mã HTML trực tiếp từ Wikipedia.
    Mẹo bóc tách thuật ngữ (Heuristics): Wikipedia LUÔN bôi đậm (thẻ <b>) từ khóa chính và các từ đồng nghĩa ở ngay đoạn mở bài đầu tiên.
    """
    url = f"https://{lang}.wikipedia.org/wiki/{title}"
    headers = {'User-Agent': 'DataMiningRAGBot/1.0 (study_project)'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm nội dung chính bài viết
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if not content_div: return []
            
        parser_output = content_div.find('div', class_='mw-parser-output')
        if not parser_output: return []
            
        # Tìm đoạn văn <p> thật sự đầu tiên (bỏ qua các bảng hộp thông tin)
        paragraphs = parser_output.find_all('p', recursive=False)
        
        terms = []
        for p in paragraphs:
            # Lấy đoạn văn có chữ
            if p.text.strip():
                # Bóc tất cả các chữ được bôi đậm (<b> hoặc <strong>)
                bold_tags = p.find_all(['b', 'strong'])
                for b in bold_tags:
                    term = b.text.strip()
                    if term and len(term) > 1:
                        terms.append(term)
                
                # Nếu tìm thấy thuật ngữ ở đoạn này thì dừng lại (Wikipedia luôn định nghĩa ở đoạn đầu)
                if terms:
                    break
                
        return terms
    except Exception as e:
        print(f"Lỗi: {e}")
        return []

def run_no_ai_crawler():
    print("=== 🕷️ KHỞI ĐỘNG CRAWLER 100% CODE (KHÔNG DÙNG AI) ===")
    print("Mẹo sử dụng: Khai thác quy tắc HTML (Thẻ <b>) của Wikipedia để lấy cặp từ vựng song ngữ.")
    print("=" * 80)
    
    for item in WIKI_PAGES:
        print(f"\n📡 Đang cào URL: {item['en_title']} & {item['vi_title']} [{item['domain'].upper()}]")
        
        en_terms = crawl_bold_terms_from_wiki(item['en_title'], lang="en")
        vi_terms = crawl_bold_terms_from_wiki(item['vi_title'], lang="vi")
        
        print("  ✅ Thuật ngữ Tiếng Anh bắt được: ", en_terms)
        print("  ✅ Thuật ngữ Tiếng Việt bắt được:", vi_terms)
        
        # Ghép cặp (Giả định từ khóa bôi đậm đầu tiên của tiếng Anh luôn ứng với từ khóa bôi đậm đầu tiên của tiếng Việt)
        if en_terms and vi_terms:
            main_en = en_terms[0]
            main_vi = vi_terms[0]
            print(f"  ➡️  [KẾT QUẢ RÚT TRÍCH]: '{main_en}' <==> '{main_vi}'")
            print(f"      (Có thể gọi ngay rag.add_knowledge(en='{main_en}', vi='{main_vi}', domain='{item['domain']}'))")
        else:
            print("  ⚠️ Không tìm thấy đủ cặp thuật ngữ ở đoạn 1.")
            
        print("-" * 80)

if __name__ == "__main__":
    run_no_ai_crawler()
