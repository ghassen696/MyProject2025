from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.users.elastic_queries import es
from app.auth.auth_utils import verify_password, create_access_token

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/login")
def login(request: LoginRequest):
    email = request.email.lower()
    # Search user by email instead of username
    res = es.search(
        index="users2",
        body={"query": {"term": {"email": email}}}
    )
    hits = res.get("hits", {}).get("hits", [])
    if not hits:
        print("Received login request:", request.dict()) 
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user_doc = hits[0]["_source"]

    if not verify_password(request.password, user_doc["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({
        "email": request.email,
        "role": user_doc.get("role")
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user_doc["email"],
        "role": user_doc.get("role"),
        "username": user_doc.get("username"),
        "employee_id": user_doc.get("employee_id")
    }
