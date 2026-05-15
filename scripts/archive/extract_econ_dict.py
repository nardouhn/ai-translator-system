import fitz
import json
import os
import re

# Đường dẫn
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(BASE_DIR, "data/raw_data/economic/tu-dien-kinh-te-4000-thuat-ngu-econ-dic-danh-cho-phien-dich.pdf")
OUTPUT_PATH = os.path.join(BASE_DIR, "data/economic/economic_glossary.json")

# Tọa độ các cột (x0) dựa trên phân tích
COL_ID_END = 53
COL_EN_END = 150
COL_VI_END = 273

def is_noise(word):
    """Lọc bỏ các từ rác (watermark, footer)"""
    noise_patterns = [
        r'lOMoARcPSD.*',
        r'Downloaded by.*',
        r'Page \d+',
        r'.*@hus\.edu\.vn.*',
        r'4000 THUẬT NGỮ KINH TẾ',
        r'ID', r'Từ', r'Nghĩa', r'Giải thích' # Header
    ]
    return any(re.match(p, word, re.IGNORECASE) for p in noise_patterns)

def process_pdf():
    print(f"Bắt đầu trích xuất PDF bằng tọa độ: {PDF_PATH}")
    doc = fitz.open(PDF_PATH)
    
    entries = []
    current_entry = None

    # Bỏ qua trang bìa (Index 0)
    for page in doc[1:]:
        # Lấy kích thước trang để tính margin
        page_rect = page.rect
        header_margin = 53 # Loại bỏ tiêu đề "ID Từ Nghĩa..."
        footer_margin = page_rect.height - 50
        
        # Lấy danh sách từ cùng tọa độ (x0, y0, x1, y1, word, block_no, line_no, word_no)
        words = page.get_text("words")
        
        # Nhóm các từ theo dòng (Dựa trên y0)
        lines = {}
        for w in words:
            # Lọc theo lề trên/dưới và noise pattern
            if w[1] < header_margin or w[1] > footer_margin:
                continue
                
            if is_noise(w[4]): continue
            
            # Làm tròn tọa độ y để nhóm các từ trên cùng 1 dòng
            y_coord = round(w[1], 1)
            if y_coord not in lines:
                lines[y_coord] = []
            lines[y_coord].append(w)
        
        # Sắp xếp các dòng theo thứ tự từ trên xuống dưới
        sorted_y = sorted(lines.keys())
        
        for y in sorted_y:
            line_words = sorted(lines[y], key=lambda x: x[0]) # Sắp xếp theo x từ trái qua phải
            
            # Phân loại từ vào các bin dựa trên tọa độ x
            id_bin = []
            en_bin = []
            vi_bin = []
            
            for w in line_words:
                x0 = w[0]
                text = w[4]
                
                if x0 < COL_ID_END:
                    # Chỉ chấp nhận nếu là số nguyên
                    if text.isdigit():
                        id_bin.append(text)
                elif COL_ID_END <= x0 < COL_EN_END:
                    en_bin.append(text)
                elif COL_EN_END <= x0 < COL_VI_END:
                    vi_bin.append(text)
                else:
                    # Cột giải thích, ta bỏ qua theo yêu cầu
                    pass

            # Xử lý Logic gộp dòng
            if id_bin:
                # Bắt đầu Entry mới
                if current_entry and current_entry["english"] and current_entry["vietnamese"]:
                    entries.append({
                        "english": current_entry["english"].strip(),
                        "vietnamese": current_entry["vietnamese"].strip()
                    })
                
                current_entry = {
                    "english": " ".join(en_bin),
                    "vietnamese": " ".join(vi_bin)
                }
            elif current_entry:
                # Ghi tiếp vào entry hiện tại (Dòng bổ sung không có ID)
                if en_bin:
                    current_entry["english"] += " " + " ".join(en_bin)
                if vi_bin:
                    current_entry["vietnamese"] += " " + " ".join(vi_bin)

    # Thêm entry cuối cùng
    if current_entry and current_entry["english"] and current_entry["vietnamese"]:
        entries.append({
            "english": current_entry["english"].strip(),
            "vietnamese": current_entry["vietnamese"].strip()
        })

    print(f"Trích xuất hoàn tất! Tìm thấy {len(entries)} mục.")
    
    # Ghi ra JSON
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    
    print(f"Dữ liệu sạch đã được lưu tại: {OUTPUT_PATH}")

if __name__ == "__main__":
    process_pdf()
