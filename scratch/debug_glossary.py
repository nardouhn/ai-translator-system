import chromadb
from chromadb.utils import embedding_functions
import re
from sentence_transformers import CrossEncoder

local_ef = embedding_functions.DefaultEmbeddingFunction()
client = chromadb.PersistentClient(path="./VectorDB_Gemini")
collection = client.get_collection(name="multi_domain_rag_kb", embedding_function=local_ef)
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def debug_glossary_retrieval(user_input, domain="medical"):
    user_input_lower = user_input.lower()
    domains_to_search = [f"{domain}_glossary", f"{domain}_context"]
    
    # 1. Glossary Pass
    glossary_where = {"domain": {"$in": [d for d in domains_to_search if "glossary" in d]}}
    print(f"Searching Glossary with filter: {glossary_where}")
    
    glossary_results = collection.query(
        query_texts=[user_input],
        n_results=30,
        where=glossary_where
    )
    
    docs = glossary_results["documents"][0]
    metas = glossary_results["metadatas"][0]
    
    print(f"Found {len(docs)} candidates in glossary pass.")
    
    for text, meta in zip(docs, metas):
        clean_term = re.escape(text.lower())
        # My current pattern: r'\b' + clean_term + r"(?:'s)?\b"
        pattern = r'\b' + clean_term + r"(?:'s)?\b"
        match = re.search(pattern, user_input_lower)
        
        print(f"Term: '{text}' | Match: {bool(match)} | Pattern: {pattern}")
        if match:
             print(f"   SUCCESS MATCH: {text}")

user_input = "The patient presented with persistent vertigo and hearing loss. Upon examination, a diagnosis of Meniere's disease was suspected, and an intratympanic steroid injection was recommended to alleviate the symptoms."
debug_glossary_retrieval(user_input)
