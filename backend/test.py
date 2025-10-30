from elasticsearch import Elasticsearch
import time

es = Elasticsearch("http://localhost:9200")

employee_id = "TEST01"
session_id = "S001"
idle_id = "IDLE001"

# idle start
es.index(index="employee_activity", document={
    "timestamp": 1760815004709,
    "event": "idle_start",
    "employee_id": employee_id,
    "session_id": session_id,
    "seq_num": 1,
    "idle_id": idle_id
})

# idle end 5 minutes later
es.index(index="employee_activity", document={
    "timestamp": 1760815004709 + 7200000,
    "event": "idle_end",
    "employee_id": employee_id,
    "session_id": session_id,
    "seq_num": 2,
    "idle_id": idle_id,
    "idle_duration_sec": 7200
})

print("Idle event created")
