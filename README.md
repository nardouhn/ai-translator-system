# AI Translator System

Một hệ thống dịch thuật AI chuyên dụng, được xây dựng để huấn luyện và đánh giá mô hình dịch tiếng Anh → tiếng Việt theo từng miền chuyên ngành.

## 🚀 Giới thiệu

Dự án này triển khai một pipeline dịch thuật dựa trên mô hình lớn Qwen và kỹ thuật LoRA để tinh chỉnh, kết hợp với dữ liệu dịch thuật có nhãn và prompt ChatML cho đầu vào/đầu ra chuẩn.

Hệ thống hiện tại bao gồm:
- `train.py`: Huấn luyện mô hình LoRA từ base model.
- `eval.py`: Đánh giá mô hình trên tập test với BLEU, chrF, TER, ROUGE.
- `dataset.py`: Chuẩn hóa, lọc và chia dữ liệu train/valid/test.
- `model.py`: Nạp base model, cấu hình LoRA, và cài đặt môi trường CUDA.
- `promp.py`: Prompt ChatML cho dịch thuật theo miền.
- `config.py`: Cấu hình hyperparameter và đường dẫn dữ liệu/mô hình.

## 📦 Yêu cầu cài đặt

Dự án sử dụng các thư viện chính sau:

- `torch>=2.1.0`
- `transformers>=4.41.0`
- `datasets>=2.19.0`
- `accelerate>=0.30.0`
- `peft>=0.11.0`
- `trl<0.9.0`
- `bitsandbytes>=0.43.0`
- `unsloth[colab-new]` từ GitHub
- `scikit-learn>=1.3.0`
- `pandas>=2.0.0`
- `numpy>=1.24.0`
- `tqdm>=4.66.0`
- `evaluate>=0.4.2`
- `sacrebleu>=2.4.0`
- `sentencepiece>=0.1.99`
- `protobuf>=4.25.0`
- `huggingface_hub>=0.23.0`

Cài đặt nhanh:

```bash
pip install -r requirements.txt
```

> Lưu ý: `BASE_MODEL_PATH` và `DATA_PATH` hiện đang trỏ đến dữ liệu trong môi trường Kaggle. Nếu chạy trên máy khác, bạn cần cập nhật lại `config.py` tương ứng.

## 🧩 Cấu trúc dự án

- `config.py`: Cấu hình mô hình, LoRA, hyperparameter và đường dẫn.
- `train.py`: Quy trình huấn luyện, chuẩn hóa dữ liệu, tạo trainer và lưu checkpoint.
- `eval.py`: Chuẩn bị tập test, tải mô hình finetuned, dịch và tính chỉ số đánh giá.
- `dataset.py`: Nạp dữ liệu CSV, loại bỏ missing/duplicate, chia tập và tạo prompt.
- `model.py`: Thiết lập môi trường CUDA, nạp base model, cấu hình LoRA.
- `promp.py`: Prompt cho ChatML với luật dịch nghiêm ngặt.
- `utils.py`: Các helper callback và patch cho Trainer.

## ▶️ Hướng dẫn sử dụng

### 1. Cập nhật cấu hình

Mở `config.py` và điều chỉnh:

- `BASE_MODEL_PATH`: đường dẫn tới base model Qwen.
- `DATA_PATH`: đường dẫn tới file CSV dữ liệu dịch.
- `MODEL_SAVE_NAME`: tên thư mục lưu mô hình sau khi huấn luyện.

### 2. Huấn luyện mô hình

```bash
python train.py
```

Quy trình huấn luyện sẽ:
- nạp base model Qwen
- cấu hình LoRA cho các lớp attention
- chuẩn hóa dữ liệu và tạo prompt ChatML
- huấn luyện bằng `SFTTrainer`
- lưu mô hình và tokenizer vào `MODEL_SAVE_NAME`

Notebook huấn luyện và đánh giá tham khảo:
- https://www.kaggle.com/code/lvn0805/qwen-model

### 3. Đánh giá mô hình

```bash
python eval.py
```

`eval.py` sẽ dùng checkpoint trong `MODEL_SAVE_NAME` (hoặc bạn có thể đổi `model_path`) để dịch trên tập test và tính BLEU, chrF, TER, ROUGE.

## 🧠 Luồng dữ liệu và mô hình

- Dữ liệu nguồn: file CSV chứa các cột `en`, `vi`, `domain`.
- Prompt `chatml_prompt` định nghĩa luật dịch nghiêm ngặt và yêu cầu đầu ra chuẩn.
- Mô hình base sử dụng `FastLanguageModel` từ `unsloth` với chế độ 4-bit.
- Kỹ thuật tinh chỉnh LoRA giúp giảm bộ tham số cần học và phù hợp với training trên GPU giới hạn.

## 💡 Ghi chú

- Mục tiêu chính của dự án là dịch sát nghĩa tiếng Anh sang tiếng Việt theo từng miền (domain).
- Cần đảm bảo dữ liệu CSV có cột `domain` để mô hình học khả năng dịch theo ngữ cảnh miền.
- Nếu muốn dùng checkpoint LoRA khởi động lại, có thể mở rộng `model.py` bằng hàm `load_lora_checkpoint`.

## 🛠️ Mở rộng

- Thêm script inference riêng nếu muốn deploy dịch online.
- Thêm pipeline test tự động cho nhiều miền.
- Khử tiếng nhiễu và kiểm tra chất lượng dữ liệu đầu vào.
