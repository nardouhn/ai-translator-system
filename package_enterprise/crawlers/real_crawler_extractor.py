"""
Multi-Source Glossary Crawler (V7 - Deep Discovery)
- Discovery Queue: Càng chạy càng tìm ra nhiều category mới để quét.
- Multi-Output: Tách dữ liệu ra 3 file: medical, technical, economic.
"""
import time
import requests
import json
import os
from kafka import KafkaProducer

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) DataMiningBot/5.0'}

# Cấu hình Kafka
KAFKA_SERVERS = os.getenv("KAFKA_SERVERS", "localhost:29092")
KAFKA_TOPIC = "translation_updates"

try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        retries=5
    )
    print(f"✅ Kafka Producer initialized: {KAFKA_SERVERS}")
except Exception as e:
    print(f"⚠️ Kafka not available, running in local-only mode: {e}")
    producer = None
# Tự động xác định thư mục của script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

QUEUE_FILE = os.path.join(BASE_DIR, "discovery_queue.json")
DONE_FILE = os.path.join(BASE_DIR, "discovery_done.json")

# Định nghĩa 3 file đầu ra
FILES = {
    "medical": os.path.join(BASE_DIR, "medical_terms.json"),
    "technical": os.path.join(BASE_DIR, "technical_terms.json"),
    "economic": os.path.join(BASE_DIR, "economic_terms.json")
}

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def request_with_retry(url, params=None):
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if resp.status_code == 429:
            time.sleep(60)
            return request_with_retry(url, params)
        return resp if resp.status_code == 200 else None
    except: return None

def process_category(cat_name, domain):
    print(f"     📂 Processing: {cat_name} [{domain}]")
    params = {
        "action": "query", "list": "categorymembers", "cmtitle": cat_name,
        "cmlimit": 500, "format": "json"
    }
    resp = request_with_retry("https://vi.wikipedia.org/w/api.php", params=params)
    if not resp: return [], []
    try:
        members = resp.json().get("query", {}).get("categorymembers", [])
        pages = [m["title"] for m in members if m["ns"] == 0]
        subcats = [m["title"] for m in members if m["ns"] == 14]
        return pages, subcats
    except: return [], []

def get_en_translations(vi_titles, domain):
    results = []
    batch_size = 50
    for i in range(0, len(vi_titles), batch_size):
        batch = vi_titles[i:i+batch_size]
        r = request_with_retry("https://vi.wikipedia.org/w/api.php", params={
            "action": "query", "titles": "|".join(batch), "prop": "langlinks", "lllang": "en", "format": "json"
        })
        if r:
            pages = r.json().get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                ll = pdata.get("langlinks", [])
                if ll:
                    results.append({"english": ll[0].get("*").lower(), "vietnamese": pdata.get("title"), "domain": domain})
        time.sleep(0.5)
    return results

if __name__ == "__main__":
    # 1. Khởi tạo & Load toàn bộ dữ liệu cũ từ 3 file để kiểm tra trùng
    all_terms = []
    for domain, path in FILES.items():
        all_terms.extend(load_json(path, []))
    
    existing_en = {t["english"].lower() for t in all_terms}
    queue = load_json(QUEUE_FILE, {
        "economic": ["Thể loại:Kinh tế học", "Thể loại:Tài chính"],
        "technical": ["Thể loại:Khoa học máy tính", "Thể loại:Trí tuệ nhân tạo"],
        "medical": ["Thể loại:Y học", "Thể loại:Bệnh học"]
    })
    done = load_json(DONE_FILE, [])

    print(f"🚀 Discovery Mode: {len(all_terms)} từ đã có | {len(done)} category đã xong.")

    # 2. Quét category mới
    DAILY_LIMIT = 10 
    new_found_terms = []

    for domain in queue.keys():
        to_process = []
        count = 0
        while queue[domain] and count < DAILY_LIMIT:
            cat = queue[domain].pop(0)
            if cat not in done:
                to_process.append(cat)
                count += 1
        
        for cat in to_process:
            pages, subcats = process_category(cat, domain)
            new_found_terms.extend(get_en_translations(pages, domain))
            for sub in subcats:
                if sub not in done and sub not in queue[domain]:
                    queue[domain].append(sub)
            done.append(cat)

    # 3. Phân loại và Lưu ra 3 file khác nhau
    added_count = {"medical": 0, "technical": 0, "economic": 0}
    
    # Tạo dictionary chứa dữ liệu theo domain
    domain_data = {dom: load_json(path, []) for dom, path in FILES.items()}
    
    for t in new_found_terms:
        en_key = t["english"].lower()
        dom = t["domain"]
        if en_key not in existing_en:
            domain_data[dom].append(t)
            existing_en.add(en_key)
            added_count[dom] += 1
            
            # Gửi lên Kafka
            if producer:
                try:
                    producer.send(KAFKA_TOPIC, t)
                except Exception as e:
                    print(f"      ❌ Lỗi gửi Kafka cho {en_key}: {e}")
    
    if producer:
        producer.flush()

    # Lưu lại 3 file json
    for dom, path in FILES.items():
        save_json(path, domain_data[dom])

    # Lưu trạng thái hàng đợi
    save_json(QUEUE_FILE, queue)
    save_json(DONE_FILE, done)

    print(f"\n✅ Hoàn tất lượt chạy!")
    print(f"➕ Medical   : +{added_count['medical']} mới")
    print(f"➕ Technical : +{added_count['technical']} mới")
    print(f"➕ Economic  : +{added_count['economic']} mới")
    print(f"📈 Hàng đợi  : Còn {sum(len(v) for v in queue.values())} category chờ quét.")
