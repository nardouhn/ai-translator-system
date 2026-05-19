import re
import math

def split_text_into_chunks(text: str, max_chars: int = 1000) -> list[str]:
    if not text:
        return []

    # Việc bọc (\n+) trong ngoặc đơn giúp re.split KHÔNG vứt bỏ dấu xuống dòng
    parts = re.split(r'(\n+)', text)
    chunks = []

    for part in parts:
        if not part:
            continue
            
        # 1. Nếu part chỉ là khoảng trắng hoặc dấu xuống dòng -> Biến nó thành 1 chunk độc lập
        if re.match(r'^[\s\n]+$', part):
            chunks.append(part)
            continue

        # 2. Nếu đoạn văn ngắn hơn max_chars -> Giữ nguyên (không dùng .strip() để giữ khoảng trắng)
        if len(part) <= max_chars:
            chunks.append(part)
            continue

        # 3. Nếu đoạn văn dài hơn max_chars -> Tách theo câu
        sentence_parts = re.split(r'([.?!;,]\s+)', part)
        sentences = []
        current_sentence = ""
        
        for sp in sentence_parts:
            current_sentence += sp
            if re.match(r'^[.?!;,]\s+$', sp) or sp == sentence_parts[-1]:
                if current_sentence:
                    sentences.append(current_sentence)
                current_sentence = ""
        
        # Cân bằng dung lượng các chunk con
        total_len = sum(len(s) for s in sentences)
        if total_len == 0:
            continue
            
        num_chunks = math.ceil(total_len / max_chars)
        target_length = total_len / num_chunks 
        
        current_chunk = ""
        for sentence in sentences:
            if len(sentence) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk) # Không dùng .strip()
                    current_chunk = ""
                for i in range(0, len(sentence), max_chars):
                    chunks.append(sentence[i:i+max_chars])
                continue

            if len(current_chunk) + len(sentence) > max_chars:
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                current_chunk += sentence
                if len(current_chunk) >= target_length:
                    chunks.append(current_chunk)
                    current_chunk = ""

        if current_chunk:
            chunks.append(current_chunk)

    return chunks

def split_text(text: str, max_length: int = 1000) -> list[str]:
    return split_text_into_chunks(text, max_length)
