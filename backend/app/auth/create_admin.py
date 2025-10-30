from elasticsearch import Elasticsearch
from app.auth.auth_utils import hash_password
from app.config import ELASTICSEARCH_URL

es = Elasticsearch(ELASTICSEARCH_URL)
INDEX_NAME = "users2"

# 1️⃣ Create index if not exists
if not es.indices.exists(index=INDEX_NAME):
    es.indices.create(
        index=INDEX_NAME,
        body={
            "mappings": {
                "properties": {
                    "username": {"type": "keyword"},
                    "email": {"type": "keyword"},
                    "role": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "password_hash": {"type": "keyword"},
                    "token": {"type": "keyword"},
                    "token_expiry": {"type": "date"},
                    "employee_id": {"type": "keyword"},
                }
            }
        },
    )
    print(f"📁 Index '{INDEX_NAME}' created")

# 2️⃣ Define admin user
admin_user = {
    "username": "admin",
    "email": "admin@gmail.com",
    "role": "admin",
    "status": "active",
    "password_hash": hash_password("Huawei@2025"),
    "token": None,
    "token_expiry": None,
    "employee_id": "G50047910-5JjP5",
}

# 3️⃣ Check if admin exists
query = {"query": {"term": {"role.keyword": "admin"}}}
res = es.search(index=INDEX_NAME, body=query)

if res["hits"]["total"]["value"] == 0:
    resp = es.index(index=INDEX_NAME, id=admin_user["employee_id"], document=admin_user)
    print("✅ Admin user created:", resp["_id"])
else:
    print("⚠️ Admin user already exists")
