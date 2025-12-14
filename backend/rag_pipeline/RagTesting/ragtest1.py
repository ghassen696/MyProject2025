"""
RAG Chatbot Evaluation Script
Tests multiple LLMs and generates comprehensive metrics for report
"""

import time
import json
import ollama
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from typing import List, Dict, Tuple
import pandas as pd
from datetime import datetime

# ---------- Config ----------
ES_URL = "http://localhost:9200"
INDEX_NAME = "html_chunks"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
RESULTS_FILE = "rag_evaluation_results.json"
CSV_FILE = "rag_evaluation_results.csv"

# Models to test
MODELS_TO_TEST = [
    "llama3.2:1b",
    "llama3.2:3b", 
    "llama3.2:latest",  # 8B or 7B version
    "phi3:mini",
    "gemma2:2b",
]

# Test queries covering different aspects
TEST_QUERIES = [
    {
        "query": "What is Huawei Cloud Stack?",
        "category": "General Definition",
        "expected_keywords": ["cloud", "platform", "infrastructure", "huawei"]
    },
    {
        "query": "How do I configure VPC networking?",
        "category": "Technical Configuration",
        "expected_keywords": ["vpc", "network", "subnet", "configure"]
    },
    {
        "query": "What are the storage options available?",
        "category": "Features",
        "expected_keywords": ["storage", "volume", "disk", "backup"]
    },
    {
        "query": "How to create a virtual machine?",
        "category": "Step-by-Step Procedure",
        "expected_keywords": ["vm", "virtual machine", "create", "instance"]
    },
    {
        "query": "What are the security best practices?",
        "category": "Security",
        "expected_keywords": ["security", "encryption", "access", "policy"]
    },
    {
        "query": "How to monitor system performance?",
        "category": "Monitoring",
        "expected_keywords": ["monitor", "performance", "metrics", "logs"]
    },
    {
        "query": "What is the difference between public and private cloud?",
        "category": "Conceptual",
        "expected_keywords": ["public", "private", "cloud", "difference"]
    },
    {
        "query": "How to troubleshoot connection errors?",
        "category": "Troubleshooting",
        "expected_keywords": ["troubleshoot", "error", "connection", "fix"]
    }
]

# ---------- Initialize ----------
es = Elasticsearch(ES_URL)
embedding_model = SentenceTransformer(EMBEDDING_MODEL)


def build_prompt(context_chunks: List[str], query: str) -> str:
    """Build prompt with retrieved context"""
    context = ""
    for i, chunk in enumerate(context_chunks, 1):
        context += f"[{i}] {chunk}\n\n"
    
    prompt = f"""You are a helpful Huawei Cloud Assistant. Use only the context below to answer the question.
If the answer is not in the context, say "I don't know".

Context:
{context}

Question: {query}
Answer (with references like [1], [2] if applicable):"""
    
    return prompt.strip()


def retrieve_context(query: str, n_results: int = 3) -> Tuple[List[str], float]:
    """Retrieve relevant chunks from Elasticsearch"""
    start = time.time()
    
    # Embed query
    query_vector = embedding_model.encode([query])[0].tolist()
    
    # Search ES
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
            "_source": ["content"]
        }
    )
    
    retrieval_time = time.time() - start
    context_chunks = [hit["_source"]["content"] for hit in response["hits"]["hits"]]
    
    return context_chunks, retrieval_time


def query_llm(model_name: str, prompt: str, stream: bool = False) -> Tuple[str, float]:
    """Query LLM and measure response time"""
    start = time.time()
    
    try:
        if stream:
            full_response = ""
            stream_obj = ollama.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful Huawei Cloud Assistant."},
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )
            
            for chunk in stream_obj:
                full_response += chunk["message"]["content"]
        else:
            response = ollama.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful Huawei Cloud Assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            full_response = response["message"]["content"]
        
        inference_time = time.time() - start
        return full_response, inference_time
    
    except Exception as e:
        print(f"❌ Error with {model_name}: {e}")
        return f"ERROR: {str(e)}", 0.0


