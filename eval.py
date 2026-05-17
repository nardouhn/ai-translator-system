import torch
import numpy as np
from tqdm import tqdm
import evaluate

from config import *
from dataset import load_dataset
from model import load_base_model, load_lora

bleu = evaluate.load("bleu")
chrf = evaluate.load("chrf")


def translate(model, tokenizer, text, domain):

    prompt = f"""<|im_start|>system
You are a Professional Translation System.
Domain: {domain}
<|im_start|>user
Dịch đoạn văn này: {text}<|im_end|>
<|im_start|>assistant
"""

    inputs = tokenizer([prompt], return_tensors="pt").to("cuda")

    outputs = model.generate(
        **inputs,
        max_new_tokens=768,
        do_sample=False,
        temperature=0.1,
        repetition_penalty=1.02,
        no_repeat_ngram_size=5,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.eos_token_id,
    )

    full = tokenizer.decode(outputs[0], skip_special_tokens=True)

    if "assistant" in full:
        out = full.split("assistant")[-1].strip()
    else:
        out = full.strip()

    stop_markers = ["<|im_end|>", "<|im_start|>", "Dịch đoạn văn này:"]
    for m in stop_markers:
        if m in out:
            out = out.split(m)[0].strip()

    lines = [l.strip() for l in out.split("\n") if l.strip()]
    if len(lines) > 1:
        out = "\n".join(lines)

    return out.strip()


def main():

    _, _, test_df = load_dataset(None)

    model, tokenizer = load_base_model(BASE_MODEL_PATH, MAX_SEQ_LENGTH)
    model = load_lora(model, CHECKPOINT_PATH)

    from unsloth import FastLanguageModel
    FastLanguageModel.for_inference(model)

    preds, refs = [], []

    for _, row in tqdm(test_df.iterrows(), total=len(test_df)):
        pred = translate(model, tokenizer, row["en"], row["domain"])
        preds.append(pred)
        refs.append([row["vi"]])

    print("BLEU:", bleu.compute(predictions=preds, references=refs))
    print("chrF:", chrf.compute(predictions=preds, references=refs))


if __name__ == "__main__":
    main()