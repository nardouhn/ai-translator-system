from deep_translator import GoogleTranslator

def translate_batch_with_provider(
    texts: list[str],
    source_lang: str,
    target_lang: str,
) -> tuple[list[str], str]:
    if not texts:
        return [], "google"
        
    delimiter = "\n\n###\n\n"
    translated_texts = []
    current_chunk = []
    current_len = 0
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    
    def process_chunk(chunk):
        if not chunk: return
        combined = delimiter.join(chunk)
        try:
            res = translator.translate(combined)
            if not res: res = combined
            
            # split with fallback for slight delimiter mutations
            res_split = [s.strip() for s in res.replace(" # # # ", "###").replace(" # # ", "###").replace("###\n", "###").split("###")]
            # remove empty strings that might be caused by extra splits
            res_split = [s for s in res_split if s]
            
            if len(res_split) == len(chunk):
                translated_texts.extend(res_split)
            else:
                # fallback to sequential
                for orig in chunk:
                    try:
                        tr = translator.translate(orig)
                        translated_texts.append(tr if tr else orig)
                    except Exception:
                        translated_texts.append(orig)
        except Exception:
            translated_texts.extend(chunk)

    for t in texts:
        t_clean = t.replace("###", "")
        if current_len + len(t_clean) > 3000 and current_chunk:
            process_chunk(current_chunk)
            current_chunk = [t_clean]
            current_len = len(t_clean)
        else:
            current_chunk.append(t_clean)
            current_len += len(t_clean) + len(delimiter)
            
    if current_chunk:
        process_chunk(current_chunk)
        
    return translated_texts, "google"

texts = ["Hello", "World", "This is a test"] * 20
res, _ = translate_batch_with_provider(texts, 'auto', 'vi')
print(len(res))
print(res[:5])
