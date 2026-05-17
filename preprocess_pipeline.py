"""
=============================================================
AI Translator - Phase 1: Data Preprocessing Pipeline
Dataset: hiimbach/mtet (English-Vietnamese)
Goal: Filter 20K IT-domain sentence pairs, clean, tokenize, analyze
=============================================================
Usage (local):
    pip install datasets pandas underthesea nltk
    python preprocess_pipeline.py

Output:
    output/dataset_en_vi_it_clean.csv
    output/dataset_en_vi_medical_clean.csv
    output/dataset_en_vi_business_clean.csv
    output/dataset_en_vi_general_clean.csv
    output/dataset_en_vi_all_domains.csv
    output/dataset_en_vi_it_clean.json
    output/vocab_en.json
    output/vocab_vi.json
    output/dataset_statistics_report.json
=============================================================
"""

import os
import re
import json
import csv
import hashlib
import statistics
from collections import Counter

try:
    from underthesea import word_tokenize as vi_word_tokenize
except ImportError:
    vi_word_tokenize = None

try:
    from nltk.tokenize import TreebankWordTokenizer
except ImportError:
    TreebankWordTokenizer = None

# ============================================================
# CONFIG
# ============================================================
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGET_SIZE = 50000
MAX_SRC_LEN = 128   # max tokens English
MAX_TGT_LEN = 150   # max tokens Vietnamese
MIN_LEN = 3          # min tokens per sentence
URL_PATTERN = re.compile(r"(?:https?://\S+|www\.\S+|\b\S+\.(?:com|net|org|io|gov|edu|vn|co|ai|dev)\S*)", flags=re.IGNORECASE)
NOISY_ARTIFACT_PATTERN = re.compile(
    r"(?:smallurl|bigurl|smallwidth|smallheight|bigwidth|bigheight|licensing|"
    r"wikihow\s*\.\s*com\s*/\s*images|/images\s*/\s*thumb|images-en\s*/\s*thumb|"
    r"\{\s*\"\"\s*[a-z_]+\s*\"\"\s*:\s*\"\")",
    flags=re.IGNORECASE,
)

# IT domain keywords (broad coverage for filtering)
IT_KEYWORDS_EN = {
    # Core CS
    "software", "hardware", "computer", "algorithm", "programming", "code",
    "developer", "application", "system", "network", "internet", "web",
    "server", "client", "database", "data", "cloud", "api", "interface",
    # Languages & frameworks
    "python", "java", "javascript", "html", "css", "react", "angular",
    "node", "docker", "kubernetes", "linux", "windows", "android", "ios",
    # ML/AI
    "machine learning", "deep learning", "artificial intelligence", "neural",
    "model", "training", "dataset", "tensor", "gpu", "cpu",
    # Security & infra
    "security", "encryption", "firewall", "protocol", "authentication",
    "token", "password", "cyber", "malware", "vulnerability",
    # DevOps & tools
    "git", "deploy", "pipeline", "container", "microservice", "devops",
    "agile", "scrum", "sprint", "repository", "commit", "branch",
    # Data
    "sql", "nosql", "query", "table", "schema", "etl", "warehouse",
    "analytics", "visualization", "dashboard",
    # General tech
    "digital", "technology", "automation", "robot", "sensor", "iot",
    "blockchain", "cryptocurrency", "virtual", "platform", "framework",
    "library", "module", "function", "variable", "class", "object",
    "array", "string", "integer", "boolean", "loop", "debug", "compile",
    "runtime", "memory", "cache", "bandwidth", "latency", "throughput",
    "frontend", "backend", "fullstack", "responsive", "mobile",
    "browser", "download", "upload", "storage", "file", "folder",
    "operating system", "kernel", "process", "thread", "socket",
    "http", "https", "tcp", "ip", "dns", "url", "domain",
    "pixel", "resolution", "render", "graphic", "animation",
    "startup", "tech", "saas", "open source", "license",
    "user", "admin", "config", "log", "error", "bug", "patch",
    "update", "version", "release", "beta", "alpha",
}

