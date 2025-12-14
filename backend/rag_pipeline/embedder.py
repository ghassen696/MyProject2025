"""# embedder.py
import json
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch, exceptions
from elasticsearch.helpers import bulk
from tqdm import tqdm

# ---------- Config ----------
ES_URL = "http://localhost:9200"
INDEX_NAME = "html_chunks"
CHUNKS_JSON_PATH = "chunked_docs.json"
BATCH_SIZE = 500
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
# ----------------------------

# Create index with vector mapping

es = Elasticsearch(ES_URL, verify_certs=False)

# Try to create index, ignore if it already exists
try:
    es.indices.create(
        index=INDEX_NAME,
        mappings={
            "properties": {
                "chunk_id": {"type": "keyword"},
                "title": {"type": "text"},
                "filepath": {"type": "keyword"},
                "content": {"type": "text"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "cosine"
                }
            }
        }
    )
    print(f"🆕 Index '{INDEX_NAME}' created.")
except exceptions.RequestError as e:
    if "resource_already_exists_exception" in str(e.info):
        print(f"✅ Index '{INDEX_NAME}' already exists.")
    else:
        raise


# Load JSON chunks
with open(CHUNKS_JSON_PATH, "r", encoding="utf-8") as f:
    docs = json.load(f)

model = SentenceTransformer(EMBEDDING_MODEL)

# Index in batches using bulk API
for i in tqdm(range(0, len(docs), BATCH_SIZE), desc="🔢 Indexing Batches"):
    batch = docs[i:i+BATCH_SIZE]
    actions = []
    for doc in batch:
        embedding = model.encode(doc["content"]).tolist()
        actions.append({
            "_index": INDEX_NAME,
            "_id": doc["chunk_id"],
            "_source": {
                "chunk_id": doc["chunk_id"],
                "title": doc["title"],
                "filepath": doc["filepath"],
                "content": doc["content"],
                "embedding": embedding
            }
        })
    bulk(es, actions)

print(f"✅ Indexed {len(docs)} chunks into Elasticsearch.")
"""
# embedder.py
import json
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from tqdm import tqdm

# ---------- Config ----------
ES_URL = "http://193.95.30.190:9200"
INDEX_NAME = "html_chunks"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
BATCH_SIZE = 500
# ----------------------------

# Elasticsearch client
es = Elasticsearch(ES_URL, verify_certs=False)

# Load embedding model
model = SentenceTransformer(EMBEDDING_MODEL)


def rebuild_index(rebuild=True):
    """
    Delete old index and recreate it if rebuild=True
    """
    if rebuild and es.indices.exists(index=INDEX_NAME):
        print("🗑️  Deleting old index...")
        es.indices.delete(index=INDEX_NAME)

    # Recreate index
    es.indices.create(
        index=INDEX_NAME,
        mappings={
            "properties": {
                "chunk_id": {"type": "keyword"},
                "title": {"type": "text"},
                "filepath": {"type": "keyword"},
                "content": {"type": "text"},
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
    """
    Embed and index chunks into Elasticsearch in batches
    """
    for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="🔢 Indexing Batches"):
        batch = chunks[i:i + BATCH_SIZE]
        actions = []
        for doc in batch:
            embedding = model.encode(doc["content"]).tolist()
            actions.append({
                "_index": INDEX_NAME,
                "_id": doc["chunk_id"],
                "_source": {
                    "chunk_id": doc["chunk_id"],
                    "title": doc["title"],
                    "filepath": doc["filepath"],
                    "content": doc["content"],
                    "embedding": embedding
                }
            })
        bulk(es, actions)

    print(f"✅ Indexed {len(chunks)} chunks into Elasticsearch.")


def load_chunks(json_path="chunked_docs.json"):
    """
    Load chunked documents JSON
    """
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)
