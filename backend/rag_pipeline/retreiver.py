"""# retriever.py (diagnostic version)
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from prompt_builder import build_prompt
import subprocess
import time
import ollama
# ---------- Config ----------
ES_URL = "http://localhost:9200"
INDEX_NAME = "html_chunks2"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
# ----------------------------

es = Elasticsearch(ES_URL)
model = SentenceTransformer(EMBEDDING_MODEL)

def query_llm(prompt: str) -> str:
    start = time.time()
    result = subprocess.run(
        ["ollama", "run", "llama3.2:latest"],
        input=prompt,
        capture_output=True,
        text=True
    )
    end = time.time()
    print(f"🧠 LLM response time: {end - start:.2f} sec")
    return result.stdout.strip()

def retrieve_and_answer(user_query: str, n_results=2):
    total_start = time.time()

    # Step 1: Embedding
    t1 = time.time()
    query_vector = model.encode([user_query])[0].tolist()
    t2 = time.time()
    print(f"⚙️ Embedding time: {t2 - t1:.2f} sec")

    # Step 2: Elasticsearch retrieval
    t3 = time.time()
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
            "_source": ["chunk_id", "title", "filepath", "content"]
        }
    )
    t4 = time.time()
    print(f"🔍 Elasticsearch search time: {t4 - t3:.2f} sec")

    # Step 3: Prompt building
    context_chunks = [hit["_source"]["content"] for hit in response["hits"]["hits"]]
    t5 = time.time()
    final_prompt = build_prompt(context_chunks, user_query)
    t6 = time.time()
    print(f"🧩 Prompt build time: {t6 - t5:.2f} sec")

    # Step 4: LLM answering
    answer = query_llm(final_prompt)

    total_end = time.time()
    print(f"⏱️ Total pipeline time: {total_end - total_start:.2f} sec\n")

    return answer
"""
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from .prompt_builder import build_prompt
import time
import ollama

# ---------- Config ----------
ES_URL = "http://localhost:9200"
INDEX_NAME = "html_chunks"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
# ----------------------------

es = Elasticsearch(ES_URL)
model = SentenceTransformer(EMBEDDING_MODEL)

def query_llm(prompt: str) -> str:
    start = time.time()
    # Uses local Ollama API instead of subprocess
    response = ollama.chat(
        model="llama3.2:latest",
        messages=[
            {"role": "system", "content": "You are a helpful Huawei Cloud Assistant trained on internal documentation."},
            {"role": "user", "content": prompt}
        ]
    )
    end = time.time()
    print(f"🧠 LLM response time: {end - start:.2f} sec")
    return response["message"]["content"]

def retrieve_and_answer(user_query: str, n_results=2):
    total_start = time.time()

    # Step 1: Embedding
    t1 = time.time()
    query_vector = model.encode([user_query])[0].tolist()
    t2 = time.time()
    print(f"⚙️ Embedding time: {t2 - t1:.2f} sec")

    # Step 2: Elasticsearch retrieval
    t3 = time.time()
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
            "_source": ["chunk_id", "title", "filepath", "content"]
        }
    )
    t4 = time.time()
    print(f"🔍 Elasticsearch search time: {t4 - t3:.2f} sec")

    # Step 3: Prompt building
    context_chunks = [hit["_source"]["content"] for hit in response["hits"]["hits"]]
    t5 = time.time()
    final_prompt = build_prompt(context_chunks, user_query)
    t6 = time.time()
    print(f"🧩 Prompt build time: {t6 - t5:.2f} sec")

    # Step 4: LLM answering (local fast API)
    answer = query_llm(final_prompt)

    total_end = time.time()
    print(f"⏱️ Total pipeline time: {total_end - total_start:.2f} sec\n")

    return answer
