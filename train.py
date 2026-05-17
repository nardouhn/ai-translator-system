import os
import gc
import numpy as np
import torch
from transformers import TrainingArguments, TrainerCallback, Trainer
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM

from config import *
from model import setup_environment, load_base_model, initialize_lora_for_training
from dataset import load_dataset


# ============================================================================
# CALLBACKS
# ============================================================================
class PrintEvalLossCallback(TrainerCallback):
    """Custom callback to print evaluation loss and perplexity"""
    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        if metrics and "eval_loss" in metrics:
            loss = metrics["eval_loss"]
            print("\n" + "=" * 60)
            print(f"📊 Step {state.global_step}: Eval Loss = {loss:.6f}")
            print(f"   Perplexity = {np.exp(loss):.2f}")
            print("=" * 60 + "\n")


# ============================================================================
# TRAINER PATCH
# ============================================================================
def patch_trainer():
    """Patch Trainer to remove conflicting tokenizer arguments"""
    original_init = Trainer.__init__

    def patched(self, *args, **kwargs):
        kwargs.pop("tokenizer", None)
        kwargs.pop("processing_class", None)
        original_init(self, *args, **kwargs)

    Trainer.__init__ = patched
    return original_init


# ============================================================================
# TRAINING CONFIGURATION
# ============================================================================
def create_training_args():
    """Create training arguments for SFTTrainer"""
    return TrainingArguments(
        per_device_train_batch_size=PER_DEVICE_TRAIN_BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        gradient_checkpointing=True,
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
        save_total_limit=3,
        output_dir=OUTPUT_DIR,
        seed=SEED,
        report_to="none"  # Offline mode
    )


# ============================================================================
# MAIN TRAINING FUNCTION
# ============================================================================
def train_from_scratch():
    """Train model from scratch (no checkpoint resume)"""
    
    print("\n" + "=" * 80)
    print("🚀 TRAINING FROM SCRATCH (QWEN 2.5 7B TRANSLATOR)")
    print("=" * 80)
    
    # Setup environment
    setup_environment()
    
    # Load base model
    model, tokenizer = load_base_model(BASE_MODEL_PATH, MAX_SEQ_LENGTH)
    
    # Initialize LoRA for training
    model = initialize_lora_for_training(model)
    
    # Load dataset
    print("\n📊 Loading dataset...")
    train_data, valid_data, _ = load_dataset(tokenizer)
    print(f"✅ Train: {len(train_data):,} | Valid: {len(valid_data):,}")
    
    # Setup data collator
    print("\n⚙️  Setting up data collator...")
    response_template = "<|im_start|>assistant\n"
    collator = DataCollatorForCompletionOnlyLM(
        response_template=response_template,
        tokenizer=tokenizer
    )
    model.tokenizer = tokenizer
    
    # Create training arguments
    training_args = create_training_args()
    
    # Apply Trainer patch
    original_init = patch_trainer()
    
    # Initialize trainer
    print("\n🏋️  Initializing trainer...")
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
    
    # Remove NotebookProgressCallback if it exists
    try:
        trainer.remove_callback("NotebookProgressCallback")
        print("✅ Removed NotebookProgressCallback")
    except ValueError:
        pass
    
    # Restore original Trainer init
    Trainer.__init__ = original_init
    
    # Start training
    print("\n" + "=" * 80)
    print("▶️  STARTING TRAINING FROM SCRATCH...")
    print("=" * 80)
    trainer.train()
    
    # Final evaluation
    print("\n" + "=" * 80)
    print("📋 FINAL EVALUATION ON VALIDATION SET")
    print("=" * 80)
    final_eval = trainer.evaluate()
    print(f"\n✅ Final Eval Loss: {final_eval['eval_loss']:.6f}")
    print(f"✅ Final Perplexity: {np.exp(final_eval['eval_loss']):.2f}")
    print(f"✅ Best model checkpoint: {trainer.state.best_model_checkpoint}")
    
    # Save final model
    print("\n" + "=" * 80)
    print("💾 SAVING FINAL MODEL")
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