# ============================================================================
# MODEL & DATA PATHS
# ============================================================================
MAX_SEQ_LENGTH = 768
SEED = 3407

BASE_MODEL_PATH = "/kaggle/input/models/qwen-lm/qwen2.5/transformers/7b-instruct/1"
DATA_PATH = "/kaggle/input/datasets/haquangdo/final-dataset/final_dataset.csv"

OUTPUT_DIR = "outputs"
MAX_PER_DOMAIN = 15000
MODEL_SAVE_NAME = "qwen_domain_translator_lora"

# ============================================================================
# LORA CONFIGURATION
# ============================================================================
LORA_R = 8
LORA_ALPHA = 16
LORA_DROPOUT = 0
LORA_TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
LORA_BIAS = "none"

# ============================================================================
# TRAINING HYPERPARAMETERS
# ============================================================================
PER_DEVICE_TRAIN_BATCH_SIZE = 1
PER_DEVICE_EVAL_BATCH_SIZE = 1
GRADIENT_ACCUMULATION_STEPS = 8
LEARNING_RATE = 3e-4
NUM_TRAIN_EPOCHS = 1
WARMUP_STEPS = 100
LOGGING_STEPS = 10
EVAL_STEPS = 500
SAVE_STEPS = 500
WEIGHT_DECAY = 0.1
MAX_GRAD_NORM = 1.0