import csv
import json
import os

def process_medical_csv(input_path: str, output_csv_path: str, output_json_path: str):
    """Read a CSV where the first half of rows contain English text and the second half contain Vietnamese text.
    Produce a CSV with two columns (english, vietnamese) and a JSON mapping.
    """
    pairs = []
    with open(input_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        # Skip header if present
        header = next(reader, None)
        # Determine if header is just 'text'
        if header and header[0].lower() != 'text':
            # Not a header, treat as first line
            f.seek(0)
            reader = csv.reader(f)
        else:
            # header consumed, continue
            pass
        # Collect lines
        lines = [row[0] for row in reader if row]
    # The file has all English lines first, followed by all Vietnamese lines
    half = len(lines) // 2
    for i in range(half):
        eng = lines[i].strip()
        viet = lines[i + half].strip()
        pairs.append((eng, viet))

    # Write paired CSV
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    with open(output_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['english', 'vietnamese'])
        writer.writerows(pairs)

    # Build JSON structure
    json_dict = {}
    for eng, viet in pairs:
        json_dict[eng] = {
            "translation": viet,
            "rule": ""
        }
    # Write JSON
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(json_dict, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    # Go one level up from scripts/ to the project root
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    input_csv = os.path.join(base_dir, 'data', 'medical', 'raw_medical_data_old.csv')
    output_csv = os.path.join(base_dir, 'data', 'medical', 'medical_data_train_processed.csv')
    output_json = os.path.join(base_dir, 'data', 'medical', 'medical_data_train.json')
    process_medical_csv(input_csv, output_csv, output_json)
    print(f"Processed CSV saved to {output_csv}")
    print(f"JSON saved to {output_json}")
