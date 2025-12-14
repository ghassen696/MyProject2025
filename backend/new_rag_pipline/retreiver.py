from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
import ollama
import time
from .prompt_builder import build_prompt_with_citations,format_response_with_sources
import asyncio
from typing import AsyncGenerator

ES_URL = "http://193.95.30.190:9200"
INDEX_NAME = "html_chunks5"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

es = Elasticsearch(ES_URL)
model = SentenceTransformer(EMBEDDING_MODEL)


def query_llm(prompt: str) -> str:
    """Query local LLM."""
    response = ollama.chat(
        model="llama3.2:latest",
        messages=[
            {
                "role": "system", 
                "content": "You are a helpful Huawei Cloud technical assistant. Always cite sources using [1], [2] format."
            },
            {"role": "user", "content": prompt}
        ],

    )
    return response["message"]["content"]


def retrieve_and_answer(user_query: str, n_results=5):
    """
    Retrieve relevant chunks and generate answer with citations.
    """
    t_start = time.time()
    t_embed = time.time()

    try:
        print(f"\n🔍 Query: {user_query}")
        
        # Encode query
        query_vector = model.encode([user_query])[0].tolist()
        print(f"⚙️ Embedding time: {time.time() - t_embed:.2f} sec")
        t_search = time.time()

        # Search Elasticsearch
        response = es.search(
            index=INDEX_NAME,
            body={
                "size": n_results,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                            "params": {"query_vector": query_vector}
                        }
                    }
                },
                "_source": ["chunk_id", "title", "filepath", "content", 
                        "product", "version", "doc_path", "doc_id"]
            }
        )
        print(f"   Elasticsearch search time: {time.time() - t_search:.2f} sec")

        # Extract chunks with full metadata
        context_chunks = [hit["_source"] for hit in response["hits"]["hits"]]
        
        if not context_chunks:
            return {
                "answer": "No relevant documentation found.",
                "sources": []
            }
        
        # Build prompt
        final_prompt = build_prompt_with_citations(context_chunks, user_query)
        
        # Query LLM
        answer = query_llm(final_prompt)
        
        # Format response with sources
        result = format_response_with_sources(answer, context_chunks)
        
        # Print sources
        print("\n📚 Sources:")
        for src in result["sources"]:
            print(f"  [{src['id']}] {src['title']} ({src['product']} {src['version']})")
            print(f"      Path: {src['doc_path']}")
        print(f"⏱️ Total pipeline time: {time.time() - t_start:.2f} sec")
        return result
    except Exception as e:
        print(f"❌ Elasticsearch error: {e}")
        print(f"⏱️ Total pipeline time: {time.time() - t_start:.2f} sec")

        return {
            "answer": "Search service is temporarily unavailable.",
            "sources": []
        }

import asyncio
from typing import AsyncGenerator
import time

async def retrieve_and_answer_stream(user_query: str, n_results=5) -> AsyncGenerator:
    """
    Streaming version that yields events as they happen.
    """
    t_start = time.time()
    
    try:
        # Step 1: Embedding
        t_embed = time.time()
        query_vector = model.encode([user_query])[0].tolist()
        embed_time = time.time() - t_embed
        
        # Step 2: Search Elasticsearch
        t_search = time.time()
        response = es.search(
            index=INDEX_NAME,
            body={
                "size": n_results,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                            "params": {"query_vector": query_vector}
                        }
                    }
                },
                "_source": ["chunk_id", "title", "filepath", "content", 
                           "product", "version", "doc_path", "doc_id"]
            }
        )
        search_time = time.time() - t_search
        
        context_chunks = [hit["_source"] for hit in response["hits"]["hits"]]
        
        if not context_chunks:
            yield {
                "type": "error",
                "content": "No relevant documentation found."
            }
            return
        
        # Step 3: Send sources immediately (INSTANT FEEDBACK!)
        sources = []
        for i, chunk in enumerate(context_chunks, 1):
            sources.append({
                "id": i,
                "title": chunk['title'],
                "product": chunk.get('product', 'Unknown'),
                "version": chunk.get('version', 'Unknown'),
                "filepath": chunk['filepath'],
                "doc_path": chunk.get('doc_path', ''),
            })
        
        yield {
            "type": "sources",
            "content": sources,
            "embed_time": round(embed_time, 2),
            "search_time": round(search_time, 2)
        }
        
        # Step 4: Build prompt
        t_prompt = time.time()  # ← ADD THIS

        final_prompt = build_prompt_with_citations(context_chunks, user_query)
        prompt_time = time.time() - t_prompt  # ← ADD THIS
        t_llm_start = time.time()  # ← ADD THIS
        first_token_time = None
        # Step 5: Stream LLM tokens
        stream = ollama.chat(
            model="llama3.2:latest",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful Huawei Cloud technical assistant. Always cite sources using [1], [2] format."
                },
                {"role": "user", "content": final_prompt}
            ],
            stream=True  # ← Enable streaming
        )
        
        for chunk in stream:
            if chunk['message']['content']:
                if first_token_time is None:
                    first_token_time = time.time() - t_llm_start
                yield {
                    "type": "token",
                    "content": chunk['message']['content']
                }
                await asyncio.sleep(0)  # Allow other tasks to run
        
        # Step 6: Send completion
        total_time = time.time() - t_start
        llm_total_time = time.time() - t_llm_start  # ← ADD THIS
        print(f"⏱️ Total pipeline time: {total_time:.2f} sec")
        print(f"⏱️ prompt_time: {prompt_time:.2f} sec")
        print(f"⏱️ embed_time: {embed_time:.2f} sec")
        print(f"⏱️ first_token_time: {first_token_time:.2f} sec" if first_token_time else "⏱️ first_token_time: 0.00 sec")
        print(f"⏱️ search_time: {search_time:.2f} sec")
        print(f"⏱️ llm_total_time: {llm_total_time:.2f} sec")
        yield {
            "type": "done",
            "total_time": round(total_time, 2),
        }
        
    except Exception as e:
        yield {
            "type": "error",
            "content": f"Search service error: {str(e)}"
        }