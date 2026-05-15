import json
import os
import chromadb
from chromadb.utils import embedding_functions

# --- Configuration ---
DB_PATH = "./VectorDB_Gemini"
BATCH_SIZE = 2000
CHECKPOINT_FILE = "scripts/rag_core/index_checkpoint.json"

# Mapping of domain folders to their primary files
DOMAINS = {
    "medical_glossary": "data/medical/medical_glossary.json",
    "economic_glossary": "data/economic/economic_glossary.json",
    "technical_glossary": "data/technical/technical_glossary.json",
    "general_context": "data/general/general_context.json",
    "medical_context": "data/medical/medical_context.json",
    "economic_context": "data/economic/economic_context.json"
}

def get_collection_name(domain_key):
    """Xác định tên Collection dựa trên khóa domain."""
    if "medical" in domain_key: return "medical_kb"
    if "economic" in domain_key: return "economic_kb"
    if "technical" in domain_key: return "technical_kb"
    return "general_kb"

def save_checkpoint(domain, index):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"domain": domain, "index": index}, f)

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {"domain": None, "index": 0}

def load_data(file_path):
    if not os.path.exists(file_path):
        print(f"Warning: File not found {file_path}")
        return []
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    standardized = []
    
    # Handle List of Dicts [{"english": ..., "vietnamese": ...}]
    if isinstance(data, list):
        for item in data:
            en = item.get("english") or item.get("en")
            vi = item.get("vietnamese") or item.get("vi") or item.get("translation")
            if en and vi:
                standardized.append({"english": str(en), "vietnamese": str(vi)})
                
    # Handle Dict {"en": {"translation": ...}}
    elif isinstance(data, dict):
        for en, details in data.items():
            if isinstance(details, dict):
                vi = details.get("translation") or details.get("vietnamese")
                if vi:
                    standardized.append({"english": str(en), "vietnamese": str(vi)})
            else:
                standardized.append({"english": str(en), "vietnamese": str(details)})
                
    return standardized

def run_indexing():
    # 1. Initialize ChromaDB with Local MiniLM
    print("Initializing ChromaDB with Local MiniLM (All-MiniLM-L6-v2 running offline)...")
    client = chromadb.PersistentClient(path=DB_PATH)
    local_ef = embedding_functions.DefaultEmbeddingFunction()
    
    # 2. Tạo sẵn các collection theo lĩnh vực
    collections = {
        "medical_kb": client.get_or_create_collection(name="medical_kb", embedding_function=local_ef),
        "economic_kb": client.get_or_create_collection(name="economic_kb", embedding_function=local_ef),
        "technical_kb": client.get_or_create_collection(name="technical_kb", embedding_function=local_ef),
        "general_kb": client.get_or_create_collection(name="general_kb", embedding_function=local_ef)
    }
    
    checkpoint = load_checkpoint()
    resume_domain = checkpoint.get("domain")
    resume_index = checkpoint.get("index", 0)
    
    if resume_domain:
        print(f"Resuming from {resume_domain} at index {resume_index}")

    total_indexed = 0
    found_resume_point = (resume_domain is None)
    
    # 3. Process each domain
    for domain_key, file_path in DOMAINS.items():
        if not found_resume_point:
            if domain_key == resume_domain:
                found_resume_point = True
            else:
                print(f"Skipping domain: {domain_key.upper()} (Already processed)")
                continue

        target_collection_name = get_collection_name(domain_key)
        collection = collections[target_collection_name]
        
        print(f"\nProcessing domain: {domain_key.upper()} -> Collection: {target_collection_name}")
        items = load_data(file_path)
        if not items:
            continue
            
        print(f"Found {len(items)} items. Starting embedding...")
        
        # 4. Preparation
        documents = []
        metadatas = []
        ids = []
        
        # Tách domain name và type từ domain_key
        # Ví dụ: "medical_glossary" -> domain="medical", type="glossary"
        #        "general_context"  -> domain="general", type="context"
        if "glossary" in domain_key:
            domain_name = domain_key.replace("_glossary", "")
            data_type = "glossary"
        else:
            domain_name = domain_key.replace("_context", "")
            data_type = "context"
        
        for idx, item in enumerate(items):
            documents.append(item["english"])
            metadatas.append({
                "vietnamese": item["vietnamese"],
                "domain": domain_name,
                "type": data_type
            })
            ids.append(f"{domain_key}_{idx}")
            
        # 5. Batch Upsert with Resuming within Domain
        start_idx = resume_index if domain_key == resume_domain else 0
        resume_index = 0 # Reset for next domains
        
        for i in range(start_idx, len(documents), BATCH_SIZE):
            end = min(i + BATCH_SIZE, len(documents))
            collection.upsert(
                documents=documents[i:end],
                metadatas=metadatas[i:end],
                ids=ids[i:end]
            )
            print(f"  > [{domain_key}] Progress: {end}/{len(documents)}")
            save_checkpoint(domain_key, end)
        
        total_indexed += len(items)
        
    print(f"\n✅ SUCCESS! Indexing session complete.")
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE) # Clean up on finish

if __name__ == "__main__":
    run_indexing()
