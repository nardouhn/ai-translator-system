import requests
import json
import os
from typing import Optional

class TranslationEngine:
    """Base class cho động cơ dịch thuật."""
    def generate(self, prompt: str) -> str:
        raise NotImplementedError("Subclasses must implement generate()")

# --- 1. Đầu chờ cho File trọng số cục bộ (Sử dụng Transformers) ---
class LocalFileModelConnector(TranslationEngine):
    def __init__(self, model_path: str, device: str = "auto"):
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.device = device
        
        # Chỉ thực hiện nạp khi được gọi hoặc kiểm tra tồn tại
        if os.path.exists(model_path):
            self._load_model()
        else:
            print(f"⚠️ Cảnh báo: Không tìm thấy file trọng số tại {model_path}. Chế độ Local sẽ không hoạt động.")

    def _load_model(self):
        # 1. Kiểm tra xem thư mục có chứa mô hình MLX không
        is_mlx_model = "mlx" in self.model_path.lower() or os.path.exists(os.path.join(self.model_path, "merges.txt"))
        
        try:
            from mlx_lm import load
            print(f"Engine [MLX]: Đang nạp mô hình từ {self.model_path}...")
            self.model, self.tokenizer = load(self.model_path)
            print("✅ Nạp mô hình MLX thành công.")
        except ImportError:
            if is_mlx_model:
                print(f"❌ Lỗi: Mô hình tại {self.model_path} là định dạng MLX nhưng thư viện 'mlx-lm' chưa được cài đặt trong môi trường Python này.")
                print("Hãy thử chạy lệnh: python3 -m pip install mlx-lm")
                return
            
            # Fallback cho Transformers (chỉ khi KHÔNG phải là mô hình MLX)
            print("⚠️ Cảnh báo: Thư viện 'mlx-lm' chưa có. Đang dùng fallback transformers cho mô hình tiêu chuẩn...")
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            dtype = torch.float16 if torch.backends.mps.is_available() else torch.float32
            offload_dir = "model_offload"
            if not os.path.exists(offload_dir): os.makedirs(offload_dir)
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=dtype,
                device_map="auto",
                low_cpu_mem_usage=True,
                offload_folder=offload_dir,
                trust_remote_code=True
            )
            print("✅ Nạp mô hình qua transformers thành công.")
        except Exception as e:
            print(f"❌ Lỗi khi nạp mô hình: {e}")

    def generate(self, prompt: str, stream: bool = False) -> str:
        if not self.model:
            return "[LỖI] Mô hình chưa được nạp. Hãy kiểm tra đường dẫn."
        
        # 1. Phát hiện mô hình MLX dựa trên type hoặc đặc trưng class
        is_mlx = "mlx" in str(type(self.model)).lower()
        
        if is_mlx:
            from mlx_lm import generate, stream_generate
            if stream:
                # Streaming mode using stream_generate
                full_response = ""
                # Bỏ temperature vì API bản này dùng sampler
                for response in stream_generate(self.model, self.tokenizer, prompt=prompt, max_tokens=512):
                    s = response.text
                    print(s, end="", flush=True)
                    full_response += s
                print() # Newline after stream
                return full_response
            else:
                # Normal mode
                return generate(self.model, self.tokenizer, prompt=prompt, max_tokens=512, temp=0.0, verbose=False)
        else:
            # 2. Fallback cho Transformers (Nếu người dùng không dùng bản MLX)
            import torch
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs, 
                    max_new_tokens=512, 
                    temperature=0.0, # Deterministic
                    do_sample=False,
                    repetition_penalty=1.1
                )
            # Chỉ lấy phần nội dung mới generated
            input_length = inputs.input_ids.shape[1]
            generated_tokens = outputs[0][input_length:]
            return self.tokenizer.decode(generated_tokens, skip_special_tokens=True)

# --- 2. Đầu chờ cho API Model (Dùng cho mô hình đang xây dựng) ---
class APIModelConnector(TranslationEngine):
    def __init__(self, api_url: str, api_key: Optional[str] = None):
        self.api_url = api_url
        self.api_key = api_key

    def generate(self, prompt: str) -> str:
        print(f"Engine: Đang gọi tới API tại {self.api_url}...")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        payload = {
            "prompt": prompt,
            "max_tokens": 512,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                result = response.json()
                # Tùy chỉnh format trả về tùy theo API của bạn
                return result.get("translation") or result.get("response") or result.get("generated_text", "")
            else:
                return f"[LỖI API] Status code: {response.status_code} - {response.text}"
        except Exception as e:
            return f"[LỖI KẾT NỐI API] {e}"

# --- 3. Mock Connector để Test nhanh ---
class MockEngine(TranslationEngine):
    def generate(self, prompt: str) -> str:
        return "[MOCK] Đây là kết quả trả về từ Engine giả lập để kiểm tra pipeline RAG."
