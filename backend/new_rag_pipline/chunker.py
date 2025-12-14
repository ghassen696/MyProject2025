from transformers import AutoTokenizer
import json

EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
CHUNK_SIZE = 480
OVERLAP = 50

tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)


def chunk_text(text: str, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    """Split text into overlapping token chunks."""
    tokens = tokenizer.encode(text, add_special_tokens=False)
    chunks = []
    
    start = 0
    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True).strip()
        if chunk_text:  # Only add non-empty chunks
            chunks.append(chunk_text)
        start += chunk_size - overlap
    
    return chunks


def chunk_documents(docs):
    """
    Convert documents into chunks with FULL metadata for citations.
    """
    all_chunks = []
    
    for doc in docs:
        content = doc["content"]
        chunks = chunk_text(content)
        
        for i, chunk in enumerate(chunks):
            chunk_data = {
                "chunk_id": f"{doc['doc_id']}_chunk_{i}",
                "content": chunk,
                # Preserve ALL metadata for citations
                "title": doc.get("title", "Untitled"),
                "filepath": doc["filepath"],
                "product": doc.get("product", "Unknown"),
                "version": doc.get("version", "Unknown"),
                "doc_path": doc.get("doc_path", ""),
                "doc_id": doc["doc_id"],
                "chunk_index": i,
                "total_chunks": len(chunks),
                # Add DC metadata if available
                "dc_type": doc.get("dc_type", ""),
                "dc_relation": doc.get("dc_relation", "")
            }
            all_chunks.append(chunk_data)
    
    return all_chunks
