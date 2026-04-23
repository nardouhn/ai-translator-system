import re

def split_text_into_chunks(text: str, max_chars: int = 350) -> list[str]:
    """
    Split text into chunks using semantic splitting (paragraphs, sentences, etc.)
    with a strict maximum character limit.
    """
    if not text.strip():
        return []

    # Priority separators: \n\n, then . , then ; , then , , then space
    separators = [r"\n\n", r"\.\s+", r";\s+", r",\s+", r"\s+"]
    
    def split_recursive(text_to_split, sep_idx):
        text_to_split = text_to_split.strip()
        if not text_to_split:
            return []
            
        if len(text_to_split) <= max_chars:
            return [text_to_split]
        
        if sep_idx >= len(separators):
            # Final fallback: Hard split by length
            return [text_to_split[i : i + max_chars].strip() for i in range(0, len(text_to_split), max_chars)]
        
        sep = separators[sep_idx]
        # Split but keep the separators to re-assemble
        parts = re.split(f"({sep})", text_to_split)
        
        chunks = []
        current_chunk = ""
        
        for part in parts:
            if not part: continue
            
            # If a single part is too long, split it with next separator
            if len(part) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                chunks.extend(split_recursive(part, sep_idx + 1))
                continue
                
            if len(current_chunk) + len(part) <= max_chars:
                current_chunk += part
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = part
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return [c for c in chunks if c]

    return split_recursive(text, 0)

def split_text(text: str, max_length: int = 1000) -> list[str]:
    # Keep this for backward compatibility if needed by other services
    return split_text_into_chunks(text, max_length)
