from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from tqdm import tqdm
import json

ES_URL = "http://193.95.30.190:9200"
INDEX_NAME = "html_chunks5"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
BATCH_SIZE = 500

es = Elasticsearch(ES_URL, verify_certs=False)
model = SentenceTransformer(EMBEDDING_MODEL)


def rebuild_index(rebuild=True):
    """Delete and recreate index with metadata fields."""
    if rebuild and es.indices.exists(index=INDEX_NAME):
        print("🗑️  Deleting old index...")
        es.indices.delete(index=INDEX_NAME)
    
    es.indices.create(
        index=INDEX_NAME,
        mappings={
            "properties": {
                "chunk_id": {"type": "keyword"},
                "content": {"type": "text"},
                "title": {"type": "text"},
                "filepath": {"type": "keyword"},
                "product": {"type": "keyword"},
                "version": {"type": "keyword"},
                "doc_path": {"type": "text"},
                "doc_id": {"type": "keyword"},
                "dc_type": {"type": "keyword"},
                "dc_relation": {"type": "keyword"},
                "chunk_index": {"type": "integer"},
                "total_chunks": {"type": "integer"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "cosine",
                    "index_options": {
                        "type": "hnsw",
                        "m": 16,
                        "ef_construction": 200
                    }
                }
            }
        }
    )
    print(f"✅ Index '{INDEX_NAME}' ready.")


def index_chunks(chunks):
    """Embed and index chunks with all metadata."""
    for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="🔢 Indexing Batches"):
        batch = chunks[i:i + BATCH_SIZE]
        actions = []
        
        for doc in batch:
            embedding = model.encode(doc["content"]).tolist()
            actions.append({
                "_index": INDEX_NAME,
                "_id": doc["chunk_id"],
                "_source": {
                    **doc,  # Include all metadata
                    "embedding": embedding
                }
            })
        
        bulk(es, actions)
    
    print(f"✅ Indexed {len(chunks)} chunks into Elasticsearch.")
