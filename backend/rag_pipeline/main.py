# main.py — orchestrate full pipeline
import json
from ingest import find_all_html_files, is_content_page, extract_content
from chunker import chunk_documents
from embedder import rebuild_index, index_chunks, load_chunks

# ---------- Config ----------
ROOT_DIR = "/root/Huawei Cloud Stack_8.3.1_05_en_YEN0426D/resources"
HTML_JSON = "html_docs.json"
CHUNKED_JSON = "chunked_docs.json"
REBUILD_INDEX = True
# ----------------------------


def step1_ingest():
    html_files = find_all_html_files(ROOT_DIR)
    documents = []

    for file in html_files:
        if is_content_page(file):
            doc = extract_content(file)
            documents.append(doc)

    with open(HTML_JSON, "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)

    print(f"✅ Step 1: extracted {len(documents)} usable HTML pages.")
    return documents


def step2_chunk(docs):
    chunked_docs = chunk_documents(docs)

    with open(CHUNKED_JSON, "w", encoding="utf-8") as f:
        json.dump(chunked_docs, f, indent=2, ensure_ascii=False)

    print(f"✅ Step 2: created {len(chunked_docs)} chunks.")
    return chunked_docs


def main():
    print("🚀 Starting RAG ingestion pipeline...")

    # Step 1: Ingest
    docs = step1_ingest()

    # Step 2: Chunk
    step2_chunk(docs)

    # Step 3: Rebuild ES index
    rebuild_index(REBUILD_INDEX)

    # Step 4: Load chunks & index
    chunks = load_chunks(CHUNKED_JSON)
    index_chunks(chunks)

    print("\n✅ All steps completed!")
    print(f"Total documents: {len(docs)}")
    print(f"Total chunks: {len(chunks)}")


if __name__ == "__main__":
    main()
