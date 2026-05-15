import json
import re

def has_vi_accents(text):
    vi_accents = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    return any(char in text.lower() for char in vi_accents)

def is_clean_english(text):
    vi_accents = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    return not any(char in text.lower() for char in vi_accents)

with open("data/medical/medical_glossary_final_v2.json", "r") as f:
    data = json.load(f)

cleaned = []
for item in data:
    en = item["english"].replace(":", "").replace("[", "").replace("]", "").strip()
    vi = item["vietnamese"].replace(":", "").replace("[", "").replace("]", "").strip()
    
    while vi and vi[0] in ".;- ": vi = vi[1:].strip()
        
    if not en or not vi: continue
        
    # The left side must NOT be Vietnamese
    if not is_clean_english(en): continue
        
    # The right side MUST have at least one Vietnamese character (tone mark)
    # This perfectly kills "something cold, there is sharp..."
    if not has_vi_accents(vi): continue
        
    # Drop long paragraphs
    if len(en.split()) >= 6: continue
    
    # Drop numbers only
    if en.replace('.', '').replace(',', '').isdigit(): continue
        
    cleaned.append({"english": en, "vietnamese": vi})

with open("data/medical/medical_glossary_cleaned.json", "w") as f:
    json.dump(cleaned, f, ensure_ascii=False, indent=4)

print(f"Original: {len(data)}, Cleaned: {len(cleaned)}")
