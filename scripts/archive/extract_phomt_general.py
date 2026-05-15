"""
Script trích xuất PhoMT (VinAI) → General Context.
Lọc câu không có cặp, quá ngắn/dài, trùng lặp.
Random sample 100,000 câu.
Output: general_context.csv + general_context.json
"""

import os
import csv
import json
import random

# Xác định đường dẫn tương đối từ vị trí script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOMT_DIR = os.path.join(BASE_DIR, "data/raw_data/general/PhoMT/detokenization/train")
OUTPUT_DIR = os.path.join(BASE_DIR, "data/general")
SAMPLE_SIZE = 100_000


def main():
    print("=" * 60)
    print("EXTRACT PHOMT → GENERAL CONTEXT")
    print("=" * 60)

    en_path = os.path.join(PHOMT_DIR, "train.en")
    vi_path = os.path.join(PHOMT_DIR, "train.vi")

    print(f"  Đang đọc PhoMT...")
    with open(en_path, 'r', encoding='utf-8') as f:
        en_lines = f.readlines()
    with open(vi_path, 'r', encoding='utf-8') as f:
        vi_lines = f.readlines()

    total_raw = min(len(en_lines), len(vi_lines))
    print(f"  Tổng dòng thô: {total_raw:,}")

    # === BỘ LỌC CHẤT LƯỢNG ===
    clean_pairs = []
    skipped = {"empty": 0, "too_short": 0, "too_long": 0, "low_alpha": 0, "duplicate": 0}
    seen = set()

    for i in range(total_raw):
        en = en_lines[i].strip()
        vi = vi_lines[i].strip()

        # 1. Bỏ câu rỗng / thiếu cặp
        if not en or not vi:
            skipped["empty"] += 1
            continue

        # 2. Bỏ câu quá ngắn (< 15 ký tự EN hoặc < 10 ký tự VI)
        if len(en) < 15 or len(vi) < 10:
            skipped["too_short"] += 1
            continue

        # 3. Bỏ câu quá dài (> 500 ký tự) - không phù hợp RAG retrieval
        if len(en) > 500 or len(vi) > 500:
            skipped["too_long"] += 1
            continue

        # 4. Bỏ câu có tỉ lệ chữ cái < 50%
        alpha_ratio = sum(c.isalpha() for c in en) / max(len(en), 1)
        if alpha_ratio < 0.5:
            skipped["low_alpha"] += 1
            continue

        # 5. Bỏ trùng lặp
        if en in seen:
            skipped["duplicate"] += 1
            continue
        seen.add(en)

        clean_pairs.append((en, vi))

    print(f"  Sau lọc: {len(clean_pairs):,} cặp câu sạch")
    print(f"  Đã loại bỏ:")
    for reason, count in skipped.items():
        if count > 0:
            print(f"    - {reason}: {count:,}")

    # Random sample
    if len(clean_pairs) > SAMPLE_SIZE:
        random.seed(42)
        clean_pairs = random.sample(clean_pairs, SAMPLE_SIZE)
        print(f"  Random sample: {SAMPLE_SIZE:,} câu")

    # Ghi CSV
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    csv_path = os.path.join(OUTPUT_DIR, "general_context.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['english', 'vietnamese'])
        for en, vi in clean_pairs:
            writer.writerow([en, vi])

    # Ghi JSON
    json_path = os.path.join(OUTPUT_DIR, "general_context.json")
    records = [{"english": en, "vietnamese": vi} for en, vi in clean_pairs]
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    csv_size = os.path.getsize(csv_path) / (1024 * 1024)
    json_size = os.path.getsize(json_path) / (1024 * 1024)
    print(f"\n  ✓ {csv_path} ({csv_size:.1f}MB)")
    print(f"  ✓ {json_path} ({json_size:.1f}MB)")

    # In 5 câu mẫu
    print("\n--- 5 CÂU MẪU ---")
    for en, vi in clean_pairs[:5]:
        print(f"  EN: {en[:120]}")
        print(f"  VI: {vi[:120]}")
        print()


if __name__ == "__main__":
    main()
