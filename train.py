import os
import gc
import torch
import pandas as pd
import numpy as np
from datasets import Dataset
from sklearn.model_selection import train_test_split
from unsloth import FastLanguageModel
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM
from transformers import TrainingArguments, TrainerCallback, Trainer

from config import *
from model import setup_environment, load_base_model, setup_lora_from_scratch
from dataset import format_prompts, filter_length, prepare_raw_data
from promp import chatml_prompt


# ==============================================================================
# CALLBACKS
# ==============================================================================
class PrintEvalLossCallback(TrainerCallback):
    """Custom callback to print evaluation loss and perplexity"""
    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        if metrics and "eval_loss" in metrics:
            loss = metrics["eval_loss"]
            print("\n" + "=" * 60)
            print(f"📊 Step {state.global_step}: Eval Loss = {loss:.6f}")
            print(f"   Perplexity = {np.exp(loss):.2f}")
            print("=" * 60 + "\n")


# ==============================================================================
# TRAINER PATCH
# ==============================================================================
def patch_trainer():
    """Patch Trainer to remove conflicting tokenizer arguments"""
    original_init = Trainer.__init__

    def patched(self, *args, **kwargs):
        kwargs.pop("tokenizer", None)
        kwargs.pop("processing_class", None)
        original_init(self, *args, **kwargs)

    Trainer.__init__ = patched
    return original_init


# ==============================================================================
# PREPARE DATASETS (Using shared prepare_raw_data from dataset.py)
# ==============================================================================
def prepare_data(tokenizer):
    """Prepare training and validation datasets"""
    
    # Get raw data splits
    train_df, valid_df, test_df = prepare_raw_data()
    
    # Convert to HF Dataset
    train_data = Dataset.from_pandas(train_df)
    valid_data = Dataset.from_pandas(valid_df)
    
    # Format prompts
    print("📝 Formatting prompts...")
    train_data = train_data.map(
        lambda ex: format_prompts(ex, chatml_prompt),
        batched=True,
        remove_columns=train_data.column_names
    )
    valid_data = valid_data.map(
        lambda ex: format_prompts(ex, chatml_prompt),
        batched=True,
        remove_columns=valid_data.column_names
    )
    
    # Filter by length
    print("🔍 Filtering sequences by length...")
    train_data = train_data.filter(lambda x: filter_length(x, tokenizer, MAX_SEQ_LENGTH))
    valid_data = valid_data.filter(lambda x: filter_length(x, tokenizer, MAX_SEQ_LENGTH))
    
    print(f"\n--- FINAL DATA DISTRIBUTION ---")
    print(f"TRAIN: {len(train_data):,} | VALID: {len(valid_data):,} | TEST: {len(test_df):,}\n")
    
    return train_data, valid_data


# ==============================================================================
# TRAINING CONFIGURATION
# ==============================================================================
def create_training_args():
    """Create training arguments"""
    return TrainingArguments(
        per_device_train_batch_size=PER_DEVICE_TRAIN_BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        gradient_checkpointing_kwargs={'use_reentrant': False},
        learning_rate=LEARNING_RATE,
        num_train_epochs=NUM_TRAIN_EPOCHS,
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        per_device_eval_batch_size=PER_DEVICE_EVAL_BATCH_SIZE,
        weight_decay=WEIGHT_DECAY,
        warmup_steps=WARMUP_STEPS,
        fp16=True,
        max_grad_norm=MAX_GRAD_NORM,
        logging_steps=LOGGING_STEPS,
        logging_strategy="steps",
        logging_first_step=True,
        disable_tqdm=False,
        eval_strategy="steps",
        eval_steps=EVAL_STEPS,
        save_strategy="steps",
        save_steps=SAVE_STEPS,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        save_total_limit=2,
        output_dir=OUTPUT_DIR,
        seed=SEED,
        report_to="none"  # Offline mode
    )


# ==============================================================================
# MAIN TRAINING FUNCTION
# ==============================================================================
def train_from_scratch():
    """Train model from scratch"""
    
    print("\n" + "=" * 80)
    print("🚀 TRAINING FROM SCRATCH (QWEN 2.5 7B TRANSLATOR)")
    print("=" * 80)
    
    # Setup environment
    setup_environment()
    
    # Load model
    print("\n" + "=" * 80)
    print("1️⃣ LOADING BASE MODEL")
    print("=" * 80)
    model, tokenizer = load_base_model(BASE_MODEL_PATH, MAX_SEQ_LENGTH)
    
    # Setup LoRA
    print("\n" + "=" * 80)
    print("2️⃣ SETTING UP LORA")
    print("=" * 80)
    model = setup_lora_from_scratch(model)
    
    # Prepare datasets
    print("\n" + "=" * 80)
    print("3️⃣ PREPARING DATASETS")
    print("=" * 80)
    train_data, valid_data = prepare_data(tokenizer)
    
    # Setup data collator
    print("\n" + "=" * 80)
    print("4️⃣ SETTING UP DATA COLLATOR")
    print("=" * 80)
    response_template = "<|im_start|>assistant\n"
    collator = DataCollatorForCompletionOnlyLM(
        response_template=response_template,
        tokenizer=tokenizer
    )
    model.tokenizer = tokenizer
    
    # Verify response template
    tok = tokenizer.encode(response_template, add_special_tokens=False)
    print(f"Response template tokenized: {tokenizer.decode(tok)}")
    
    # Create training arguments
    training_args = create_training_args()
    
    # Apply Trainer patch
    print("\n" + "=" * 80)
    print("5️⃣ INITIALIZING TRAINER")
    print("=" * 80)
    original_init = patch_trainer()
    
    # Initialize trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_data,
        eval_dataset=valid_data,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        data_collator=collator,
        args=training_args,
        callbacks=[PrintEvalLossCallback()],
    )
    
    # Remove NotebookProgressCallback if exists
    try:
        trainer.remove_callback("NotebookProgressCallback")
        print("✅ Removed NotebookProgressCallback")
    except ValueError:
        pass
    
    # Restore original Trainer init
    Trainer.__init__ = original_init
    
    # Start training
    print("\n" + "=" * 80)
    print("▶️  STARTING TRAINING")
    print("=" * 80)
    trainer.train()
    
    # Final evaluation
    print("\n" + "=" * 80)
    print("📋 FINAL EVALUATION")
    print("=" * 80)
    final_eval = trainer.evaluate()
    print(f"\n✅ Final Eval Loss: {final_eval['eval_loss']:.6f}")
    print(f"✅ Final Perplexity: {np.exp(final_eval['eval_loss']):.2f}")
    print(f"✅ Best checkpoint: {trainer.state.best_model_checkpoint}")
    
    # Save model
    print("\n" + "=" * 80)
    print("💾 SAVING MODEL")
    print("=" * 80)
    model.save_pretrained(MODEL_SAVE_NAME)
    tokenizer.save_pretrained(MODEL_SAVE_NAME)
    print(f"✅ Model saved to: {MODEL_SAVE_NAME}/")
    print(f"✅ Tokenizer saved to: {MODEL_SAVE_NAME}/")
    
    print("\n" + "=" * 80)
    print("🎉 TRAINING COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    
    return trainer, model, tokenizer


if __name__ == "__main__":
    trainer, model, tokenizer = train_from_scratch()