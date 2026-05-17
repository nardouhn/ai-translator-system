import os
import torch
import uvicorn
import gradio as gr
import re
from fastapi import FastAPI, Body
from threading import Thread
from transformers import AutoModelForCausalLM, AutoTokenizer

from core.rag_manager import RAGManager
MERGED_MODEL_PATH = os.getenv("MERGED_MODEL_PATH", "/home/model_deploy/qwen25_7b_merged")
MAX_SEQ_LENGTH = int(os.getenv("MAX_SEQ_LENGTH", "2048"))
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "/home/model_deploy/VectorDB/VectorDB")

# Khởi tạo RAG Manager
rag_manager = RAGManager(db_path=VECTOR_DB_PATH)

print(f"📦 Đang nạp model đã merge từ: {MERGED_MODEL_PATH} ...")

# Thiết lập device tự động (ưu tiên CUDA nếu có, không thì chạy CPU)
device = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(MERGED_MODEL_PATH, local_files_only=True)
from transformers import BitsAndBytesConfig

# Cấu hình ép xung và nén 4-bit (Giảm VRAM từ 15GB xuống 4.5GB)
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
)

model = AutoModelForCausalLM.from_pretrained(
    MERGED_MODEL_PATH,
    quantization_config=bnb_config,
    device_map="auto" if torch.cuda.is_available() else None,
    attn_implementation="flash_attention_2" if torch.cuda.is_available() else None,
    local_files_only=True
)

if device == "cpu":
    model.to("cpu")

print(f"✅ Model đã sẵn sàng trên {device.upper()}!")


def translate_text(text, domain="general"):
    if not text.strip(): return ""
    domain = domain.lower().strip()
    tm_context, glossary = rag_manager.get_context(text, domain=domain)

    prompt = rag_manager.format_prompt(text, tm_context, glossary, domain)
    stop_token_ids = [tokenizer.eos_token_id, 151645, 151643]
    
    inputs = tokenizer([prompt], return_tensors="pt").to(device)
    input_len = inputs.input_ids.shape[1]

    with torch.inference_mode():
        outputs = model.generate(
            input_ids=inputs.input_ids,
            attention_mask=inputs.attention_mask,
            max_new_tokens=1024, 
            use_cache=True,
            do_sample=False,
            repetition_penalty=1.05, 
            eos_token_id=stop_token_ids,
            pad_token_id=tokenizer.eos_token_id,
        )
        
    new_tokens = outputs[0][input_len:]
    translation = tokenizer.decode(new_tokens, skip_special_tokens=False).strip()
    
    # DỌN RÁC
    stop_markers = ["<|im_end|>", "<|im_start|>", "Dịch đoạn văn này:", "user\n", "system\n", "Note:", "Giải thích:", "^ Jump up ^"]
    for marker in stop_markers:
        if marker in translation:
            translation = translation.split(marker)[0].strip()

    # LOGIC ÉP SỐ DÒNG
    input_lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    output_lines = [l.strip() for l in translation.strip().split('\n') if l.strip()]
    
    if len(input_lines) > 0 and len(output_lines) > len(input_lines):
        translation = "\n".join(output_lines[:len(input_lines)])
    else:
        translation = "\n".join(output_lines)

    # Dọn dẹp ký tự thừa
    translation = re.split(r'(\.|\•|\*){5,}', translation)[0]
    translation = re.sub(r'[\)\.\s\-\'\"\\/]+$', '', translation)
    
    return translation.strip().replace("<|im_end|>", "")

# 3. CHUNKING VĂN BẢN DÀI
def translate_long_text(text, domain="general"):
    if len(text.split()) <= 400:
        return translate_text(text, domain)
    
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        word_count = len(sentence.split())
        if current_length + word_count <= 400:
            current_chunk.append(sentence)
            current_length += word_count
        else:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
            current_length = word_count
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    translated_results = []
    print(f"🚀 Đang dịch văn bản dài ({len(chunks)} đoạn)...")
    for i, chunk in enumerate(chunks):
        translated_results.append(translate_text(chunk, domain))
        
    return "\n\n".join(translated_results)


app = FastAPI()

@app.get("/")
async def health():
    return {"status": "online", "model": "Qwen 2.5 Fine-tuned (HuggingFace)"}

@app.post("/translate")
async def api_translate(text: str = Body(...), domain: str = Body("general")):
    result = translate_long_text(text, domain.lower())
    return {"translation": result}

def run_api(port):
    uvicorn.run(app, host="0.0.0.0", port=port)

with gr.Blocks(theme=gr.themes.Soft(), title="Qwen Translator Pro") as ui:
    gr.Markdown("# 🌐 Professional Domain Translator")
    gr.Markdown("Hỗ trợ dịch văn bản dài (5000 từ+) với độ chính xác cao bám sát bản gốc.")
    
    with gr.Row():
        with gr.Column():
            input_box = gr.Textbox(label="English Input", lines=12, placeholder="Dán văn bản cần dịch tại đây...")
            domain_box = gr.Dropdown(
                choices=["general", "technical", "economic", "medical"], 
                value="general", 
                label="Domain (Lower-case)"
            )
            btn = gr.Button("Dịch ngay 🚀", variant="primary")
        with gr.Column():
            output_box = gr.Textbox(label="Vietnamese Translation", lines=15, interactive=False)
            
    btn.click(translate_long_text, inputs=[input_box, domain_box], outputs=output_box)

if __name__ == "__main__":
    api_port = int(os.getenv("PORT", "8001"))
    ui_port = 7860

    print(f"\n" + "="*50)
    print(f"🚀 FASTAPI đang chạy tại: http://0.0.0.0:{api_port}/docs")
    print(f"🎨 GRADIO UI đang chạy tại: http://0.0.0.0:{ui_port}")
    print(f"="*50 + "\n")

    # Chạy FastAPI ngầm
    Thread(target=run_api, args=(api_port,), daemon=True).start()

    # Chạy UI
    ui.launch(
        server_name="0.0.0.0", 
        server_port=ui_port,
        share=True
    )
