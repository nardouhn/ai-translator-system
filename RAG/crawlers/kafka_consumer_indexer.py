import json
import os
import chromadb
from chromadb.utils import embedding_functions
from kafka import KafkaConsumer
import hashlib

# --- Cấu hình ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ưu tiên lấy từ biến môi trường Docker, nếu không có mới tự tính toán
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(BASE_DIR), "VectorDB"))
KAFKA_SERVERS = os.getenv("KAFKA_SERVERS", "localhost:29092")
KAFKA_TOPIC = "translation_updates"

def get_collection_name(domain):
    if domain == "medical": return "medical_kb"
    if domain == "economic": return "economic_kb"
    if domain == "technical": return "technical_kb"
    return "general_kb"

def start_consumer():
    print(f"📡 Kafka Consumer đang khởi động: {KAFKA_SERVERS}")
    print(f"📂 Kết nối database tại: {DB_PATH}")

    # Khởi tạo ChromaDB
    client = chromadb.PersistentClient(path=DB_PATH)
    local_ef = embedding_functions.DefaultEmbeddingFunction()

    # Khởi tạo Kafka Consumer
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_SERVERS,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='indexer-group',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        print(f"✅ Đang lắng nghe topic: {KAFKA_TOPIC}...")
    except Exception as e:
        print(f"❌ Không thể kết nối Kafka: {e}")
        return

    for message in consumer:
        item = message.value
        english = item.get("english")
        vietnamese = item.get("vietnamese")
        domain = item.get("domain", "general")

        if english and vietnamese:
            en_clean = english.strip().lower()
            term_id = hashlib.md5(en_clean.encode()).hexdigest()
            col_name = get_collection_name(domain)
            
            try:
                collection = client.get_or_create_collection(name=col_name, embedding_function=local_ef)
                collection.upsert(
                    documents=[english],
                    metadatas=[{
                        "english": english,
                        "vietnamese": vietnamese, 
                        "domain": domain, 
                        "type": "glossary"
                    }],
                    ids=[f"glos_{domain}_{term_id}"]
                )
                print(f"📥 [KAFKA] Đã nạp: {english} -> {vietnamese} ({domain})")
            except Exception as e:
                print(f"❌ Lỗi nạp dữ liệu cho {en}: {e}")

if __name__ == "__main__":
    start_consumer()