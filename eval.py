import os
import torch
import pandas as pd
import numpy as np
from tqdm import tqdm
from unsloth import FastLanguageModel
import sacrebleu
from evaluate import load
import re

from config import *
from model import load_base_model, load_lora_checkpoint
from dataset import prepare_raw_data
from promp import chatml_prompt


# ==============================================================================
# 1. PREPARE TEST DATA (Using shared prepare_raw_data from dataset.py)
# ==============================================================================
def prepare_test_data(test_size_limit=500):
    """
    Prepare test set from shared dataset split
    
    Args:
        test_size_limit: Limit number of test samples (None for all)
    
    Returns:
        test_df: Test dataframe
    """
    print("1️⃣ Preparing test dataset...")
    _, _, test_df = prepare_raw_data()
    
    if test_size_limit:
        test_df = test_df.head(test_size_limit)
    
    print(f"✅ Test set size: {len(test_df)} samples")
    return test_df


# ==============================================================================
# 2. LOAD MODEL
# ==============================================================================
def load_model(model_path):
    """
    Load finetuned model and tokenizer
    
    Args:
        model_path: Path to model or checkpoint
    
    Returns:
        model, tokenizer
    """
    print(f"2️⃣ Loading model from: {model_path}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=MAX_SEQ_LENGTH,
        load_in_4bit=True,
        local_files_only=True,
    )
    FastLanguageModel.for_inference(model)
    print("✅ Model loaded successfully")
    return model, tokenizer


# ==============================================================================
# 3. TRANSLATION FUNCTION WITH IMPROVED POST-PROCESSING
# ==============================================================================
def generate_translation(model, tokenizer, text, domain):
    """
    Generate translation with advanced post-processing
    
    Args:
        model: Finetuned model
        tokenizer: Model tokenizer
        text: English text to translate
        domain: Domain of text
    
    Returns:
        translation: Vietnamese translation
    """
    prompt = chatml_prompt.format(
        source_lang="English",
        target_lang="Vietnamese",
        domain=domain,
        user_input=text
    )
    
    inputs = tokenizer([prompt], return_tensors="pt").to("cuda")
    input_length = inputs.input_ids.shape[1]
    
    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=1024,
            do_sample=False,
            repetition_penalty=1.05,
            eos_token_id=[tokenizer.eos_token_id, 151645, 151643],
            pad_token_id=tokenizer.eos_token_id,
        )
    
    new_tokens = outputs[0][input_length:]
    translation = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    
    # Post-processing 1: Stop markers
    stop_markers = ["<|im_end|>", "<|im_start|>", "Dịch đoạn văn này:", "user\n", "system\n", "Note:", "Giải thích:", "^ Jump up ^"]
    for marker in stop_markers:
        if marker in translation:
            translation = translation.split(marker)[0].strip()

    # Post-processing 2: Match output lines to input lines
    input_lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    output_lines = [l.strip() for l in translation.strip().split('\n') if l.strip()]
    
    if len(input_lines) > 0 and len(output_lines) > len(input_lines):
        translation = "\n".join(output_lines[:len(input_lines)])
    else:
        translation = "\n".join(output_lines)
    
    # Post-processing 3: Clean trailing garbage
    translation = re.split(r'(\.|\•|\*){5,}', translation)[0]
    translation = re.sub(r'[\)\.\s\-\'\"\\/]+$', '', translation)
    
    return translation.strip()


# ==============================================================================
# 4. CALCULATE METRICS
# ==============================================================================
def calculate_metrics(predictions, references):
    """
    Calculate evaluation metrics
    
    Args:
        predictions: List of predictions
        references: List of references
    
    Returns:
        Dictionary of metrics
    """
    print("\n4️⃣ Calculating metrics...")
    
    refs_sacrebleu = [references]
    
    # BLEU Score
    bleu = sacrebleu.corpus_bleu(predictions, refs_sacrebleu)
    
    # chrF Score
    chrf = sacrebleu.corpus_chrf(predictions, refs_sacrebleu)
    
    # TER Score
    ter = sacrebleu.corpus_ter(predictions, refs_sacrebleu)
    
    # ROUGE Score
    rouge_metric = load("rouge")
    rouge_results = rouge_metric.compute(predictions=predictions, references=references)
    
    return {
        "bleu": bleu.score,
        "chrf": chrf.score,
        "ter": ter.score,
        "rouge_l": rouge_results['rougeL'] * 100
    }


# ==============================================================================
# MAIN EVALUATION FUNCTION
# ==============================================================================
def main(model_path=None, test_size_limit=500):
    """
    Main evaluation function
    
    Args:
        model_path: Path to finetuned model. If None, uses MODEL_SAVE_NAME
        test_size_limit: Limit test samples (for faster evaluation)
    """
    if model_path is None:
        model_path = MODEL_SAVE_NAME
    
    # Prepare test data
    test_df = prepare_test_data(test_size_limit)
    
    # Load model
    model, tokenizer = load_model(model_path)
    
    # Generate translations
    print("\n3️⃣ Generating translations...")
    predictions = []
    references = []
    domains = []
    
    for idx, row in tqdm(test_df.iterrows(), total=len(test_df), desc="Translating"):
        en_text = row['en']
        vi_ref = row['vi']
        domain = row['domain']
        
        pred = generate_translation(model, tokenizer, en_text, domain)
        
        predictions.append(pred)
        references.append(vi_ref)
        domains.append(domain)
    
    # Calculate metrics
    metrics = calculate_metrics(predictions, references)
    
    # Display results
    print("\n" + "=" * 60)
    print("🏆 EVALUATION RESULTS ON TEST SET")
    print("=" * 60)
    print(f"🔹 BLEU Score  : {metrics['bleu']:.2f} (>30 good, >40 excellent)")
    print(f"🔹 chrF Score  : {metrics['chrf']:.2f} (>50 good)")
    print(f"🔹 TER Score   : {metrics['ter']:.2f} (<40 good)")
    print(f"🔹 ROUGE-L     : {metrics['rouge_l']:.2f}")
    print("=" * 60)

    # Domain-level metrics
    print("\n5. Đang tính metrics theo từng domain...")
    df_eval = pd.DataFrame({
        "domain": domains,
        "pred": predictions,
        "ref": references
    })

    rouge_metric = load("rouge")
    domain_results = []

    for domain, group in df_eval.groupby("domain"):
        preds = group["pred"].tolist()
        refs = group["ref"].tolist()

        bleu = sacrebleu.corpus_bleu(preds, [refs])
        chrf = sacrebleu.corpus_chrf(preds, [refs])
        ter = sacrebleu.corpus_ter(preds, [refs])
        rouge = rouge_metric.compute(predictions=preds, references=refs)

        domain_results.append({
            "domain": domain,
            "count": len(group),
            "bleu": bleu.score,
            "chrf": chrf.score,
            "ter": ter.score,
            "rougeL": rouge["rougeL"] * 100
        })

    domain_df = pd.DataFrame(domain_results).sort_values("bleu", ascending=False)

    print("\n" + "=" * 70)
    print("📊 KẾT QUẢ THEO TỪNG DOMAIN")
    print("=" * 70)
    print(domain_df.to_string(index=False))
    print("=" * 70)

    return metrics


if __name__ == "__main__":
    main()