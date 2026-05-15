"""
Script trích xuất cặp câu song ngữ từ PDF Học viện Tài chính.
Nguồn: tai-lieu-dich-anh-viet-chuyen-nganh-kinh-te-tai-chinh-tacn1.pdf
Output: data/economic/economic_context.json
"""

import os
import re
import json
import fitz  # PyMuPDF

# Xác định đường dẫn tương đối từ vị trí script
BASE_DIR_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.join(BASE_DIR_ROOT, "data")
RAW_DIR = os.path.join(BASE_DIR_ROOT, "data/raw_data")
PDF_PATH = os.path.join(RAW_DIR, "economic/tai-lieu-dich-anh-viet-chuyen-nganh-kinh-te-tai-chinh-tacn1.pdf")
OUTPUT_PATH = os.path.join(BASE_DIR, "economic/economic_context.json")


def read_pdf(pdf_path):
    """Đọc toàn bộ text từ PDF và loại bỏ noise."""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"

    # Xóa header/footer lặp lại và noise
    full_text = re.sub(r'Đội ngũ Quản trị viên.*?HVTC\s*\n?', '', full_text)
    full_text = re.sub(r'Downloaded by.*?\n', '', full_text)
    full_text = re.sub(r'lOMoARcPSD\|\d+\s*\n?', '', full_text)
    full_text = re.sub(r'Scan to open on Studeersnel\n?', '', full_text)
    full_text = re.sub(r'Studocu is not sponsored.*?\n', '', full_text)

    return full_text


def extract_pairs(text, direction="en_vi"):
    """Trích xuất cặp câu từ text.
    Hỗ trợ cả format có mũi tên (➔/=>) và format không có mũi tên (tách bằng heuristic ngôn ngữ).
    """
    pairs = []
    entries = re.split(r'\n\s*(\d+)\.\s+', text)

    current_num = None
    for part in entries:
        part = part.strip()
        if not part:
            continue
        if re.match(r'^\d+$', part):
            current_num = int(part)
            continue
        if current_num is None:
            continue

        # Thử tách bằng mũi tên trước
        splits = re.split(r'\s*(?:➔|=>|=\>)\s*', part, maxsplit=1)

        if len(splits) == 2 and splits[0].strip() and splits[1].strip():
            part1 = ' '.join(splits[0].strip().split())
            part2 = ' '.join(splits[1].strip().split())
        else:
            # Không có mũi tên → tách bằng heuristic ngôn ngữ
            lines = part.strip().split('\n')

            if direction == "en_vi":
                en_lines, vi_lines = [], []
                found_vi = False
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    non_ascii = sum(1 for c in line if ord(c) > 127)
                    ratio = non_ascii / max(len(line), 1)
                    if not found_vi and ratio < 0.05:
                        en_lines.append(line)
                    else:
                        found_vi = True
                        vi_lines.append(line)
                part1 = ' '.join(en_lines)
                part2 = ' '.join(vi_lines)
            else:
                vi_lines, en_lines = [], []
                found_en = False
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    non_ascii = sum(1 for c in line if ord(c) > 127)
                    ratio = non_ascii / max(len(line), 1)
                    if not found_en and ratio > 0.03:
                        vi_lines.append(line)
                    else:
                        found_en = True
                        en_lines.append(line)
                part1 = ' '.join(vi_lines)
                part2 = ' '.join(en_lines)

        if not part1 or not part2:
            current_num = None
            continue

        if direction == "en_vi":
            pairs.append({"english": part1, "vietnamese": part2})
        else:
            pairs.append({"vietnamese": part1, "english": part2})

        current_num = None

    return pairs


def main():
    print("=" * 60)
    print("EXTRACT PDF HỌC VIỆN TÀI CHÍNH → ECONOMIC CONTEXT")
    print("=" * 60)

    full_text = read_pdf(PDF_PATH)

    # Tách phần EN-VI và VI-EN
    vi_en_match = re.search(r'II\.\s*Viet\s*-\s*Eng', full_text)
    en_vi_text = full_text[:vi_en_match.start()]
    vi_en_text = full_text[vi_en_match.start():]

    en_vi_pairs = extract_pairs(en_vi_text, "en_vi")
    vi_en_pairs = extract_pairs(vi_en_text, "vi_en")

    print(f"  EN → VI: {len(en_vi_pairs)} câu")
    print(f"  VI → EN: {len(vi_en_pairs)} câu")

    all_pairs = en_vi_pairs + vi_en_pairs
    print(f"  TỔNG: {len(all_pairs)} câu")

    # Lưu JSON
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_pairs, f, ensure_ascii=False, indent=2)

    print(f"\n  ✓ {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH)//1024}KB)")


if __name__ == "__main__":
    main()
