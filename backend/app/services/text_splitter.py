def split_text(text: str, max_length: int = 500) -> list[str]:
    normalized_text = " ".join(text.split())
    if not normalized_text:
        return []

    words = normalized_text.split(" ")
    segments: list[str] = []
    current_segment = ""

    for word in words:
        if len(word) > max_length:
            if current_segment:
                segments.append(current_segment)
                current_segment = ""
            start = 0
            while start < len(word):
                segments.append(word[start : start + max_length])
                start += max_length
            continue

        candidate = word if not current_segment else f"{current_segment} {word}"
        if len(candidate) <= max_length:
            current_segment = candidate
        else:
            segments.append(current_segment)
            current_segment = word

    if current_segment:
        segments.append(current_segment)

    return segments
