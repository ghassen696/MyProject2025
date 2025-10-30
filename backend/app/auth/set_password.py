from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from app.auth.auth_utils import hash_password, check_password_strength
from app.users.elastic_queries import get_user_by_token, update_user_doc

router = APIRouter()

class SetPasswordRequest(BaseModel):
    token: str
    email: EmailStr
    password: str
    confirm_password: str
    employee_id: str  # keep this field


@router.post("/set-password")
def set_password(request: SetPasswordRequest):
    # 1️⃣ Get user by token
    print("Payload received:", request.dict())

    user_doc = get_user_by_token(request.token)

    if not user_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user_id = user_doc["_id"]
    user_data = user_doc["_source"]
    print("User doc found:", user_doc)

    print("Token expiry:", user_data.get("token_expiry"))

    # 2️⃣ Verify token expiry
    token_expiry_str = user_data.get("token_expiry")
    if not token_expiry_str:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    token_expiry = datetime.fromisoformat(token_expiry_str)
    if datetime.now(timezone.utc) > token_expiry:
        raise HTTPException(status_code=400, detail="Token has expired")

    # 3️⃣ Verify email
    if request.email.lower() != user_data.get("email", "").lower():
        raise HTTPException(status_code=400, detail="Email does not match invitation")

    # 4️⃣ Verify employee ID
    if request.employee_id != user_data.get("employee_id"):
        raise HTTPException(status_code=400, detail="Invalid employee ID")

    # 5️⃣ Check password strength
    errors = check_password_strength(request.password)
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    # 6️⃣ Confirm password match
    if request.password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # 7️⃣ Update user
    update_user_doc(user_id, {
        "password_hash": hash_password(request.password),
        "status": "active",
        "token": None,
        "token_expiry": None
    })

    return {"message": "Password set successfully!"}
