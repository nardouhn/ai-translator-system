import json
import threading
from confluent_kafka import Consumer, KafkaError
from core.rag_manager import RAGManager

class KafkaRAGWorker(threading.Thread):
    def __init__(self, rag_manager: RAGManager, bootstrap_servers: str, topic: str, group_id: str = "rag-group"):
        super().__init__()
        self.rag = rag_manager
        self.topic = topic
        self.conf = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest'
        }
        self.running = True
        self.daemon = True # Tự động tắt khi main process tắt

    def run(self):
        print(f"🚀 Kafka Worker: Đang kết nối tới {self.conf['bootstrap.servers']}...")
        try:
            consumer = Consumer(self.conf)
            consumer.subscribe([self.topic])

            while self.running:
                msg = consumer.poll(1.0)
                if msg is None: continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF: continue
                    else:
                        print(f"❌ Kafka Error: {msg.error()}")
                        break

                try:
                    data = json.loads(msg.value().decode('utf-8'))
                    en = data.get("english")
                    vi = data.get("vietnamese")
                    domain = data.get("domain", "general")

                    if en and vi:
                        self.rag.add_knowledge(en=en, vi=vi, domain=domain)
                except Exception as e:
                    print(f"⚠️ Kafka: Lỗi xử lý message: {e}")

            consumer.close()
        except Exception as e:
            print(f"❌ Kafka Worker crashed: {e}")

    def stop(self):
        self.running = False