# Medical domain keywords (English side used for scoring)
MEDICAL_KEYWORDS_EN = {
    "medical", "medicine", "hospital", "clinic", "doctor", "nurse",
    "patient", "diagnosis", "treatment", "therapy", "disease", "infection",
    "virus", "bacteria", "vaccine", "vaccination", "immune", "immunity",
    "health", "healthcare", "public health", "symptom", "fever", "pain",
    "blood", "pressure", "heart", "lung", "kidney", "liver", "brain",
    "cancer", "diabetes", "hypertension", "stroke", "allergy", "asthma",
    "surgery", "operation", "emergency", "intensive care", "icu", "ward",
    "pharmacy", "drug", "medication", "prescription", "antibiotic", "dose",
    "laboratory", "lab", "test", "x-ray", "ultrasound", "mri", "ct scan",
    "epidemic", "pandemic", "outbreak", "mental health", "depression", "anxiety",
    "rehabilitation", "nutrition", "diet", "clinical", "trial", "biomedical",
}

# Business/Economy domain keywords (English side used for scoring)
BUSINESS_KEYWORDS_EN = {
    "business", "economy", "economic", "finance", "financial", "marketing", "brand",
    "market", "marketshare", "trade", "commerce", "sales", "retail", "wholesale",
    "customer", "client", "consumer", "product", "service", "pricing", "price",
    "cost", "expense", "profit", "revenue", "income", "investment", "investor",
    "stock", "bond", "bank", "banking", "credit", "loan", "debt", "cashflow",
    "budget", "tax", "inflation", "gdp", "currency", "exchange rate",
    "company", "enterprise", "startup", "corporation", "corporate", "firm",
    "industry", "commercial", "management", "strategy", "operation", "supply chain",
    "logistics", "distribution", "contract", "deal", "negotiation", "partnership",
    "employer", "employee", "workforce", "human resources", "hr", "leadership",
}

