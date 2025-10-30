import time
from retreiver import retrieve_and_answer

# ---------- Test Queries ----------
test_queries2 = [
    "How to view Component Information?",
    "How to manually back up applications and data of ManageOne Deployment Portal?",
    "How to delete the DR Configuration?",
    "how to fix an error in myload balancer instance?"
]
test_queries = [
    "how to fix an error in myload balancer instance?"
]

print("🚀 Testing RAG response speed and accuracy...\n")

for q in test_queries:
    print(f"🔍 Query: {q}")
    start = time.time()
    answer = retrieve_and_answer(q, n_results=2)
    end = time.time()
    duration = end - start
    print(f"🧠 Answer:\n{answer}\n")
    print(f"⚡ Time taken: {duration:.2f} seconds")
    print("="*80, "\n")
