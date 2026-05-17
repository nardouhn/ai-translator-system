import os
import torch
import gc
from unsloth import FastLanguageModel
from peft import PeftModel
from config import *

def setup_environment():
    """Setup CUDA environment and cleanup VRAM"""
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["UNSLOTH_DISABLE_STATS"] = "0"
    
    # Remove distributed training env vars
    for var in ["WORLD_SIZE", "RANK", "LOCAL_RANK"]:
        if var in os.environ:
            del os.environ[var]
    
    gc.collect()
    torch.cuda.empty_cache()
    print("✅ CUDA environment setup complete")


def load_base_model(path, max_seq_length):
    """Load base model from scratch (training from beginning)"""
    print("📥 Loading base model from scratch...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=path,
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=True,
        local_files_only=True,
    )

    tokenizer.pad_token = tokenizer.eos_token
    model.config.pad_token_id = tokenizer.pad_token_id
    
    print("✅ Base model loaded successfully")
    return model, tokenizer


def setup_lora_from_scratch(model):
    """Setup LoRA configuration from scratch for training"""
    print("🎯 Setting up LoRA configuration...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        target_modules=LORA_TARGET_MODULES,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        bias=LORA_BIAS,
        use_gradient_checkpointing="unsloth",
        random_state=SEED,
    )
    model.print_trainable_parameters()
    print("✅ LoRA setup complete")
    return model


def load_lora_checkpoint(model, checkpoint_path):
    """Load LoRA checkpoint (for resuming training)"""
    print(f"📂 Loading LoRA checkpoint from {checkpoint_path}...")
    model = PeftModel.from_pretrained(
        model,
        checkpoint_path,
        is_trainable=True
    )
    model = FastLanguageModel.for_training(model)
    model.print_trainable_parameters()
    print("✅ LoRA checkpoint loaded successfully")
    return model