# General daily-life communication keywords (non-specialized)
GENERAL_KEYWORDS_EN = {
    "hello", "hi", "thanks", "thank you", "sorry", "please", "welcome",
    "good morning", "good afternoon", "good evening", "good night",
    "how are you", "see you", "take care", "nice to meet you",
    "family", "friend", "home", "house", "room", "kitchen", "school",
    "food", "drink", "water", "coffee", "tea", "breakfast", "lunch", "dinner",
    "sleep", "wake", "walk", "run", "travel", "bus", "train", "car", "bike",
    "weather", "rain", "sunny", "cold", "hot", "weekend", "holiday", "birthday",
    "shopping", "store", "market", "money", "pay", "buy", "sell",
    "phone", "message", "call", "photo", "music", "movie", "book", "game",
    "work", "office", "meeting", "today", "tomorrow", "yesterday", "now", "later",
    "help", "problem", "idea", "plan", "time", "day", "week", "month", "year",
    "happy", "sad", "tired", "busy", "ready", "late", "early", "important",
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def normalize_text(text: str) -> str:
    """Normalize unicode quotes, whitespace, punctuation."""
    # Remove URLs early so they do not affect filtering/tokenization stats.
    text = URL_PATTERN.sub(" ", text)
    text = text.replace('\u201c', '"').replace('\u201d', '"')  # smart quotes
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u2026', '...')
    text = re.sub(r'\s+', ' ', text).strip()
    if text.count('"') % 2 != 0:
        text = text.replace('"', '')
    return text


def normalize_punctuation_chars(text: str) -> str:
    """Normalize Unicode punctuation variants to ASCII punctuation."""
    punctuation_map = {
        "，": ",",
        "。": ".",
        "！": "!",
        "？": "?",
        "；": ";",
        "：": ":",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
    }
    for src, dst in punctuation_map.items():
        text = text.replace(src, dst)
    return text


def is_noisy_artifact_text(text: str) -> bool:
    """Detect common noisy fragments like scraped JSON image metadata blocks."""
    # Normalize spacing around punctuation so patterns like "wikihow. com" still match.
    compact = re.sub(r"\s+", " ", text)
    compact = re.sub(r"\s*([./:])\s*", r"\1", compact)
    return bool(NOISY_ARTIFACT_PATTERN.search(compact))


def has_tab_artifact(text: str) -> bool:
    """Detect both real tab and escaped tab sequence in raw text."""
    return "\t" in text or "\\t" in text


def sync_pair_punctuation(en_text: str, vi_text: str) -> tuple:
    """Keep ending punctuation consistent between EN and VI sides."""
    en_text = normalize_punctuation_chars(en_text)
    vi_text = normalize_punctuation_chars(vi_text)

    # Keep internal special punctuation sequence ':,' consistent across pair.
    en_colon_comma = en_text.count(":,")
    vi_colon_comma = vi_text.count(":,")
    if en_colon_comma > vi_colon_comma:
        missing = en_colon_comma - vi_colon_comma
        for _ in range(missing):
            comma_pos = vi_text.find(",")
            if comma_pos == -1:
                break
            vi_text = vi_text[:comma_pos] + ":," + vi_text[comma_pos + 1:]
    elif vi_colon_comma > en_colon_comma:
        missing = vi_colon_comma - en_colon_comma
        for _ in range(missing):
            comma_pos = en_text.find(",")
            if comma_pos == -1:
                break
            en_text = en_text[:comma_pos] + ":," + en_text[comma_pos + 1:]

    en_end = re.search(r"([.!?]+)$", en_text)
    vi_end = re.search(r"([.!?]+)$", vi_text)

    target_end = en_end.group(1) if en_end else (vi_end.group(1) if vi_end else "")

    en_base = re.sub(r"[.!?]+$", "", en_text).rstrip()
    vi_base = re.sub(r"[.!?]+$", "", vi_text).rstrip()

    if target_end:
        en_text = f"{en_base}{target_end}"
        vi_text = f"{vi_base}{target_end}"
    else:
        en_text = en_base
        vi_text = vi_base

    # Custom punctuation mapping requested for VI side.
    # If EN ends with '"', force VI to end with ')'.
    # If EN ends with '.', force VI to end with '..'.
    en_trim = en_text.rstrip()
    vi_trim = vi_text.rstrip()
    if en_trim.endswith('"'):
        vi_core = re.sub(r"[\"\)\.!?]+$", "", vi_trim).rstrip()
        vi_text = f"{vi_core})"
    elif en_trim.endswith('.'):
        vi_core = re.sub(r"[\.!?]+$", "", vi_trim).rstrip()
        vi_text = f"{vi_core}.."

    # Fix numbered list punctuation: "b/" en should become "b)" vi, "c/" en should become "c)", etc.
    # Pattern: single letter followed by / (like a/, b/, c/, d/, etc.) should map to letter followed by )
    vi_text = re.sub(r'([a-zA-Z])\/', r'\1)', vi_text)

    return en_text, vi_text


def simple_tokenize_en(text: str) -> list:
    """English tokenizer using nltk.tokenize (lowercase, no punctuation)."""
    if TreebankWordTokenizer is None:
        raise ImportError("Missing dependency 'nltk'. Install with: pip install nltk")

    text = text.lower()
    tokenizer = TreebankWordTokenizer()
    tokens = tokenizer.tokenize(text)
    return [tok for tok in tokens if re.fullmatch(r"[a-z0-9]+(?:'[a-z]+)?", tok)]


def simple_tokenize_vi(text: str) -> list:
    """Vietnamese tokenizer using underthesea, removing punctuation."""
    if vi_word_tokenize is None:
        raise ImportError("Missing dependency 'underthesea'. Install with: pip install underthesea")

    text = text.lower()
    tokens = vi_word_tokenize(text, format="list")

    # Keep only word tokens and normalize multi-word tokens with underscores.
    normalized = []
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        parts = re.findall(r"[\w_]+", tok, re.UNICODE)
        normalized.extend(parts)

    return normalized


def is_it_domain(en_text: str) -> int:
    """Score how IT-related a sentence is (keyword count)."""
    text_lower = en_text.lower()
    return sum(1 for kw in IT_KEYWORDS_EN if kw in text_lower)


def is_medical_domain(en_text: str) -> int:
    """Score how medical-related a sentence is (keyword count)."""
    text_lower = en_text.lower()
    return sum(1 for kw in MEDICAL_KEYWORDS_EN if kw in text_lower)


def is_business_domain(en_text: str) -> int:
    """Score how business/economy-related a sentence is (keyword count)."""
    text_lower = en_text.lower()
    return sum(1 for kw in BUSINESS_KEYWORDS_EN if kw in text_lower)


def is_general_domain(en_text: str) -> int:
    """Score how general daily-life communication a sentence is (keyword count)."""
    text_lower = en_text.lower()
    return sum(1 for kw in GENERAL_KEYWORDS_EN if kw in text_lower)


def is_valid_pair(en: str, vi: str) -> bool:
    """Quality filter: length, ratio, alphabet presence."""
    en_w, vi_w = en.split(), vi.split()
    if len(en_w) < MIN_LEN or len(vi_w) < MIN_LEN:
        return False
    if len(en_w) > MAX_SRC_LEN or len(vi_w) > MAX_TGT_LEN:
        return False
    ratio = len(vi_w) / max(len(en_w), 1)
    if ratio > 4.0 or ratio < 0.25:
        return False
    if not re.search(r'[a-zA-Z]', en):
        return False
    if not re.search(r'[a-zA-Z\u00c0-\u1ef9]', vi):
        return False
    return True


def coverage_at(vocab_counter: Counter, threshold: float) -> int:
    """How many unique words cover `threshold`% of total tokens."""
    total = sum(vocab_counter.values())
    target = total * threshold
    cumulative = 0
    for i, (_, count) in enumerate(vocab_counter.most_common(), 1):
        cumulative += count
        if cumulative >= target:
            return i
    return len(vocab_counter)


def compute_length_stats(lengths: list) -> dict:
    """Descriptive stats for a list of lengths."""
    s = sorted(lengths)
    n = len(s)
    return {
        "count": n,
        "mean": round(statistics.mean(s), 2),
        "median": round(statistics.median(s), 2),
        "stdev": round(statistics.stdev(s), 2) if n > 1 else 0,
        "min": s[0],
        "max": s[-1],
        "p25": s[n // 4],
        "p75": s[3 * n // 4],
    }


def clean_and_filter_pairs(pairs: list) -> tuple:
    """Normalize, remove noisy artifacts, synchronize punctuation, deduplicate, and quality-filter pairs."""
    prepared = []
    artifact_filtered = 0
    tab_filtered = 0
    for p in pairs:
        if has_tab_artifact(p["en"]) or has_tab_artifact(p["vi"]):
            tab_filtered += 1
            continue

        en_text = normalize_text(p["en"])
        vi_text = normalize_text(p["vi"])

        if is_noisy_artifact_text(en_text) or is_noisy_artifact_text(vi_text):
            artifact_filtered += 1
            continue

        en_text, vi_text = sync_pair_punctuation(en_text, vi_text)
        prepared.append({"en": en_text, "vi": vi_text})

    seen = set()
    unique, dup = [], 0
    for p in prepared:
        h = hashlib.md5((p["en"] + "|||" + p["vi"]).encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(p)
        else:
            dup += 1

    clean = [p for p in unique if is_valid_pair(p["en"], p["vi"])]
    quality_filtered = len(unique) - len(clean)
    return clean, dup, quality_filtered, artifact_filtered, tab_filtered


# ============================================================
# MAIN PIPELINE
# ============================================================
def main():
    from datasets import load_dataset

    # --- STEP 1: Load ---
    print("=" * 60)
    print("STEP 1: Loading dataset ura-hcmut/PhoMT ...")
    print("=" * 60)
    ds = load_dataset("ura-hcmut/PhoMT", split="train")
    print(f"  Total raw samples: {len(ds):,}")
    print(f"  Columns: {ds.column_names}")

    # --- STEP 2: Extract EN-VI pairs ---
    print("\nSTEP 2: Extracting EN-VI pairs ...")
    pairs = []
    for row in ds:
        # Adapt to actual column names
        en = row.get("en") or row.get("source") or ""
        vi = row.get("vi") or row.get("target") or ""
        if not en or not vi:
            trans = row.get("translation", {})
            if isinstance(trans, dict):
                en = trans.get("en", "")
                vi = trans.get("vi", "")
        if en and vi:
            pairs.append({"en": str(en).strip(), "vi": str(vi).strip()})
    print(f"  Extracted: {len(pairs):,} pairs")

    # --- STEP 3: Domain filter ---
    print("\nSTEP 3A: Filtering IT domain ...")
    scored = [(is_it_domain(p["en"]), p) for p in pairs]
    scored.sort(key=lambda x: -x[0])

    it_pairs = [dict(p) for sc, p in scored if sc >= 1]
    print(f"  Pairs with IT score >= 1: {len(it_pairs):,}")

    if len(it_pairs) < TARGET_SIZE:
        gap = TARGET_SIZE - len(it_pairs)
        general = [p for sc, p in scored if sc == 0][:gap]
        it_pairs.extend(general)
        print(f"  Supplemented with {len(general):,} general pairs")
    else:
        it_pairs = it_pairs[:TARGET_SIZE]
    print(f"  After filter: {len(it_pairs):,}")

    print("\nSTEP 3B: Filtering Medical domain ...")
    med_scored = [(is_medical_domain(p["en"]), p) for p in pairs]
    med_scored.sort(key=lambda x: -x[0])
    med_pairs = [dict(p) for sc, p in med_scored if sc >= 1][:TARGET_SIZE]
    print(f"  Pairs with Medical score >= 1: {len(med_pairs):,}")

    print("\nSTEP 3C: Filtering Business domain ...")
    business_scored = [(is_business_domain(p["en"]), p) for p in pairs]
    business_scored.sort(key=lambda x: -x[0])
    business_pairs = [dict(p) for sc, p in business_scored if sc >= 1][:TARGET_SIZE]
    print(f"  Pairs with Business score >= 1: {len(business_pairs):,}")

    print("\nSTEP 3D: Filtering General daily-life domain ...")
    general_candidates = []
    for p in pairs:
        it_score = is_it_domain(p["en"])
        med_score = is_medical_domain(p["en"])
        business_score = is_business_domain(p["en"])
        general_score = is_general_domain(p["en"])

        # Keep general only when not specialized in IT/Medical/Business.
        if it_score == 0 and med_score == 0 and business_score == 0:
            general_candidates.append((general_score, p))

    general_candidates.sort(key=lambda x: -x[0])
    general_pairs = [dict(p) for sc, p in general_candidates if sc >= 1][:TARGET_SIZE]

    if len(general_pairs) < TARGET_SIZE:
        gap = TARGET_SIZE - len(general_pairs)
        generic_fallback = [p for sc, p in general_candidates if sc == 0][:gap]
        general_pairs.extend(dict(p) for p in generic_fallback)
        print(f"  Supplemented with {len(generic_fallback):,} non-specialized pairs")

    print(f"  General non-specialized pairs: {len(general_pairs):,}")

    # --- STEP 4: Clean ---
    print("\nSTEP 4: Cleaning ...")
    before_clean = len(it_pairs)
    clean, dup, quality_filtered, artifact_filtered, tab_filtered = clean_and_filter_pairs(it_pairs)
    med_before_clean = len(med_pairs)
    med_clean, med_dup, med_quality_filtered, med_artifact_filtered, med_tab_filtered = clean_and_filter_pairs(med_pairs)
    business_before_clean = len(business_pairs)
    business_clean, business_dup, business_quality_filtered, business_artifact_filtered, business_tab_filtered = clean_and_filter_pairs(business_pairs)
    general_before_clean = len(general_pairs)
    general_clean, general_dup, general_quality_filtered, general_artifact_filtered, general_tab_filtered = clean_and_filter_pairs(general_pairs)

    print(f"  Duplicates removed: {dup}")
    print(f"  Artifact filtered: {artifact_filtered}")
    print(f"  Tab filtered: {tab_filtered}")
    print(f"  Quality filtered: {quality_filtered}")
    print(f"  Final clean: {len(clean):,}")
    print(f"  Medical duplicates removed: {med_dup}")
    print(f"  Medical artifact filtered: {med_artifact_filtered}")
    print(f"  Medical tab filtered: {med_tab_filtered}")
    print(f"  Medical quality filtered: {med_quality_filtered}")
    print(f"  Medical final clean: {len(med_clean):,}")
    print(f"  Business duplicates removed: {business_dup}")
    print(f"  Business artifact filtered: {business_artifact_filtered}")
    print(f"  Business tab filtered: {business_tab_filtered}")
    print(f"  Business quality filtered: {business_quality_filtered}")
    print(f"  Business final clean: {len(business_clean):,}")
    print(f"  General duplicates removed: {general_dup}")
    print(f"  General artifact filtered: {general_artifact_filtered}")
    print(f"  General tab filtered: {general_tab_filtered}")
    print(f"  General quality filtered: {general_quality_filtered}")
    print(f"  General final clean: {len(general_clean):,}")

    # --- STEP 5: Tokenize & Vocab ---
    print("\nSTEP 5: Tokenization & Vocabulary ...")
    en_vocab, vi_vocab = Counter(), Counter()
    en_lens, vi_lens = [], []
    for p in clean:
        et = simple_tokenize_en(p["en"])
        vt = simple_tokenize_vi(p["vi"])
        p["en_tokens"] = et
        p["vi_tokens"] = vt
        en_vocab.update(et)
        vi_vocab.update(vt)
        en_lens.append(len(et))
        vi_lens.append(len(vt))
    print(f"  EN vocab: {len(en_vocab):,} | VI vocab: {len(vi_vocab):,}")
    print(f"  Avg EN len: {statistics.mean(en_lens):.1f} | Avg VI len: {statistics.mean(vi_lens):.1f}")

    # --- STEP 6: Statistics ---
    print("\nSTEP 6: Computing statistics ...")
    en_stats = compute_length_stats(en_lens)
    vi_stats = compute_length_stats(vi_lens)
    ratios = [v / max(e, 1) for e, v in zip(en_lens, vi_lens)]
    ratio_stats = compute_length_stats(ratios)

    en_total = sum(en_vocab.values())
    vi_total = sum(vi_vocab.values())
    en_hapax = sum(1 for _, c in en_vocab.items() if c == 1)
    vi_hapax = sum(1 for _, c in vi_vocab.items() if c == 1)

    report = {
        "dataset_info": {
            "source": "hiimbach/mtet",
                "domain_focus": "IT / Medical / Business / General",
            "total_raw": len(pairs),
            "after_it_filter": before_clean,
            "after_medical_filter": med_before_clean,
                "after_business_filter": business_before_clean,
                "after_general_filter": general_before_clean,
            "duplicates_removed": dup,
            "artifact_filtered": artifact_filtered,
            "tab_filtered": tab_filtered,
            "medical_duplicates_removed": med_dup,
            "medical_artifact_filtered": med_artifact_filtered,
            "medical_tab_filtered": med_tab_filtered,
                "business_duplicates_removed": business_dup,
                "business_artifact_filtered": business_artifact_filtered,
                "business_tab_filtered": business_tab_filtered,
                "general_duplicates_removed": general_dup,
                "general_artifact_filtered": general_artifact_filtered,
                "general_tab_filtered": general_tab_filtered,
            "quality_filtered": quality_filtered,
            "medical_quality_filtered": med_quality_filtered,
                "business_quality_filtered": business_quality_filtered,
                "general_quality_filtered": general_quality_filtered,
            "final_clean": len(clean),
            "medical_final_clean": len(med_clean),
                "business_final_clean": len(business_clean),
                "general_final_clean": len(general_clean),
        },
        "sentence_length": {
            "english": en_stats,
            "vietnamese": vi_stats,
            "vi_en_ratio": ratio_stats,
        },
        "vocabulary": {
            "english": {
                "vocab_size": len(en_vocab),
                "total_tokens": en_total,
                "type_token_ratio": round(len(en_vocab) / max(en_total, 1), 4),
                "hapax_legomena": en_hapax,
                "hapax_ratio": round(en_hapax / max(len(en_vocab), 1), 4),
                "coverage_90pct": coverage_at(en_vocab, 0.90),
                "coverage_95pct": coverage_at(en_vocab, 0.95),
                "top_30": en_vocab.most_common(30),
            },
            "vietnamese": {
                "vocab_size": len(vi_vocab),
                "total_tokens": vi_total,
                "type_token_ratio": round(len(vi_vocab) / max(vi_total, 1), 4),
                "hapax_legomena": vi_hapax,
                "hapax_ratio": round(vi_hapax / max(len(vi_vocab), 1), 4),
                "coverage_90pct": coverage_at(vi_vocab, 0.90),
                "coverage_95pct": coverage_at(vi_vocab, 0.95),
                "top_30": vi_vocab.most_common(30),
            },
        },
        "samples": [{"en": p["en"], "vi": p["vi"]} for p in clean[:10]],
    }

    # --- STEP 7: Save ---
    print("\nSTEP 7: Saving outputs ...")

    # CSV
    csv_path = os.path.join(OUTPUT_DIR, "dataset_en_vi_it_clean.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "en", "vi", "en_len", "vi_len"])
        w.writeheader()
        for i, p in enumerate(clean):
            w.writerow({"id": i, "en": p["en"], "vi": p["vi"],
                         "en_len": len(p["en_tokens"]), "vi_len": len(p["vi_tokens"])})

    # Medical CSV
    med_csv_path = os.path.join(OUTPUT_DIR, "dataset_en_vi_medical_clean.csv")
    with open(med_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "en", "vi", "en_len", "vi_len"])
        w.writeheader()
        for i, p in enumerate(med_clean):
            w.writerow({"id": i, "en": p["en"], "vi": p["vi"],
                         "en_len": len(simple_tokenize_en(p["en"])),
                         "vi_len": len(simple_tokenize_vi(p["vi"]))})

    # Business CSV
    business_csv_path = os.path.join(OUTPUT_DIR, "dataset_en_vi_business_clean.csv")
    with open(business_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "en", "vi", "en_len", "vi_len"])
        w.writeheader()
        for i, p in enumerate(business_clean):
            w.writerow({"id": i, "en": p["en"], "vi": p["vi"],
                         "en_len": len(simple_tokenize_en(p["en"])),
                         "vi_len": len(simple_tokenize_vi(p["vi"]))})

    # General CSV
    general_csv_path = os.path.join(OUTPUT_DIR, "dataset_en_vi_general_clean.csv")
    with open(general_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "en", "vi", "en_len", "vi_len"])
        w.writeheader()
        for i, p in enumerate(general_clean):
            w.writerow({"id": i, "en": p["en"], "vi": p["vi"],
                         "en_len": len(simple_tokenize_en(p["en"])),
                         "vi_len": len(simple_tokenize_vi(p["vi"]))})

    # Merged multi-domain CSV (requested: en, vi, domain)
    merged_csv_path = os.path.join(OUTPUT_DIR, "dataset_en_vi_all_domains.csv")
    with open(merged_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["en", "vi", "domain"])
        w.writeheader()
        for p in clean:
            w.writerow({"en": p["en"], "vi": p["vi"], "domain": "it"})
        for p in med_clean:
            w.writerow({"en": p["en"], "vi": p["vi"], "domain": "medical"})
        for p in business_clean:
            w.writerow({"en": p["en"], "vi": p["vi"], "domain": "business"})
        for p in general_clean:
            w.writerow({"en": p["en"], "vi": p["vi"], "domain": "general"})

    # JSON
    json_path = os.path.join(OUTPUT_DIR, "dataset_en_vi_it_clean.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([{"id": i, "en": p["en"], "vi": p["vi"],
                     "en_tokens": p["en_tokens"], "vi_tokens": p["vi_tokens"]}
                    for i, p in enumerate(clean)],
                  f, ensure_ascii=False, indent=2)

    # Vocab files
    for name, vocab in [("vocab_en.json", en_vocab), ("vocab_vi.json", vi_vocab)]:
        with open(os.path.join(OUTPUT_DIR, name), "w", encoding="utf-8") as f:
            json.dump(dict(vocab.most_common()), f, ensure_ascii=False, indent=2)

    # Report
    rpt_path = os.path.join(OUTPUT_DIR, "dataset_statistics_report.json")
    with open(rpt_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print("DONE! Output files in ./{OUTPUT_DIR}/")
    print(f"{'='*60}")
    print(f"  dataset_en_vi_it_clean.csv   ({len(clean):,} rows)")
    print(f"  dataset_en_vi_medical_clean.csv ({len(med_clean):,} rows)")
    print(f"  dataset_en_vi_business_clean.csv ({len(business_clean):,} rows)")
    print(f"  dataset_en_vi_general_clean.csv ({len(general_clean):,} rows)")
    print(f"  dataset_en_vi_all_domains.csv")
    print(f"  dataset_en_vi_it_clean.json")
    print(f"  vocab_en.json                ({len(en_vocab):,} entries)")
    print(f"  vocab_vi.json                ({len(vi_vocab):,} entries)")
    print(f"  dataset_statistics_report.json")


if __name__ == "__main__":
    main()
