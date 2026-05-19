import re
import math

def split_text_into_chunks(text: str, max_chars: int = 1000) -> list[str]:
    """
    Cắt văn bản ưu tiên theo paragraph, sau đó theo câu (bảo toàn dấu câu).
    Gom các câu lại đến mức dung lượng "tương đối" (target_length) thì ngắt.
    """
    if not text or not text.strip():
        return []

    # 1. Tách văn bản thành các đoạn (paragraph)
    paragraphs = [p.strip() for p in re.split(r'\n+', text) if p.strip()]
    chunks = []

    for para in paragraphs:
        if len(para) <= max_chars:
            chunks.append(para)
            continue

        # 2. Tách đoạn dài thành các CÂU, giữ nguyên dấu câu (. ? ! ; ,)
        parts = re.split(r'([.?!;,]\s+)', para)
        sentences = []
        current_sentence = ""
        for part in parts:
            current_sentence += part
            if re.match(r'^[.?!;,]\s+$', part) or part == parts[-1]:
                if current_sentence.strip():
                    sentences.append(current_sentence)
                current_sentence = ""
        
        # 3. Tính toán dung lượng "tương đối" (target)
        total_len = sum(len(s) for s in sentences)
        num_chunks = math.ceil(total_len / max_chars)
        target_length = total_len / num_chunks 
        
        current_chunk = ""
        for sentence in sentences:
            # Ngoại lệ: Câu không có dấu câu nào mà vẫn dài > 1000 ký tự -> Buộc cắt cứng
            if len(sentence) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                for i in range(0, len(sentence), max_chars):
                    chunks.append(sentence[i:i+max_chars].strip())
                continue

            # Nếu cộng thêm câu này vào mà vượt max_chars (1000) -> Bắt buộc ngắt sớm
            if len(current_chunk) + len(sentence) > max_chars:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += sentence
                
                # MỚI: Chỉ cần chunk hiện tại đạt ngưỡng "tương đối" thì chốt sổ.
                # Ví dụ: 1200 chia 2 -> target là 600.
                # Đang có 400, cộng thêm 1 câu thành 800 (800 >= 600) -> Lập tức ngắt!
                # Kết quả ra 2 chunk: 800 và 400, hoàn toàn không bị vỡ dấu câu.
                if len(current_chunk) >= target_length:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

        # Đẩy nốt chunk cuối cùng vào danh sách
        if current_chunk:
            chunks.append(current_chunk.strip())

    return chunks

def split_text(text: str, max_length: int = 1000) -> list[str]:
    return split_text_into_chunks(text, max_length)
