import os
import torch
from unsloth import FastLanguageModel
from peft import PeftModel

def load_base_model(path, max_seq_length):
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=path,
        max_seq_length=max_seq_length,
        load_in_4bit=True,
        local_files_only=True,
    )

    tokenizer.pad_token = tokenizer.eos_token
    model.config.pad_token_id = tokenizer.pad_token_id

    return model, tokenizer


def load_lora(model, checkpoint_path):
    model = PeftModel.from_pretrained(
        model,
        checkpoint_path,
        is_trainable=True
    )
    return model