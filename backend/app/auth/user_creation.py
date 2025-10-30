from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from app.users.elastic_queries import es
import asyncio
from app.users.email_utils import send_invite_email
router = APIRouter()

class CreateUserRequest(BaseModel):
    email: EmailStr
    employee_id: str
    role: str = "user"

@router.post("/create-user")
async def create_user(request: CreateUserRequest):
    # Extract username from email
    email = request.email.lower()
    username = request.email.split("@")[0]

    # Generate token and expiry
    token = str(uuid4())
    token_expiry = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    # Build the user document
    user_doc = {
        "username": username,
        "email": email,
        "employee_id": request.employee_id,
        "role": request.role,
        "status": "pending",
        "token": token,
        "token_expiry": token_expiry,
        "password_hash": None
    }

    # Index into Elasticsearch
    doc_id = str(uuid4())

    res = es.index(index="users2", id=doc_id, document=user_doc)

    if res["result"] not in ["created", "updated"]:
        raise HTTPException(status_code=500, detail="Failed to create user")
    asyncio.create_task(send_invite_email(email, token))
    return {"message": "User created", "token": token}
