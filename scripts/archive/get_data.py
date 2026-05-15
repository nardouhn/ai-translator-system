import os
import zipfile
import shutil
import csv
from huggingface_hub import hf_hub_download

# Set the access token (Should be set as environment variable HF_TOKEN)
hf_token = os.getenv("HF_TOKEN")
if hf_token:
    os.environ["HF_TOKEN"] = hf_token
else:
    print("⚠️ Cảnh báo: Không tìm thấy HF_TOKEN trong biến môi trường. Việc tải từ Hugging Face có thể bị giới hạn hoặc thất bại.")
print("Đang tiến hành tải PhoMT.zip từ Hugging Face (Có thể mất vài phút vì file khá lớn khoảng 350MB)...")

try:
    # Tải file PhoMT.zip về local
    file_path = hf_hub_download(repo_id="vinai/PhoMT", filename="PhoMT.zip", repo_type="dataset", local_dir=".")
    print(f"Đã tải thành công file ZIP: {file_path}")
    print("--------------------------------------------------")
except Exception as e:
    print(f"Lỗi khi tải file: {e}")
    exit(1)

# Giải nén tìm dữ liệu y tế (Medical)
extract_dir = "PhoMT_extracted"
print(f"Đang giải nén tập tin vào thư mục {extract_dir}...")
with zipfile.ZipFile(file_path, 'r') as zip_ref:
    zip_ref.extractall(extract_dir)

# PhoMT dataset contains train/dev/test splits in various directories. 
# We will recursively find the "medical" domain files.
# Typically, translated datasets have .en and .vi files.
# Let's inspect the files first.
import glob
print("Tiến hành kiểm tra cấu trúc file y tế (Medical)...")
medical_en = glob.glob(f"{extract_dir}/**/medical/*.en", recursive=True) + glob.glob(f"{extract_dir}/**/*medical*.en", recursive=True)
medical_vi = glob.glob(f"{extract_dir}/**/medical/*.vi", recursive=True) + glob.glob(f"{extract_dir}/**/*medical*.vi", recursive=True)

if not medical_en or not medical_vi:
    print("Không tìm thấy các file *.en *.vi trong dữ liệu vừa giải nén!")
    # In ra thư mục con để kiểm tra
    for r, d, f in os.walk(extract_dir):
        print(f"Directory: {r}")
        for file in f:
            if "medical" in r.lower() or "medical" in file.lower():
                print(f"  --> File: {file}")
else:
    medical_en.sort()
    medical_vi.sort()
    print(f"Tìm thấy các file En: {medical_en}")
    print(f"Tìm thấy các file Vi: {medical_vi}")

    pairs = []
    for en_file, vi_file in zip(medical_en, medical_vi):
        with open(en_file, "r", encoding="utf-8") as f_en, open(vi_file, "r", encoding="utf-8") as f_vi:
            for line_en, line_vi in zip(f_en, f_vi):
                pairs.append((line_en.strip(), line_vi.strip()))
    
    # Save as CSV
    out_csv = "data/medical/medical_vin.csv"
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["english", "vietnamese"])
        writer.writerows(pairs)
    
    print(f"Thành công! Đã chuyển đổi dữ liệu medical và lưu {len(pairs)} cặp câu vào {out_csv}")