root_dir: "/root/Huawei Cloud Stack_8.3.1_05_en_YEN0426D/resources",
html_json: "html_docs.json",
chunked_json: "chunked_docs.json",
rebuild_index: true,
n_results: 3,
chunk_size: 480,
overlap: 50,
embedding_model: "sentence-transformers/all-mpnet-base-v2",
llm_model: "llama3.2:latest"
ES_URL=http://193.95.30.190:9200
ES_USER=elastic
ES_PASSWORD=your_password
OLLAMA_HOST=http://193.95.30.190:11434