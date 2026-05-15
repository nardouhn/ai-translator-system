import os
import torch
import gc
from safetensors.torch import load_file, save_file
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
from peft import PeftConfig, PeftModel
import json
from tqdm import tqdm
import sys

# Tự động thêm thư mục gốc của dự án vào PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

def manual_merge_layer_by_layer():
    # Cấu hình đường dẫn tương đối dựa trên project_root
    base_model_name = "Qwen/Qwen2.5-7B-Instruct"
    adapter_path = os.path.join(project_root, "outputs", "checkpoint-3000")
    output_path = os.path.join(project_root, "outputs", "completed_model")
    
    print(f"=== BẮT ĐẦU GỘP MÔ HÌNH (TỐI ƯU RAM) ===")
    
    # 1. Tìm đường dẫn cache của Base Model
    from huggingface_hub import snapshot_download
    print(f"Đang xác định vị trí Base Model: {base_model_name}...")
    base_model_path = snapshot_download(base_model_name, allow_patterns=["*.safetensors", "*.json"])
    
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # 2. Nạp Adapter Weights
    print("\n[1/5] Đang nạp LoRA Adapter weights...")
    adapter_safetensors = os.path.join(adapter_path, "adapter_model.safetensors")
    if not os.path.exists(adapter_safetensors):
        print(f"❌ Lỗi: Không tìm thấy {adapter_safetensors}")
        return
        
    adapter_weights = load_file(adapter_safetensors)
    
    with open(os.path.join(adapter_path, "adapter_config.json"), "r") as f:
        adapter_config = json.load(f)
    
    scaling = adapter_config.get("lora_alpha", 16) / adapter_config.get("r", 8)

    # 3. Duyệt qua từng file shard
    shards = [f for f in os.listdir(base_model_path) if f.endswith(".safetensors")]
    shards.sort()
    
    for shard_name in shards:
        print(f"\n--- Đang xử lý file: {shard_name} ---")
        shard_path = os.path.join(base_model_path, shard_name)
        base_weights = load_file(shard_path)
        merged_weights = {}

        for key in tqdm(base_weights.keys(), desc="Gộp layers"):
            weight = base_weights[key].to(torch.float16)
            
            adapter_key_prefix = f"base_model.model.{key.replace('.weight', '')}"
            lora_A_key = f"{adapter_key_prefix}.lora_A.weight"
            lora_B_key = f"{adapter_key_prefix}.lora_B.weight"

            if lora_A_key in adapter_weights and lora_B_key in adapter_weights:
                A = adapter_weights[lora_A_key].to(torch.float16)
                B = adapter_weights[lora_B_key].to(torch.float16)
                weight = weight + (B @ A) * scaling
                
            merged_weights[key] = weight

        save_path = os.path.join(output_path, shard_name)
        save_file(merged_weights, save_path)
        del base_weights, merged_weights
        gc.collect()

    # 4. Sao chép cấu hình
    print("\n[3/5] Đang sao chép các file cấu hình...")
    import shutil
    for f in os.listdir(base_model_path):
        if f.endswith(".json"):
            shutil.copy(os.path.join(base_model_path, f), os.path.join(output_path, f))
    
    tokenizer = AutoTokenizer.from_pretrained(adapter_path, trust_remote_code=True)
    tokenizer.save_pretrained(output_path)
    print(f"✅ Hoàn thành gộp tại: {output_path}")

if __name__ == "__main__":
    manual_merge_layer_by_layer()
