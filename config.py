# ============================================================================
# MODEL & DATA PATHS
# ============================================================================
MAX_SEQ_LENGTH = 768
SEED = 3407

BASE_MODEL_PATH = "/kaggle/input/models/qwen-lm/qwen2.5/transformers/7b-instruct/1"
DATA_PATH = "/kaggle/input/datasets/lvn0805/dataset-finetune/dataset_en_vi_all_domains_filtered_v3.2.csv"

OUTPUT_DIR = "/kaggle/working/outputs"
MAX_PER_DOMAIN = 10000
MODEL_SAVE_NAME = "qwen_domain_translator_lora_v2_scratch"

# ============================================================================
# TRAINING HYPERPARAMETERS
# ============================================================================
PER_DEVICE_TRAIN_BATCH_SIZE = 8
PER_DEVICE_EVAL_BATCH_SIZE = 1
GRADIENT_ACCUMULATION_STEPS = 4
LEARNING_RATE = 2e-4
NUM_TRAIN_EPOCHS = 1
WARMUP_STEPS = 50
LOGGING_STEPS = 10
EVAL_STEPS = 250
SAVE_STEPS = 250
WEIGHT_DECAY = 0.1
MAX_GRAD_NORM = 1.0