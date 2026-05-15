from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import subprocess
import os

# --- Cấu hình ---
CRAWLER_PATH = "/app/crawlers/real_crawler_extractor.py"
CONSUMER_PATH = "/app/crawlers/kafka_consumer_indexer.py"

default_args = {
    'owner': 'admin',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def run_crawler():
    """Chạy script crawler để phát hiện thuật ngữ mới và đẩy lên Kafka."""
    result = subprocess.run(["python", CRAWLER_PATH], capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Crawler failed: {result.stderr}")
    print(result.stdout)

# Khởi tạo DAG
with DAG(
    'rag_translation_pipeline',
    default_args=default_args,
    description='Pipeline tự động crawl và nạp tri thức cho RAG',
    schedule_interval=timedelta(days=1), # Chạy mỗi ngày một lần
    catchup=False,
) as dag:

    crawl_task = PythonOperator(
        task_id='run_daily_crawler',
        python_callable=run_crawler,
    )

    # Lưu ý: Consumer thường được chạy như một service ngầm (trong Docker) 
    # chứ không chạy theo Task vụ của Airflow vì nó cần lắng nghe liên tục.
    # Task này ở đây có thể dùng để kiểm tra trạng thái hoặc khởi động lại nếu cần.
    
    crawl_task
