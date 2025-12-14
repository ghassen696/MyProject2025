from typing import List, Dict

def build_prompt_with_citations(context_chunks: List[Dict], query: str) -> str:
    """
    Build prompt with rich citation metadata.
    """
    context = ""
    for i, chunk in enumerate(context_chunks, 1):
        # Format citation info
        citation = f"[{i}] {chunk['title']}"
        if chunk.get('product') != 'Unknown':
            citation += f" ({chunk['product']})"
        if chunk.get('version') != 'Unknown':
            citation += f" v{chunk['version']}"
        
        context += f"{citation}\n{chunk['content']}\n\n"
    
    prompt = f"""You are a Huawei Cloud technical assistant. Answer the question using ONLY the provided documentation context.

IMPORTANT CITATION RULES:
1. Cite EVERY factual claim with [1], [2], etc.
2. Use multiple citations if claim spans sources: [1][2]
3. Format: "The feature supports X [1] and Y [2]."
4. If unsure, say "The documentation doesn't specify this."

Context:
{context}

Question: {query}

Answer (cite sources as [1], [2], etc.):"""
    
    return prompt.strip()


def format_response_with_sources(answer: str, context_chunks: List[Dict]) -> Dict:
    """
    Format the final response with full source citations.
    """
    sources = []
    for i, chunk in enumerate(context_chunks, 1):
        source = {
            "id": i,
            "title": chunk['title'],
            "product": chunk.get('product', 'Unknown'),
            "version": chunk.get('version', 'Unknown'),
            "filepath": chunk['filepath'],
            "doc_path": chunk.get('doc_path', ''),
            # You could add URL if you have a doc hosting server
            # "url": f"https://docs.yourcompany.com/{chunk['doc_id']}"
        }
        sources.append(source)
    
    return {
        "answer": answer,
        "sources": sources
    }