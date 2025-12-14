# main.py — orchestrate full pipeline
import json
from ingest import ingest_all_documents
from chunker import chunk_documents
from embedder import rebuild_index, index_chunks

# ---------- Config ----------
ROOT_DIR = "/root/Huawei Cloud Stack_8.3.1_05_en_YEN0426D/resources"
HTML_JSON = "ingest.json"
CHUNKED_JSON = "chunked.json"
REBUILD_INDEX = False
# ----------------------------

def step1_ingest():
    """Step 1: Ingest all HTML documents."""
    print(f"📂 Scanning directory: {ROOT_DIR}")
    docs = ingest_all_documents(ROOT_DIR, HTML_JSON)
    print(f"\n✅ Step 1 Complete: {len(docs)} documents extracted")
    print(f"   Output: {HTML_JSON}")
    return docs

def step2_chunk(docs):
    """Step 2: Chunk documents into smaller pieces."""
    print(f"✂️  Chunking {len(docs)} documents...")
    chunks = chunk_documents(docs)
    
    # Save chunks
    with open(CHUNKED_JSON, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Step 2 Complete: {len(chunks)} chunks created")
    print(f"   Output: {CHUNKED_JSON}")
    print(f"   Avg chunks per doc: {len(chunks) / len(docs):.1f}")
    return chunks

def step3_embed_and_index(chunks):
    """Step 3: Embed chunks and index into Elasticsearch."""    
    if REBUILD_INDEX:
        print("🔨 Rebuilding Elasticsearch index...")
        rebuild_index(REBUILD_INDEX)
    
    print(f"🧮 Embedding and indexing {len(chunks)} chunks...")
    print("⏳ This may take a while...")
    index_chunks(chunks)
    
    print(f"\n✅ Step 3 Complete: All chunks indexed")
    print(f"   Index name: html_chunks")
    return True

def main():
    print("🚀 Starting RAG ingestion pipeline...")

    # Step 1: Ingest
    docs = step1_ingest()

    # Step 2: Chunk
    chunks = step2_chunk(docs)

    # Step 3: Load chunks & index
    step3_embed_and_index(chunks)

    print("\n✅ All steps completed!")
    print(f"Total documents: {len(docs)}")
    print(f"Total chunks: {len(chunks)}")

if __name__ == "__main__":
    main()