def evaluate_response(response: str, expected_keywords: List[str]) -> Dict:
    """Evaluate response quality based on keywords and structure"""
    response_lower = response.lower()
    
    # Keyword matching
    keywords_found = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
    keyword_score = (keywords_found / len(expected_keywords)) * 100
    
    # Response quality checks
    has_references = any(f"[{i}]" in response for i in range(1, 6))
    says_dont_know = "don't know" in response_lower or "i don't know" in response_lower
    response_length = len(response.split())
    
    return {
        "keywords_found": keywords_found,
        "total_keywords": len(expected_keywords),
        "keyword_score": round(keyword_score, 2),
        "has_references": has_references,
        "says_dont_know": says_dont_know,
        "response_length": response_length,
        "is_empty": len(response.strip()) < 10
    }


def test_single_model(model_name: str, test_queries: List[Dict]) -> List[Dict]:
    """Test a single model against all queries"""
    print(f"\n{'='*60}")
    print(f"Testing Model: {model_name}")
    print(f"{'='*60}")
    
    results = []
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n[{i}/{len(test_queries)}] Query: {test_case['query'][:60]}...")
        
        # Retrieve context
        context_chunks, retrieval_time = retrieve_context(test_case['query'])
        
        # Build prompt
        prompt = build_prompt(context_chunks, test_case['query'])
        
        # Query LLM
        response, inference_time = query_llm(model_name, prompt)
        
        # Evaluate response
        evaluation = evaluate_response(response, test_case['expected_keywords'])
        
        # Store results
        result = {
            "model": model_name,
            "query": test_case['query'],
            "category": test_case['category'],
            "response": response,
            "retrieval_time": round(retrieval_time, 3),
            "inference_time": round(inference_time, 3),
            "total_time": round(retrieval_time + inference_time, 3),
            **evaluation,
            "timestamp": datetime.now().isoformat()
        }
        
        results.append(result)
        
        print(f"  ⏱️  Retrieval: {retrieval_time:.2f}s | Inference: {inference_time:.2f}s")
        print(f"  ✅ Keyword Score: {evaluation['keyword_score']:.1f}%")
        print(f"  📝 Response Length: {evaluation['response_length']} words")
    
    return results


def generate_summary_statistics(all_results: List[Dict]) -> pd.DataFrame:
    """Generate summary statistics per model"""
    df = pd.DataFrame(all_results)
    
    summary = df.groupby('model').agg({
        'inference_time': ['mean', 'std', 'min', 'max'],
        'retrieval_time': ['mean'],
        'total_time': ['mean'],
        'keyword_score': ['mean', 'std'],
        'response_length': ['mean'],
        'has_references': 'sum',
        'says_dont_know': 'sum'
    }).round(3)
    
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    summary = summary.reset_index()
    
    return summary


def run_full_evaluation():
    """Run complete evaluation on all models"""
    print("🚀 Starting RAG Chatbot Evaluation")
    print(f"📊 Testing {len(MODELS_TO_TEST)} models with {len(TEST_QUERIES)} queries each")
    
    all_results = []
    
    for model in MODELS_TO_TEST:
        try:
            model_results = test_single_model(model, TEST_QUERIES)
            all_results.extend(model_results)
        except Exception as e:
            print(f"❌ Failed to test {model}: {e}")
            continue
    
    # Save detailed results
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved detailed results to {RESULTS_FILE}")
    
    # Generate and save summary
    summary_df = generate_summary_statistics(all_results)
    summary_df.to_csv(CSV_FILE, index=False)
    print(f"✅ Saved summary statistics to {CSV_FILE}")
    
    # Print summary table
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print(summary_df.to_string(index=False))
    
    return all_results, summary_df


if __name__ == "__main__":
    results, summary = run_full_evaluation()
    
    print("\n" + "="*80)
    print("EVALUATION COMPLETE!")
    print("="*80)
    print(f"Total tests run: {len(results)}")
    print(f"Results saved to: {RESULTS_FILE}")
    print(f"Summary saved to: {CSV_FILE}")