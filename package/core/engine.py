import os
import torch
from typing import Optional
from transformers import AutoModelForCausalLM, AutoTokenizer

class TranslationEngine:
    """Base class for translation engines."""
    def generate(self, prompt: str, stream: bool = False) -> str:
        raise NotImplementedError("Subclasses must implement generate()")

class CloudInferenceEngine(TranslationEngine):
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.is_mlx = False
        self._load_model()

    def _load_model(self):
        if not os.path.exists(self.model_path):
            print(f"⚠️ Engine: Path '{self.model_path}' not found locally. Assuming it's a HuggingFace repo ID and attempting to download...")

        print(f"Engine: Loading model from {self.model_path}...")
        
        # Check if MLX is available (for local Mac testing)
        try:
            from mlx_lm import load
            print("Engine: [MLX] Detected Apple Silicon environment. Loading with MLX...")
            self.model, self.tokenizer = load(self.model_path)
            self.is_mlx = True
            print("Engine: ✅ MLX model loaded successfully.")
        except ImportError:
            # Standard Transformers for Cloud (Linux/GPU/CPU)
            print("Engine: [Torch] Loading with standard Transformers...")
            self.is_mlx = False
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
            
            # Determine device
            if torch.cuda.is_available():
                device = "cuda"
                dtype = torch.float16
                print(f"Engine: Detected CUDA GPU. Using {dtype}.")
            else:
                device = "cpu"
                dtype = torch.float32
                print(f"Engine: No GPU detected. Using CPU with {dtype}.")
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=dtype,
                device_map="auto" if device == "cuda" else None,
                trust_remote_code=True
            )
            if device == "cpu":
                self.model = self.model.to("cpu")
            print("Engine: ✅ Transformers model loaded successfully.")
        except Exception as e:
            print(f"❌ Engine: Failed to load model: {e}")
            self.model = None

    def generate(self, prompt: str, stream: bool = False) -> str:
        if not self.model:
            return "[ERROR] Model not loaded. Check MODEL_PATH environment variable."

        if self.is_mlx:
            from mlx_lm import generate
            from mlx_lm.sample_utils import make_sampler
            sampler = make_sampler(temp=0.0)
            return generate(self.model, self.tokenizer, prompt=prompt, max_tokens=512, sampler=sampler)
        else:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    do_sample=False
                )
            input_length = inputs.input_ids.shape[1]
            return self.tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True)

class GeminiInferenceEngine(TranslationEngine):
    """
    Engine sử dụng Google Gemini API.
    Yêu cầu: pip install google-generativeai
    Và phải set biến môi trường GEMINI_API_KEY.
    """
    def __init__(self, model_name: str = "gemini-1.5-pro"):
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("⚠️ CẢNH BÁO: Chưa cấu hình GEMINI_API_KEY. Vui lòng export GEMINI_API_KEY=your_key")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        print(f"Engine: ✅ Khởi tạo thành công kết nối tới Google {model_name}")

    def generate(self, prompt: str, stream: bool = False) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"[LỖI GEMINI API]: {str(e)}"
