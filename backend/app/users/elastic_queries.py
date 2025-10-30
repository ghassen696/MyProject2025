from elasticsearch import Elasticsearch
from app.config import ELASTICSEARCH_URL

es = Elasticsearch(ELASTICSEARCH_URL)

# --- Existing ---
def get_user_by_token(token: str):
    res = es.search(index="users2", body={"query": {"match": {"token": token}}})
    hits = res.get("hits", {}).get("hits", [])
    if hits:
        return hits[0]
    return None

def update_user_doc(user_id: str, doc: dict):
    return es.update(index="users2", id=user_id, body={"doc": doc})

# --- New: Delete user ---
def delete_user_doc(user_id: str):
    return es.delete(index="users2", id=user_id)
def get_all_users():
    res = es.search(index="users2", body={"query": {"match_all": {}}}, size=1000)
    hits = res.get("hits", {}).get("hits", [])
    users = []
    for h in hits:
        u = h["_source"]
        u["employee_id"] = h["_id"]
        users.append(u)
    return users

