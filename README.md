# AI Translator System (EN-VI)

Hệ thống này tập trung vào xây dựng dữ liệu song ngữ Anh-Việt cho bài toán máy dịch, gồm 3 phần:

- Thu thập dữ liệu thô từ nhiều nguồn.
- Tiền xử lý, lọc chất lượng và tách theo domain.
- Khám phá và đánh giá chất lượng dữ liệu bằng notebook.

## Mục tiêu dự án

- Tạo tập dữ liệu EN-VI có chất lượng tốt cho huấn luyện/finetune mô hình dịch.
- Hỗ trợ dữ liệu đa domain: `it`, `medical`, `business`, `general`.
- Duy trì pipeline để tái lập và mở rộng dữ liệu.

## Cấu trúc thư mục

- `crawler.py`: Crawl dữ liệu thô từ Hugging Face, web song ngữ, và GitHub README song ngữ.
- `opus_en_vi.ipynb`: Tải và tổng hợp corpus EN-VI từ OPUS.
- `preprocess_pipeline.py`: Pipeline tiền xử lý và lọc chất lượng đa domain.
- `check_filter_quality (1).ipynb`: Kiểm tra chất lượng lọc (semantic filtering/back-translation).
- `eda_en_vi_translator.ipynb`: EDA và thống kê dữ liệu EN-VI.
- `dataset_en_vi_all_domains_filtered_v3.2.csv`: Dataset đã lọc (cột: `en,vi,domain`).



## 1) Crawl dữ liệu thô

Script `crawler.py` sinh bộ dữ liệu thô, gộp từ các nguồn:

- Hugging Face datasets (mặc định gồm 2 nguồn EN-VI).
- Các trang web song ngữ (truyền qua `--web-url`, có thể truyền nhiều lần).
- Các README song ngữ trên GitHub (truy vấn qua GitHub Search API).

### Đầu ra của crawler

Mặc định lưu vào thư mục `raw_dataset/`:

- `raw_dataset.parquet`
- `raw_dataset.jsonl`

Mỗi bản ghi có các cột:

- `en`: câu tiếng Anh
- `vi`: câu tiếng Việt
- `source`: nguồn dữ liệu
- `metadata`: metadata dạng JSON string

### Cách chạy crawler

```bash
pip install pandas datasets beautifulsoup4 pyarrow
python crawler.py --output-dir raw_dataset
```

Tùy chọn:

```bash
python crawler.py \
  --output-dir raw_dataset \
  --github-token <YOUR_GITHUB_TOKEN> \
  --web-url https://example.com/bilingual-page-1 \
  --web-url https://example.com/bilingual-page-2
```

## 2) Tiền xử lý và lọc đa domain

Script `preprocess_pipeline.py` đọc dataset `ura-hcmut/PhoMT` trên Hugging Face, sau đó thực hiện:

1. Trích xuất cặp câu EN-VI (hỗ trợ nhiều schema cột).
2. Chấm điểm domain theo tập keyword:
	- IT
	- Medical
	- Business
	- General (ưu tiên câu không chuyên ngành)
3. Làm sạch và lọc chất lượng:
	- Chuẩn hóa ký tự/khoảng trắng/dấu câu
	- Loại URL/noise artifacts/tab artifacts
	- Đồng bộ dấu câu EN-VI
	- Xóa trùng lặp theo hash
	- Lọc cặp câu theo độ dài, tỉ lệ độ dài, và điều kiện chữ cái
4. Tokenization:
	- EN: NLTK Treebank tokenizer
	- VI: underthesea
5. Tính thống kê:
	- Độ dài câu, tỉ lệ VI/EN
	- Từ vựng, TTR, hapax, coverage
6. Xuất file CSV/JSON/báo cáo.

### Yêu cầu môi trường

```bash
pip install datasets pandas underthesea nltk
```

Nếu chưa có tokenizer data cho NLTK, có thể cần:

```bash
python -c "import nltk; nltk.download('punkt')"
```

### Cách chạy preprocess

```bash
python preprocess_pipeline.py
```

### Đầu ra preprocess (thư mục `output/`)

- `dataset_en_vi_it_clean.csv`
- `dataset_en_vi_medical_clean.csv`
- `dataset_en_vi_business_clean.csv`
- `dataset_en_vi_general_clean.csv`
- `dataset_en_vi_all_domains.csv`
- `dataset_en_vi_it_clean.json`
- `vocab_en.json`
- `vocab_vi.json`
- `dataset_statistics_report.json`

## 3) Notebook hỗ trợ nghiên cứu

### `opus_en_vi.ipynb`

- Notebook hướng đến Colab.
- Tải dữ liệu EN-VI từ nhiều corpus OPUS (OpenSubtitles, WikiMatrix, TED2020, Tatoeba, QED, KDE4, GNOME, Ubuntu, bible-uedin, ELRC).
- Có checkpoint/logging để xử lý tập lớn.

### `eda_en_vi_translator.ipynb`

- EDA cho dataset EN-VI.
- Kiểm tra missing, duplicate, empty string.
- Tạo các feature độ dài câu/số từ và trực quan hóa.

### `check_filter_quality (1).ipynb`

- Pipeline kiểm tra chất lượng lọc cho dataset lớn.
- Kết hợp các bước:
	- Basic filtering theo độ dài và len ratio
  - Abbreviation consistency
  - Back-translation (vi -> en)
	- Semantic similarity bằng sentence-transformers

## Dataset sẵn có trong repo

`dataset_en_vi_all_domains_filtered_v3.2.csv` là bản dataset đã lọc sẵn, với 3 cột:

- `en`
- `vi`
- `domain`

## Quy trình đề xuất (end-to-end)

1. Crawl dữ liệu thô với `crawler.py` (nếu cần bộ dữ liệu riêng).
2. Chạy `preprocess_pipeline.py` để tạo bộ dữ liệu đa domain và thống kê.
3. Dùng `eda_en_vi_translator.ipynb` để kiểm tra phân bố và chất lượng.
4. Dùng `check_filter_quality (1).ipynb` cho bước lọc semantically stricter trước khi huấn luyện.

## Lưu ý

- Các notebook hiện tại thiên về Google Colab (đường dẫn `/content/...`).
- Nếu chạy local, cần đổi PATH và cấu hình lại đường dẫn file.
- Crawler GitHub có thể gặp giới hạn API nếu không dùng token.
